"""Module to work with Data Commons CustomDataManager"""

from __future__ import annotations

from collections.abc import Sequence
from os import PathLike
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import HttpUrl

from dcp_tools.custom_data.config_utils import (
    DuplicatePolicy,
    merge_configs,
    merge_configs_from_directory,
)
from dcp_tools.custom_data.models.config_file import Config
from dcp_tools.custom_data.models.data_files import (
    ColumnMappings,
    ExplicitSchemaFile,
    MCFFileName,
)
from dcp_tools.custom_data.models.mcf import MCFNodes
from dcp_tools.custom_data.models.sources import Source
from dcp_tools.custom_data.models.stat_vars import (
    StatType,
    StatVarGroupMCFNode,
    StatVarMCFNode,
)
from dcp_tools.custom_data.schema_tools import (
    build_stat_var_groups_from_strings,
    csv_metadata_to_nodes,
    validate_mcf_file_name,
)

DEFAULT_STATVAR_MCF_NAME: str = "custom_nodes.mcf"
DEFAULT_GROUP_NAME: str = "custom_groups.mcf"


def _parse_kwargs_into_properties(locals_dict: dict[str, Any]) -> dict[str, Any]:
    """Parse a dictionary of keyword arguments into a dictionary of properties"""

    props = {
        k: v
        for k, v in locals_dict.items()
        if k not in {"self", "additional_properties", "override", "mcf_file_name"}
        and v is not None
    }

    if "additional_properties" in locals_dict:
        additional = locals_dict.get("additional_properties", {})
        if additional:
            props.update(additional)

    return props


class CustomDataManager:
    """Class to handle the config json, data, and MCF files for Custom Data Commons

    Args:
        config_file: Path to the config json file. If not provided, a new config objet will be created.
        mcf_files: Path to one or more MCF files. If not provided, a new MCFNodes object will be created.

    Usage:

    To start instantiate the object with or without an existing config json and MCF file
    >>> dc_manager = CustomDataManager()
    or
    >>> dc_manager = CustomDataManager(config_file="path/to/config.json", mcf_file="path/to/mcf_file.mcf")

    To add a provenance to the config, use the add_provenance method
    >>> dc_manager.add_provenance(
    >>>     provenance_name="Provenance Name",
    >>>     provenance_url="https://example.com/provenance",
    >>>     source_name="Source Name",
    >>>     source_url="https://example.com/source"
    >>> )

    This will add a provenance and a source in the config. If the source already exists,
    you can add another provenance to the existing source
    >>> dc_manager.add_provenance(
    >>>    provenance_name="Provenance Name",
    >>>    provenance_url="https://example.com/provenance",
    >>>    source_name="Source Name"
    >>> )

    To add a variable for export to an MCF file (using the explicit schema), use the
    add_variable_to_mcf method
    >>> dc_manager.add_variable_to_mcf(
    >>>    Node="StatVar",
    >>>    name="Variable Name",
    >>>    description="Variable Description",
    >>>    ...
    >>>    )

    You can also add variables for export to an MCF file using a CSV file. The CSV file should
    contain the variables you want to add.
    >>> dc_manager.add_variables_to_mcf_from_csv(file_path="path/to/file.csv")

    To add an input file and data to the config, using the explicit (per row) schema,
    use the add_variablePerRow_input_file method
    >>> dc_manager.add_explicit_schema_file(
    >>>    file_name="input_file.csv",
    >>>    provenance="Provenance Name",
    >>>    data=df,
    >>>    columnMappings={"entity": "Country", "date": "Year", "value": "Value"}
    >>>    )

    It isn't a requirement to add the data at the same time as the input file. You can add the data
    later using the add_data method. This is useful when you want to edit the config file
    without needing the data.

    To add data to the config, you can use the add_input_file and override the information already
    registered, or you can use the add_data method.
    Note: To add data, the input file must already be registered in the config file
    >>> dc_manager.add_data(<data>, "input_file.csv")

    To set the includeInputSubdirs and the groupStatVarsByProperty fields of the config, use
    the set_includeInputSubdirs and set_groupStatVarsByProperty methods
    >>> dc_manager.set_includeInputSubdirs(True)
    >>> dc_manager.set_groupStatVarsByProperty(True)

    Once you are ready to export the config and the data, use the exporter methods.
    Note that while the config is being edited (provenances, variables, input files being added)
    the config may not be valid. If any exporter method is called, the config will be
    validated and an error will be raised if the config is not valid.

    To export the config, data, and MCF file, use the export_all method
    >>> dc_manager.export_all("path/to/folder")

    To export the MCF file, use the export_mcf_file method
    >>> dc_manager.export_mfc_file("path/to/folder", file_name="custom_nodes.mcf")

    To export only the config, use the export_config method
    >>> dc_manager.export_config("path/to/config")

    or get the config as a dictionary using the config_to_dict method
    >>> dc_manager = dc_manager.config_to_dict()

    To export only the data, use the export_data method
    >>> dc_manager.export_data("path/to/data")
    """

    def __init__(
        self,
        config_file: str | PathLike[str] | None = None,
        mcf_files: str | Path | Sequence[str | Path] | None = None,
    ) -> None:
        """
        Initialize the CustomDataManager object
        Args:
            config_file: Path to the config json file. If not provided, a new config object will be created.
            mcf_files: Path to one or more MCF files. If not provided, a new MCFNodes object will be created.
        """

        self._config = (
            Config.from_json(config_file)
            if config_file
            else Config(inputFiles={}, sources={})
        )

        if mcf_files:
            # Normalize a single path to a one-element list.
            if isinstance(mcf_files, (str, Path)):
                paths = [Path(mcf_files)]
            else:
                paths = [Path(p) for p in mcf_files]

            self._mcf_nodes: dict[str, MCFNodes] = {
                path.name: MCFNodes().load_from_mcf_file(file_path=path)
                for path in paths
            }
        else:
            self._mcf_nodes: dict[str, MCFNodes] = {
                DEFAULT_STATVAR_MCF_NAME: MCFNodes()
            }

        self._data = {}

    def __repr__(self) -> str:
        input_files_count = len(self._config.inputFiles)
        sources_count = len(self._config.sources)
        nodes_count = sum(
            [len(var) for var in [n.nodes for n in self._mcf_nodes.values()] if var]
        )

        variables_count = nodes_count
        dataframes_count = len(self._data)

        include_input_subdirs = self._config.includeInputSubdirs
        group_statvars = self._config.groupStatVarsByProperty
        root_group_name = self._config.defaultCustomRootStatVarGroupName
        namespace = self._config.customIdNamespace
        svg_prefix = self._config.customSvgPrefix
        blocklist = self._config.svHierarchyPropsBlocklist

        return (
            f"<CustomDataManager config: "
            f"\n{input_files_count} inputFiles, with {dataframes_count} containing data"
            f"\n{sources_count} sources"
            f"\n{variables_count} variables"
            f"\nflags: includeInputSubdirs={include_input_subdirs}, "
            f"groupStatVarsByProperty={group_statvars}, "
            f"defaultCustomRootStatVarGroupName={root_group_name}, "
            f"customIdNamespace={namespace}, customSvgPrefix={svg_prefix}, "
            f"svHierarchyPropsBlocklist={blocklist}>"
        )

    def set_includeInputSubdirs(self, set_value: bool) -> CustomDataManager:
        """Set the includeInputSubdirs attribute of the config"""
        self._config.includeInputSubdirs = set_value
        return self

    def set_groupStatVarsByProperty(self, set_value: bool) -> CustomDataManager:
        """Set the groupStatVarsByProperty attribute of the config"""
        self._config.groupStatVarsByProperty = set_value
        return self

    def set_defaultCustomRootStatVarGroupName(
        self, name: str | None
    ) -> CustomDataManager:
        """Set the default custom root StatVarGroup display name in the config."""

        self._config.defaultCustomRootStatVarGroupName = name
        return self

    def set_customIdNamespace(
        self, namespace: str | None, *, update_svg_prefix: bool = True
    ) -> CustomDataManager:
        """Set the namespace for generated custom Statistical Variables and groups.

        Args:
            namespace: Namespace token to use. Pass ``None`` to unset.
            update_svg_prefix: Automatically set ``customSvgPrefix`` to
                ``"<namespace>/g/"`` when the prefix isn't explicitly defined yet.
                Defaults to ``True``.
        """

        self._config.customIdNamespace = namespace

        if update_svg_prefix and namespace and not self._config.customSvgPrefix:
            self._config.customSvgPrefix = f"{namespace}/g/"

        return self

    def set_customSvgPrefix(self, prefix: str | None) -> CustomDataManager:
        """Set the prefix used for generated custom StatVarGroup IDs."""

        self._config.customSvgPrefix = prefix
        return self

    def set_svHierarchyPropsBlocklist(
        self, blocklist: list[str] | None
    ) -> CustomDataManager:
        """Set the StatVar hierarchy property blocklist.

        Duplicate entries are removed while preserving the original order.
        Pass ``None`` to unset the blocklist.
        """

        if blocklist is None:
            self._config.svHierarchyPropsBlocklist = None
        else:
            seen: set[str] = set()
            deduped: list[str] = []
            for prop in blocklist:
                if prop not in seen:
                    seen.add(prop)
                    deduped.append(prop)
            self._config.svHierarchyPropsBlocklist = deduped
        return self

    def add_provenance(
        self,
        provenance_name: str,
        provenance_url: HttpUrl | str,
        source_name: str,
        source_url: HttpUrl | str | None = None,
        override: bool = False,
    ) -> CustomDataManager:
        """Add a provenance to the config

        Add a provenance (optionally with a new source) to the sources section of the config
        file. If the source does not exist, it will be added but a source URL must be provided.
        If the source exists, the provenance will be added to the existing source.
        If the provenance already exists, it will be overwritten if override is set to True.

        Args:
            provenance_name: Name of the provenance
            provenance_url: URL of the provenance
            source_name: Name of the source
            source_url: URL of the source (optional)
            override: If True, overwrite the existing provenance if it exists. Defaults to False.

        Raises:
            ValueError: If the source does not exist and no source URL is provided,
                or if the provenance already exists and override is not set to True.
        """

        if source_name not in self._config.sources:
            if source_url is None:
                raise ValueError(
                    f"Source '{source_name}' not found. "
                    "Please provide a source URL so the source can be added."
                )
            self._config.sources[source_name] = Source(
                url=HttpUrl(source_url),
                provenances={provenance_name: HttpUrl(provenance_url)},
            )

        else:
            if (
                provenance_name in self._config.sources[source_name].provenances
                and not override
            ):
                raise ValueError(
                    f"Provenance '{provenance_name}' already exists for source '{source_name}'. "
                    "Use override=True to overwrite it."
                )
            self._config.sources[source_name].provenances[provenance_name] = HttpUrl(
                provenance_url
            )

        return self

    def add_variable_to_mcf(
        self,
        *,
        Node: str,
        name: str,
        memberOf: list[str] | str | None = None,
        statType: str | StatType | None = None,
        shortDisplayName: str | None = None,
        description: str | None = None,
        searchDescription: list[str] | str | None = None,
        provenance: str | None = None,
        populationType: str | None = None,
        measuredProperty: str | None = None,
        measurementQualifier: str | None = None,
        measurementDenominator: str | None = None,
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_STATVAR_MCF_NAME,
    ) -> CustomDataManager:
        """Add a StatVar node for the MCF file

        Args:
            Node: The identifier of the statistical variable.
            name: Name of the variable (Optional)
            memberOf: Member of group for the variable (Optional)
            statType: Type of the statistical variable (Optional)
            shortDisplayName: Short display name of the variable (Optional)
            description: Description of the variable (Optional)
            searchDescription: Search description of the variable (Optional)
            provenance: Provenance of the variable (Optional)
            populationType: Population type of the variable (Optional)
            measuredProperty: Measured property of the variable (Optional)
            measurementQualifier: Measurement qualifier of the variable (Optional)
            measurementDenominator: Measurement denominator of the variable (Optional)
            additional_properties: Additional properties for the variable,
                passed as a dictionary with the target property as key.(Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf). Defaults to "custom_nodes.mcf".

        Returns:
            CustomDataManager object
        """

        props = _parse_kwargs_into_properties(locals())
        node = StatVarMCFNode(**props)

        name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(name, MCFNodes()).add(node, override=override)

        return self

    def add_variable_group_to_mcf(
        self,
        *,
        Node: str,
        name: str,
        specializationOf: str,
        description: str | None = None,
        provenance: str | None = None,
        shortDisplayName: str | None = None,
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_GROUP_NAME,
    ) -> CustomDataManager:
        """Add a StatVarGroup node for the MCF file

        Args:
            Node: DCID of the group you are defining. It must be prefixed by g/ and may include
                an additional prefix before the g.
            name: This is the name of the heading that will appear in the Statistical Variable Explorer.
            specializationOf: Specialization of the variable group. For a top-level group,
                this must be dcid:dc/g/Root, which is the root group in the statistical
                variable hierarchy in the Knowledge Graph.To create a sub-group, specify the
                DCID of another node you have already defined.
            description: Description of the variable group (Optional)
            provenance: Provenance of the variable group (Optional)
            shortDisplayName: Short display name of the variable group (Optional)
            additional_properties: Additional properties for the variable group,
                passed as a dictionary with the target property as key.(Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf). Defaults to "custom_groups.mcf".

        Returns:
            CustomDataManager object
        """
        props = _parse_kwargs_into_properties(locals())

        node = StatVarGroupMCFNode(**props)

        name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(name, MCFNodes()).add(node, override=override)
        return self

    def add_variables_to_mcf_from_csv(
        self,
        csv_file_path: str | Path,
        *,
        mcf_file_name: MCFFileName | str = DEFAULT_STATVAR_MCF_NAME,
        column_to_property_mapping: dict[str, str] | None = None,
        parse_groups: bool = False,
        group_namespace: str | None = None,
        csv_options: dict[str, Any] | None = None,
        ignore_columns: list[str] | None = None,
        override: bool = False,
    ) -> CustomDataManager:
        """
        Read a CSV containing StatVar nodes and parse them into StatVarMCFNode objects.

        Args:
            csv_file_path: Path to the CSV file.
            mcf_file_name: Name of the MCF file. Defaults to "custom_nodes.mcf".
            column_to_property_mapping: Optional map from CSV column names to
                ``StatVarMCFNode`` attribute names.
            parse_groups: If True, parse groups into StatVar nodes. That means the `memberOf`
                attribute of each StatVar node in `stat_vars`, which is expected to be a
                slash-separated string path describing its group hierarchy
                (e.g.,"Economic/Employment/Unemployment"), gets transformed into StatVarGroupMCFNode
                objects for each group level. This sets up their parent-child relationships,
                and updates the original memberOf attribute to reference the deepest group DCID.
                Defaults to False.
            group_namespace: Namespace for the groups. If not provided, an empty string is used.
                This is only used if parse_groups is True.
            csv_options: Extra keyword arguments forwarded verbatim to
                ``pandas.read_csv``.
            ignore_columns: List of columns to ignore in the CSV file.
            override: If True, overwrite the existing nodes if they exist. Defaults to False.
        """
        stat_vars = csv_metadata_to_nodes(
            file_path=csv_file_path,
            column_to_property_mapping=column_to_property_mapping,
            csv_options=csv_options,
            ignore_columns=ignore_columns,
        )

        if parse_groups:
            if not group_namespace:
                group_namespace = ""
            stat_vars = build_stat_var_groups_from_strings(
                stat_vars, groups_namespace=group_namespace
            )
        elif group_namespace:
            raise ValueError(
                "group_namespace should not be set if parse_groups is False"
            )

        name = validate_mcf_file_name(mcf_file_name)
        for node in stat_vars.nodes:
            self._mcf_nodes.setdefault(name, MCFNodes()).add(node, override=override)

        return self

    def _data_override_check(self, file_name: str, override: bool) -> None:
        """Check if the data already exists and override is not set"""
        if file_name in self._data and not override:
            raise ValueError(
                f"Data for file '{file_name}' already exists. "
                "Use a different name or set override as `True`."
            )

    def add_explicit_schema_file(
        self,
        file_name: str,
        provenance: str,
        data: pd.DataFrame | None = None,
        columnMappings: dict[str, str] | None = None,
        ignoreColumns: list[str] | None = None,
        override: bool = False,
    ) -> CustomDataManager:
        """Add an inputFile to the config and optionally register the data as pandas DataFrame.

        This method registers an input file in the config. Optionally it also registers the
        data that accompanies the input file registered. The registration of the data is made
        optional in cases where a user wants to edit the config file without the
        accompanying data. The data can be registered later using the add data method.

        This method is for the explicit schema approach (variable per row). Read more about
        the explicit (variable-per-row) schema format here:
        https://docs.datacommons.org/custom_dc/custom_data.html


        Args:
            file_name: Name of the file (should be a .csv file)
            provenance: Provenance of the data. This should be the name of the provenance
                in the sources section of the config file. Use add_provenance to add a provenance
                to the config file.
            data: Data to register (optional)
            columnMappings: Column mappings. Match the headings in the CSV file to the allowed
                properties. Allowed keys are [entity, date, value, unit,
                scalingFactor, measurementMethod, observationPeriod].
            ignoreColumns: List of columns to ignore (optional)
            override: If True, overwrite the existing file if it exists. Defaults to False.

        """

        # check if the file already exists
        self._data_override_check(file_name=file_name, override=override)

        if columnMappings is None:
            columnMappings = {}

        self._config.inputFiles[file_name] = ExplicitSchemaFile(
            ignoreColumns=ignoreColumns,
            provenance=provenance,
            columnMappings=ColumnMappings(**columnMappings),
        )

        # if data is provided, register it
        if data is not None:
            self._data[file_name] = data

        return self

    def add_data(
        self, data: pd.DataFrame, file_name: str, override: bool = False
    ) -> CustomDataManager:
        """Add data to the config

        Args:
            data: Data to register
            file_name: Name of the file (should be a .csv file and have been
                registered in the config file)
            override: If True, overwrite the existing data if it exists.
        """

        if file_name not in self._config.inputFiles:
            raise ValueError(
                f"File '{file_name}' not found in the config file. Please register the "
                "file in the config file before adding data, using the "
                "add_explicit_schema_file method."
            )

        self._data_override_check(file_name=file_name, override=override)

        self._data[file_name] = data
        return self

    def rename_variable(
        self, old_name: str, new_name: str, *, mcf_file_name: str | None = None
    ) -> CustomDataManager:
        """Rename a variable across any loaded MCF files.

        Args:
            old_name: The name of the variable to rename.
            new_name: The new name for the variable.
            mcf_file_name: Optional name of the MCF file from which to rename the variable.
                If omitted, all managed MCF files are searched.
        Raises:
            ValueError: If the variable is not found in any searched MCF file, or if the
                new name already exists in any searched MCF file.

        """

        file_names = (
            [validate_mcf_file_name(mcf_file_name)]
            if mcf_file_name
            else list(self._mcf_nodes.keys())
        )

        found_old = any(
            node.Node == old_name
            for name in file_names
            for node in (self._mcf_nodes.get(name) or MCFNodes()).nodes
        )
        found_new = any(
            node.Node == new_name
            for name in file_names
            for node in (self._mcf_nodes.get(name) or MCFNodes()).nodes
        )

        if not found_old:
            raise ValueError(f"Variable '{old_name}' not found")
        if found_new:
            raise ValueError(f"Variable '{new_name}' already exists")

        for name in file_names:
            nodes = self._mcf_nodes.get(name)
            if not nodes:
                continue
            for idx, node in enumerate(nodes.nodes):
                if node.Node == old_name:
                    nodes.nodes[idx].Node = new_name

        return self

    def rename_provenance(self, old_name: str, new_name: str) -> CustomDataManager:
        """Rename a provenance and update all references.

        Args:
            old_name: The name of the provenance to rename.
            new_name: The new name for the provenance.
        Raises:
            ValueError: If the provenance is not found in the config or MCF files,
                or if the new name already exists.
        Raises:
            ValueError: If the provenance is not found in the config or MCF files,
                or if the new name already exists.

        """

        source = None
        for src in self._config.sources.values():
            if old_name in src.provenances:
                source = src
                break

        if source is None:
            raise ValueError(f"Provenance '{old_name}' not found")
        if new_name in source.provenances:
            raise ValueError(f"Provenance '{new_name}' already exists for source")

        source.provenances[new_name] = source.provenances.pop(old_name)

        for info in self._config.inputFiles.values():
            if info.provenance == old_name:
                info.provenance = new_name

        for nodes in self._mcf_nodes.values():
            for node in nodes.nodes:
                prov = getattr(node, "provenance", None)
                if prov in {old_name, f'"{old_name}"'}:
                    node.provenance = f'"{new_name}"'

        return self

    def rename_source(self, old_name: str, new_name: str) -> CustomDataManager:
        """Rename a source key in the config.

        Args:
            old_name: The name of the source to rename.
            new_name: The new name for the source.
        Raises:
            ValueError: If the source is not found in the config or MCF files,
                or if the new name already exists.

        """

        if old_name not in self._config.sources:
            raise ValueError(f"Source '{old_name}' not found")
        if new_name in self._config.sources:
            raise ValueError(f"Source '{new_name}' already exists")

        self._config.sources[new_name] = self._config.sources.pop(old_name)

        return self

    def remove_indicator(
        self, indicator_id: str, *, mcf_file_name: str | None = None
    ) -> CustomDataManager:
        """Remove a single indicator from the manager.

        This removes the indicator from any loaded MCF files. If
        ``mcf_file_name`` is provided, only that MCF file is searched;
        otherwise all MCF files will be inspected.

        Args:
            indicator_id: Identifier of the indicator/StatVar to remove.
            mcf_file_name: Optional name of the MCF file from which to remove the
                node. If omitted, all managed MCF files are searched.

        Raises:
            ValueError: If the indicator is not found in any MCF file.
        """

        found = False

        file_names = (
            [
                (
                    validate_mcf_file_name(mcf_file_name)
                    if mcf_file_name is not None
                    else None
                )
            ]
            if mcf_file_name
            else self._mcf_nodes.keys()
        )
        for name in file_names:
            nodes = self._mcf_nodes.get(name)
            if not nodes:
                continue
            try:
                nodes.remove(indicator_id)
                found = True
            except ValueError:
                pass

        if not found:
            raise ValueError(f"Indicator '{indicator_id}' not found")

        return self

    def remove_by_provenance(self, provenance: str) -> CustomDataManager:
        """Remove all files and indicators associated with a provenance."""

        removed = False

        files_to_remove = [
            f
            for f, info in self._config.inputFiles.items()
            if info.provenance == provenance
        ]
        for file_name in files_to_remove:
            self._config.inputFiles.pop(file_name)
            self._data.pop(file_name, None)
            removed = True

        for nodes in self._mcf_nodes.values():
            for node in list(nodes.nodes):
                if getattr(node, "provenance", None) == f'"{provenance}"':
                    nodes.remove(node.Node)
                    removed = True

        if not removed:
            raise ValueError(f"No data found for provenance '{provenance}'")

        return self

    def remove_provenance(self, provenance: str) -> CustomDataManager:
        """Remove a provenance and any associated data and references."""

        self.remove_by_provenance(provenance)

        found = False
        for source in self._config.sources.values():
            if provenance in source.provenances:
                del source.provenances[provenance]
                found = True

        if not found:
            raise ValueError(f"Provenance '{provenance}' not found in sources")

        return self

    def remove_by_source(self, source: str) -> CustomDataManager:
        """Remove all data associated with every provenance of a source."""

        if source not in self._config.sources:
            raise ValueError(f"Source '{source}' not found")

        for prov in list(self._config.sources[source].provenances.keys()):
            self.remove_by_provenance(prov)

        return self

    def remove_source(self, source: str) -> CustomDataManager:
        """Remove a source and all its provenances from the config and data."""

        self.remove_by_source(source)

        del self._config.sources[source]

        return self

    def export_config(self, dir_path: str | PathLike[str]) -> None:
        """Export the config to a JSON file

        Before exporting, the config is validated to ensure that all required fields
        are present and that the config is valid.

        Args:
            dir_path: Path to the directory where the config will be exported.

        Raises:
            ValueError: If the config is not valid
        """

        self._config.validate_config()

        output_path = Path(dir_path) / "config.json"
        with output_path.open("w") as f:
            f.write(
                self._config.model_dump_json(indent=4, exclude_none=True, by_alias=True)
            )

    def export_mfc_file(
        self,
        dir_path: str | PathLike[str],
        mcf_file_name: str = DEFAULT_STATVAR_MCF_NAME,
        override: bool = False,
    ) -> None:
        """Export the MCF file to a file

        Args:
            dir_path: Path to the directory where the MCF file will be exported.
            mcf_file_name: Name of the MCF file (must end in .mcf). Defaults to "custom_nodes.mcf".
            override: If True, overwrite the file if it exists. Defaults to False.
        """
        mcf_file_name = validate_mcf_file_name(mcf_file_name)

        output_path = Path(dir_path) / mcf_file_name

        nodes = self._mcf_nodes.get(mcf_file_name)
        if not nodes:
            raise ValueError(f"No data available for '{mcf_file_name}'")

        nodes.export_to_mcf_file(file_path=output_path, override=override)

    def config_to_dict(self) -> dict:
        """Export the config to a dictionary

        Before exporting, the config is validated to ensure that all required fields are
        present and that the config is valid.

        Returns:
            Dict: The config as a dictionary

        Raises:
            ValueError: If the config is not valid
        """

        self._config.validate_config()

        return self._config.model_dump(mode="json", exclude_none=True)

    def export_data(self, dir_path: str | PathLike[str]) -> None:
        """Export the data to CSV files

        Args:
            dir_path: Path to the directory where the data will be exported.
        """

        if not self._data:
            raise ValueError("No data to export")

        for file, data in self._data.items():
            data.to_csv(Path(dir_path) / file, index=False)

    def validate_all_input_files_have_data(self) -> CustomDataManager:
        """Validate that every declared input file has a corresponding data entry.

        Raises:
            ValueError: If one or more input files declared in the config do not have
                associated data registered in this manager.
        """

        missing = [
            file_name
            for file_name in self._config.inputFiles
            if file_name not in self._data
        ]
        if missing:
            raise ValueError(
                f"The following input files declared in the config have no corresponding "
                f"data: {missing}. Use add_data() or pass data= when registering the "
                f"input file."
            )
        return self

    def export_all(
        self,
        dir_path: str | PathLike[str],
        override: bool = False,
        mcf_file_names: str | list[str] | None = None,
        validate_data: bool = False,
    ) -> None:
        """Export the config, MCF file, and data to a directory

        Args:
            dir_path: Path to the directory where the config and data will be exported.
            override: If True, overwrite the files if they exist. Defaults to False.
            mcf_file_names: Name of the MCF file(s) to export (must end in .mcf).
                Defaults to None, which means no MCF file will be exported.
            validate_data: If True, raise a ValueError before exporting if any input
                file declared in the config does not have a corresponding data entry.
                Defaults to False.
        """

        if validate_data:
            self.validate_all_input_files_have_data()

        self.export_config(dir_path)

        self.export_data(dir_path)

        if mcf_file_names:
            if isinstance(mcf_file_names, str):
                mcf_file_names = [mcf_file_names]
            for mcf_file_name in mcf_file_names:
                self.export_mfc_file(
                    dir_path=dir_path, mcf_file_name=mcf_file_name, override=override
                )

    def validate_config(self) -> CustomDataManager:
        """Validate the config

        This method checks the config for any issues and ensuring all the fields and values are valid. It raises
        an error if there are any issues with the config.

        Raises:
            pydantic.ValidationError if the config is not valid
        """

        self._config.validate_config()
        return self

    def merge_config(
        self,
        config: Config | dict | str | PathLike[str],
        *,
        policy: DuplicatePolicy = "error",
    ) -> CustomDataManager:
        """Merge ``config`` into the current configuration.

        Args:
            config: The config to merge. This can be a Config object, a dictionary,
                or a path to a JSON file.
            policy: How to resolve collisions. Can be "error", "override", or "ignore".
                Defaults to "error". If "error", an error is raised if there are any
                collisions. If "override", the new config will override the existing
                config. If "ignore", the new config's value will be ignored if there are any
                collisions.

        """

        if isinstance(config, (str, PathLike)):
            cfg = Config.from_json(str(config))
        elif isinstance(config, dict):
            cfg = Config.model_validate(config)
        else:
            cfg = config

        merge_configs(existing=self._config, new=cfg, policy=policy)
        return self

    def merge_configs_from_directory(
        self,
        directory: str | PathLike[str],
        *,
        policy: DuplicatePolicy = "error",
        replace_loaded_config: bool = True,
    ) -> CustomDataManager:
        """Merge all config files in a directory and its subdirectories

        This method will recursively search for config files in a directory and its
        subdirectories and merge them with the config already in the manager.
        If no config exists in the manager, it will be created from the merged config files.

        Args:
            directory: The directory to search for config files.
            policy: How to resolve collisions. Can be "error", "override", or "ignore".
                Defaults to "error". If "error", an error is raised if there are any
                collisions. If "override", the new config will override the existing
                config. If "ignore", the new config's value will be ignored if there are any
                collisions.

        """

        directory_configs = merge_configs_from_directory(
            directory=directory, policy=policy
        )

        if replace_loaded_config:
            self._config = directory_configs
        else:
            self.merge_config(directory_configs, policy=policy)

        return self

    @classmethod
    def from_config_files_in_directory(
        cls,
        directory: str | PathLike[str],
        *,
        policy: DuplicatePolicy = "error",
        mcf_files: str | Path | Sequence[str | Path] | None = None,
    ) -> CustomDataManager:
        """Create a manager loading and merging configs from ``directory``. This will
        recursively search for config files in subdirectories. It will merge them to create
        a single config. The config will be loaded into the manager.

        Args:
            directory: The directory to search for config files.
            policy: How to resolve collisions. Can be "error", "override", or "ignore".
            mcf_files: Path to one or more MCF files. If not provided, a new MCFNodes object
                will be created.

        Returns:
            CustomDataManager: A new instance of the CustomDataManager class with the
                loaded config and MCF files.

        """

        manager = cls(mcf_files=mcf_files)
        manager.merge_configs_from_directory(
            directory, policy=policy, replace_loaded_config=True
        )
        return manager
