"""Module to work with Data Commons CustomDataManager"""

from __future__ import annotations

import json
from collections.abc import Sequence
from os import PathLike
from pathlib import Path
from typing import Any

import pandas as pd

from dcp_tools.custom_data.config_utils import (
    DuplicatePolicy,
    merge_configs,
    merge_configs_from_directory,
)
from dcp_tools.custom_data.models.common import ensure_dcid, mint_dcid
from dcp_tools.custom_data.models.config_file import Config
from dcp_tools.custom_data.models.data_files import (
    ColumnMappings,
    InputFile,
    MCFFileName,
    ObservationProperties,
)
from dcp_tools.custom_data.models.mcf import Node, Nodes
from dcp_tools.custom_data.models.schema_nodes import (
    EntityTypeNode,
    EventTypeNode,
    MeasurementMethodNode,
    PropertyNode,
    UnitOfMeasureNode,
)
from dcp_tools.custom_data.models.sources import ProvenanceNode, SourceNode
from dcp_tools.custom_data.models.stat_vars import (
    StatType,
    StatVarGroupNode,
    StatVarNode,
)
from dcp_tools.custom_data.models.vertical_specs import VerticalSpec
from dcp_tools.custom_data.schema_tools import (
    csv_metadata_to_nodes,
    validate_mcf_file_name,
)

DEFAULT_STATVAR_MCF_NAME: str = "custom_nodes.mcf"
DEFAULT_GROUP_NAME: str = "custom_groups.mcf"
DEFAULT_PROVENANCE_MCF_NAME: str = "provenance.mcf"
DEFAULT_VERTICAL_SPECS_NAME: str = "vertical_specs.json"


def _parse_kwargs_into_properties(
    locals_dict: dict[str, Any], *, extra_exclude: set[str] | None = None
) -> dict[str, Any]:
    """Parse a dictionary of keyword arguments into a dictionary of properties"""

    exclude = {"self", "additional_properties", "override", "mcf_file_name"}
    if extra_exclude:
        exclude |= extra_exclude

    props = {k: v for k, v in locals_dict.items() if k not in exclude and v is not None}

    if "additional_properties" in locals_dict:
        additional = locals_dict.get("additional_properties", {})
        if additional:
            props.update(additional)

    return props


class CustomDataManager:
    """Class to handle the config json, data, and MCF files for Custom Data Commons

    Args:
        config_file: Path to the config json file. If not provided, a new config object will be created.
        mcf_files: Path to one or more MCF files. If not provided, a new Nodes object will be created.

    Usage:

    To start instantiate the object with or without an existing config json and MCF file
    >>> dc_manager = CustomDataManager()
    or
    >>> dc_manager = CustomDataManager(config_file="path/to/config.json", mcf_file="path/to/mcf_file.mcf")

    Source/Provenance (MCF):

    To add a Source and Provenance (emitted as MCF nodes to ``provenance.mcf`` by default),
    use the ``add_source`` and ``add_provenance`` methods:
    >>> dc_manager.add_source(dcid="ONEData", name="ONE Data", url="https://data.one.org")
    >>> dc_manager.add_provenance(
    >>>     dcid="ONEClimateFinance",
    >>>     name="ONE Climate Finance",
    >>>     url="https://datacommons.one.org/data/climate-finance-files",
    >>>     source="ONEData",
    >>> )

    To add a variable for export to an MCF file, use the add_variable_to_mcf method.
    ``dcid`` accepts a bare or ``dcid:``-prefixed token, as the schema-node builders below do:
    >>> dc_manager.add_variable_to_mcf(
    >>>    dcid="StatVar",
    >>>    name="Variable Name",
    >>>    description="Variable Description",
    >>>    ...
    >>>    )

    Schema nodes (MCF):

    To add custom schema nodes (entity types, event types, properties, units, and
    measurement methods), use the five typed builders. All five accept bare or
    ``dcid:``-prefixed ``dcid`` tokens. Note: ``add_measurement_method`` is the only
    builder where ``name`` is optional — only ``dcid`` is required.
    >>> dc_manager.add_entity_type(dcid="MyClass", name="My Class")
    >>> dc_manager.add_event_type(dcid="MyEvent", name="My Event")
    >>> dc_manager.add_property(
    >>>     dcid="myProp",
    >>>     name="My Property",
    >>>     domain_includes="Person",
    >>>     range_includes="Number",
    >>> )
    >>> dc_manager.add_unit(dcid="USD", name="US Dollar", short_display_name="$")
    >>> dc_manager.add_measurement_method(dcid="MyCensus")

    You can also add variables for export to an MCF file using a CSV file. The CSV file should
    contain the variables you want to add.
    >>> dc_manager.add_variables_to_mcf_from_csv(file_path="path/to/file.csv")

    To add an input file and data to the config, use the add_input_file method
    >>> dc_manager.add_input_file(
    >>>    file_name="input_file.csv",
    >>>    provenance="Provenance Name",
    >>>    data=df,
    >>>    column_mappings={"observationAbout": "Country", "date": "Year", "value": "Value"}
    >>>    )

    For multi-entity observations, map each dimension with a ``custom:<name>`` key, and declare the
    matching ``dcid:<name>`` properties on the StatVar:
    >>> dc_manager.add_input_file(
    >>>    file_name="input_file.csv",
    >>>    provenance="Provenance Name",
    >>>    data=df,
    >>>    column_mappings={
    >>>        "variable": "Var",
    >>>        "date": "Year",
    >>>        "value": "Value",
    >>>        "custom:originCountry": "Provider",
    >>>        "custom:destinationCountry": "Recipient",
    >>>    },
    >>> )
    >>> dc_manager.add_variable_to_mcf(
    >>>    dcid="dcid:var/StatVar",
    >>>    name="Variable Name",
    >>>    observation_properties=["dcid:originCountry", "dcid:destinationCountry"],
    >>> )

    It isn't a requirement to add the data at the same time as the input file. You can add the data
    later using the add_data method. This is useful when you want to edit the config file
    without needing the data.

    To add data to the config, you can use the add_input_file and override the information already
    registered, or you can use the add_data method.
    Note: To add data, the input file must already be registered in the config file
    >>> dc_manager.add_data(<data>, "input_file.csv")

    To set the ``include_input_subdirs`` and ``group_stat_vars_by_property`` config fields, use
    the set_include_input_subdirs and set_group_stat_vars_by_property methods
    >>> dc_manager.set_include_input_subdirs(True)
    >>> dc_manager.set_group_stat_vars_by_property(True)

    Once you are ready to export the config and the data, use the exporter methods.
    Note that while the config is being edited (provenances, variables, input files being added)
    the config may not be valid. If any exporter method is called, the config will be
    validated and an error will be raised if the config is not valid.

    To export the config, data, and MCF file, use the export_all method
    >>> dc_manager.export_all("path/to/folder")

    To export the MCF file, use the export_mcf_file method
    >>> dc_manager.export_mcf_file("path/to/folder", mcf_file_name="custom_nodes.mcf")

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
            mcf_files: Path to one or more MCF files. If not provided, a new Nodes object will be created.
        """

        self._config = (
            Config.from_json(config_file) if config_file else Config(input_files=[])
        )

        if mcf_files:
            # Normalize a single path to a one-element list.
            if isinstance(mcf_files, (str, Path)):
                paths = [Path(mcf_files)]
            else:
                paths = [Path(p) for p in mcf_files]

            self._mcf_nodes: dict[str, Nodes] = {
                path.name: Nodes().load_from_mcf_file(file_path=path) for path in paths
            }
        else:
            self._mcf_nodes: dict[str, Nodes] = {DEFAULT_STATVAR_MCF_NAME: Nodes()}

        self._data = {}
        self._vertical_specs: list[VerticalSpec] = []

    def __repr__(self) -> str:
        input_files_count = len(self._config.input_files)

        all_nodes = [n for nodes in self._mcf_nodes.values() for n in nodes.nodes]
        sources_count = sum(1 for n in all_nodes if n.type_of == "dcid:Source")
        provenances_count = sum(1 for n in all_nodes if n.type_of == "dcid:Provenance")
        variables_count = len(all_nodes) - sources_count - provenances_count

        dataframes_count = len(self._data)
        vertical_specs_count = len(self._vertical_specs)

        import_name = self._config.import_name
        include_input_subdirs = self._config.include_input_subdirs
        group_statvars = self._config.group_stat_vars_by_property
        root_group_name = self._config.default_custom_root_stat_var_group_name
        namespace = self._config.custom_id_namespace
        svg_prefix = self._config.custom_svg_prefix
        blocklist = self._config.sv_hierarchy_props_blocklist
        data_download_url = self._config.data_download_url
        vertical_specs_file = self._config.vertical_specs_file

        return (
            f"<CustomDataManager config: "
            f"\n{input_files_count} inputFiles, with {dataframes_count} containing data"
            f"\n{sources_count} sources"
            f"\n{provenances_count} provenances"
            f"\n{variables_count} variables"
            f"\n{vertical_specs_count} vertical specs"
            f"\nflags: importName={import_name}, "
            f"includeInputSubdirs={include_input_subdirs}, "
            f"groupStatVarsByProperty={group_statvars}, "
            f"defaultCustomRootStatVarGroupName={root_group_name}, "
            f"customIdNamespace={namespace}, customSvgPrefix={svg_prefix}, "
            f"svHierarchyPropsBlocklist={blocklist}, "
            f"dataDownloadUrl={data_download_url}, "
            f"verticalSpecsFile={vertical_specs_file}>"
        )

    def set_import_name(self, name: str | None) -> CustomDataManager:
        """Set the import name in the config.

        The import name is used by the platform prep job to name the JSON-LD output
        directory. Pass ``None`` to unset it; ``export_config`` then defaults it to the
        export directory name.
        """
        self._config.import_name = name
        return self

    def set_include_input_subdirs(self, set_value: bool) -> CustomDataManager:
        """Set the includeInputSubdirs attribute of the config"""
        self._config.include_input_subdirs = set_value
        return self

    def set_group_stat_vars_by_property(self, set_value: bool) -> CustomDataManager:
        """Set the groupStatVarsByProperty attribute of the config"""
        self._config.group_stat_vars_by_property = set_value
        return self

    def set_default_custom_root_stat_var_group_name(
        self, name: str | None
    ) -> CustomDataManager:
        """Set the default custom root StatVarGroup display name in the config."""

        self._config.default_custom_root_stat_var_group_name = name
        return self

    def set_custom_id_namespace(
        self, namespace: str | None, *, update_svg_prefix: bool = True
    ) -> CustomDataManager:
        """Set the namespace for generated custom Statistical Variables and groups.

        Args:
            namespace: Namespace token to use. Pass ``None`` to unset.
            update_svg_prefix: Automatically set ``customSvgPrefix`` to
                ``"<namespace>/g/"`` when the prefix isn't explicitly defined yet.
                Defaults to ``True``.
        """

        self._config.custom_id_namespace = namespace

        if update_svg_prefix and namespace and not self._config.custom_svg_prefix:
            self._config.custom_svg_prefix = f"{namespace}/g/"

        return self

    def set_custom_svg_prefix(self, prefix: str | None) -> CustomDataManager:
        """Set the prefix used for generated custom StatVarGroup IDs."""

        self._config.custom_svg_prefix = prefix
        return self

    def set_sv_hierarchy_props_blocklist(
        self, blocklist: list[str] | None
    ) -> CustomDataManager:
        """Set the StatVar hierarchy property blocklist.

        Duplicate entries are removed while preserving the original order.
        Pass ``None`` to unset the blocklist.
        """

        if blocklist is None:
            self._config.sv_hierarchy_props_blocklist = None
        else:
            seen: set[str] = set()
            deduped: list[str] = []
            for prop in blocklist:
                if prop not in seen:
                    seen.add(prop)
                    deduped.append(prop)
            self._config.sv_hierarchy_props_blocklist = deduped
        return self

    def set_data_download_url(self, urls: list[str] | None) -> CustomDataManager:
        """Set the data download URLs in the config.

        Replaces any existing list. Pass ``None`` to unset the field (absent from the
        exported ``config.json``).
        """
        self._config.data_download_url = urls
        return self

    def add_data_download_url(self, url: str) -> CustomDataManager:
        """Append a single data download URL to the config.

        Initializes the list to ``[url]`` when the field is unset.
        """
        existing = self._config.data_download_url or []
        self._config.data_download_url = [*existing, url]
        return self

    def set_vertical_specs_file(self, file_name: str | None) -> CustomDataManager:
        """Set the vertical-specs filename in the config.

        Plain filename string (no ``.json``-suffix enforcement). Pass ``None`` to unset.
        """
        self._config.vertical_specs_file = file_name
        return self

    def add_vertical_spec(
        self,
        *,
        verticals: list[str],
        population_type: str = "Thing",
        measured_properties: list[str] | None = None,
        file_name: str | None = None,
    ) -> CustomDataManager:
        """Add a vertical-specs entry guiding StatVar hierarchy generation.

        Appends one spec to the vertical-specs file written by ``export_all`` (or
        ``export_vertical_specs``) and points the config's ``verticalSpecsFile`` at the
        file. The importer reads it only when ``groupStatVarsByProperty`` is set.

        The config's ``verticalSpecsFile`` is set to ``file_name`` when given; otherwise
        it defaults to ``"vertical_specs.json"`` on first use and an existing value
        (e.g. one set via ``set_verticalSpecsFile``) is left untouched.

        Args:
            verticals: Vertical (top-level group) names to file matching stat vars under.
            population_type: Population type the spec applies to. Defaults to ``"Thing"``.
            measured_properties: Measured properties the spec applies to (optional).
            file_name: Name of the vertical-specs file to write. When omitted, uses the
                config's existing ``verticalSpecsFile`` or ``"vertical_specs.json"``.
        """
        self._vertical_specs.append(
            VerticalSpec(
                population_type=population_type,
                measured_properties=measured_properties or [],
                verticals=verticals,
            )
        )
        if file_name is not None:
            self._config.vertical_specs_file = file_name
        elif self._config.vertical_specs_file is None:
            self._config.vertical_specs_file = DEFAULT_VERTICAL_SPECS_NAME
        return self

    def add_source(
        self,
        *,
        dcid: str,
        url: str,
        name: str | None = None,
        description: str | None = None,
        license: str | None = None,
        is_part_of: str | None = None,
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_PROVENANCE_MCF_NAME,
    ) -> CustomDataManager:
        """Add a Source MCF node.

        Emits a ``dcid:Source`` node to the MCF collection (default: ``provenance.mcf``).
        The node is referenced by ``add_provenance`` via the same bare ``dcid`` token
        (passed to its ``source`` argument).

        Args:
            dcid: Identifier for the source node. Minting rule: bare token →
                ``dcid:source/<token>``; pass an already ``dcid:``-prefixed value to use
                it verbatim. Must be a valid dcid token (no whitespace).
            url: URL of the data source.
            name: Optional human-readable name of the source. (Optional)
            description: Optional human-readable description. (Optional)
            license: Optional license information. (Optional)
            is_part_of: Optional DCID of a parent source. (Optional)
            additional_properties: Additional MCF properties, passed as a dictionary
                with the target property as key. (Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf).
                Defaults to ``"provenance.mcf"``.

        Returns:
            CustomDataManager object

        Raises:
            ValueError: If the ``dcid`` token contains whitespace, if a node with the same
                id already exists and ``override`` is False, or if the file name is invalid.
        """

        dcid = mint_dcid(prefix="source", token=dcid)
        url = str(url)
        props = _parse_kwargs_into_properties(locals())
        node = SourceNode(**props)

        mcf_name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(mcf_name, Nodes()).add(node, override=override)

        return self

    def add_provenance(
        self,
        *,
        dcid: str,
        url: str,
        source: str,
        name: str | None = None,
        description: str | None = None,
        license: str | None = None,
        license_type: str | None = None,
        last_data_refresh_date: str | None = None,
        next_data_refresh_date: str | None = None,
        next_source_release_date: str | None = None,
        source_release_frequency: str | None = None,
        earliest_observation_date: str | None = None,
        latest_observation_date: str | None = None,
        curator: str | None = None,
        is_part_of: str | None = None,
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_PROVENANCE_MCF_NAME,
    ) -> CustomDataManager:
        """Add a Provenance MCF node linked to an existing Source.

        Emits a ``dcid:Provenance`` node to the MCF collection (default: ``provenance.mcf``).
        The corresponding Source must already be registered via ``add_source``.

        Args:
            dcid: Identifier for the provenance node. Minting rule: bare token →
                ``dcid:provenance/<token>``; pass an already ``dcid:``-prefixed value to
                use it verbatim. Must be a valid dcid token (no whitespace).
            url: URL of the provenance dataset.
            source: Bare name of the parent Source (must already have been added via
                ``add_source``). The same minting rule applies: bare name →
                ``dcid:source/<source>``; ``dcid:``-prefixed → verbatim.
            name: Optional human-readable name of the provenance. (Optional)
            description: Optional human-readable description. (Optional)
            license: Optional license information. (Optional)
            license_type: Optional license type. (Optional)
            last_data_refresh_date: Optional date of last data refresh. (Optional)
            next_data_refresh_date: Optional date of next expected data refresh. (Optional)
            next_source_release_date: Optional date of next source release. (Optional)
            source_release_frequency: Optional frequency of source releases. (Optional)
            earliest_observation_date: Optional earliest observation date. (Optional)
            latest_observation_date: Optional latest observation date. (Optional)
            curator: Optional curator of the dataset. (Optional)
            is_part_of: Optional DCID of a parent provenance. (Optional)
            additional_properties: Additional MCF properties, passed as a dictionary
                with the target property as key. (Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf).
                Defaults to ``"provenance.mcf"``.

        Returns:
            CustomDataManager object

        Raises:
            ValueError: If the ``source`` has not been added yet, if the ``dcid`` or
                ``source`` token contains whitespace, if a node with the same id already
                exists and ``override`` is False, or if the file name is invalid.
        """

        dcid = mint_dcid(prefix="provenance", token=dcid)
        url = str(url)
        source_link = mint_dcid(prefix="source", token=source)
        self._require_source_exists(source, source_link)
        props = _parse_kwargs_into_properties(locals(), extra_exclude={"source"})
        node = ProvenanceNode(**props)

        mcf_name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(mcf_name, Nodes()).add(node, override=override)

        return self

    def add_variable_to_mcf(
        self,
        *,
        dcid: str,
        name: str,
        member_of: list[str] | str | None = None,
        stat_type: str | StatType | None = None,
        short_display_name: str | None = None,
        description: str | None = None,
        search_description: list[str] | str | None = None,
        provenance: str | None = None,
        population_type: str | None = None,
        measured_property: str | None = None,
        measurement_qualifier: str | None = None,
        measurement_denominator: str | None = None,
        observation_properties: list[str] | None = None,
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_STATVAR_MCF_NAME,
    ) -> CustomDataManager:
        """Add a StatVar node for the MCF file

        Args:
            dcid: The identifier of the statistical variable. A bare token is
                normalized to ``dcid:<token>`` and an already ``dcid:``-prefixed token
                is kept as-is; either way whitespace raises ``ValueError``. The same
                applies to ``populationType``, ``measuredProperty``,
                ``measurementQualifier`` and ``measurementDenominator``.
            name: Name of the variable (Optional)
            member_of: Member of group for the variable (Optional)
            stat_type: Type of the statistical variable (Optional)
            short_display_name: Short display name of the variable (Optional)
            description: Description of the variable (Optional)
            search_description: Search description of the variable (Optional)
            provenance: Provenance of the variable (Optional)
            population_type: Population type of the variable (Optional)
            measured_property: Measured property of the variable (Optional)
            measurement_qualifier: Measurement qualifier of the variable (Optional)
            measurement_denominator: Measurement denominator of the variable (Optional)
            observation_properties: For multi-entity data, the list of dcid:-prefixed properties
                that apply to observations, one per custom dimension (Optional)
            additional_properties: Additional properties for the variable,
                passed as a dictionary with the target property as key.(Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf). Defaults to "custom_nodes.mcf".

        Returns:
            CustomDataManager object
        """

        dcid = ensure_dcid(dcid)
        if population_type is not None:
            population_type = ensure_dcid(population_type)
        if measured_property is not None:
            measured_property = ensure_dcid(measured_property)
        if measurement_qualifier is not None:
            measurement_qualifier = ensure_dcid(measurement_qualifier)
        if measurement_denominator is not None:
            measurement_denominator = ensure_dcid(measurement_denominator)

        props = _parse_kwargs_into_properties(locals())
        node = StatVarNode(**props)

        name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(name, Nodes()).add(node, override=override)

        return self

    def add_variable_group_to_mcf(
        self,
        *,
        dcid: str,
        name: str,
        specialization_of: str,
        description: str | None = None,
        provenance: str | None = None,
        short_display_name: str | None = None,
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_GROUP_NAME,
    ) -> CustomDataManager:
        """Add a StatVarGroup node for the MCF file

        Args:
            dcid: DCID of the group you are defining. It must be prefixed by g/ and may include
                an additional prefix before the g.
            name: This is the name of the heading that will appear in the Statistical Variable Explorer.
            specialization_of: Specialization of the variable group. For a top-level group,
                this must be dcid:dc/g/Root, which is the root group in the statistical
                variable hierarchy in the Knowledge Graph.To create a sub-group, specify the
                DCID of another node you have already defined.
            description: Description of the variable group (Optional)
            provenance: Provenance of the variable group (Optional)
            short_display_name: Short display name of the variable group (Optional)
            additional_properties: Additional properties for the variable group,
                passed as a dictionary with the target property as key.(Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf). Defaults to "custom_groups.mcf".

        Returns:
            CustomDataManager object
        """
        props = _parse_kwargs_into_properties(locals())

        node = StatVarGroupNode(**props)

        name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(name, Nodes()).add(node, override=override)
        return self

    def add_entity_type(
        self,
        *,
        dcid: str,
        name: str,
        description: str | None = None,
        included_in: str | list[str] | None = None,
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_STATVAR_MCF_NAME,
    ) -> CustomDataManager:
        """Add a custom entity-type (Class) MCF node.

        Emits a ``dcid:Class`` node to the MCF collection (default: ``custom_nodes.mcf``).

        Args:
            dcid: Identifier token for the Class. Bare tokens are normalized to
                ``dcid:<token>`` (e.g. ``"MyClass"`` → ``"dcid:MyClass"``); already
                ``dcid:``-prefixed values are passed through verbatim. Names must be
                valid dcid tokens (no whitespace).
            name: Human-readable name for the entity type.
            description: Optional human-readable description. (Optional)
            included_in: Bare provenance name (or list of names) the entity type is
                defined in. **Important:** this takes the bare provenance name (not a
                dcid, unlike the other ref params). The provenance must already be
                registered via ``add_provenance``. The builder emits ``includedIn`` for
                **both** the provenance and its linked Source (one bare name → two
                dcids out). (Optional)
            additional_properties: Additional MCF properties, passed as a dictionary
                with the target property as key. (Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf).
                Defaults to ``"custom_nodes.mcf"``.

        Returns:
            CustomDataManager object

        Raises:
            ValueError: If Node contains whitespace, if a node with the same id already
                exists and ``override`` is False, if the file name is invalid, or if any
                provenance referenced by ``includedIn`` has not been registered.
        """
        dcid = ensure_dcid(dcid)
        if included_in is not None:
            included_in = self._expand_included_in(included_in)
        props = _parse_kwargs_into_properties(locals())
        node = EntityTypeNode(**props)
        mcf_name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(mcf_name, Nodes()).add(node, override=override)
        return self

    def add_event_type(
        self,
        *,
        dcid: str,
        name: str,
        description: str | None = None,
        sub_class_of: str = "dcid:Event",
        included_in: str | list[str] | None = None,
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_STATVAR_MCF_NAME,
    ) -> CustomDataManager:
        """Add a custom event-type (Class) MCF node.

        Emits a ``dcid:Class`` node with ``subClassOf`` defaulting to ``dcid:Event``
        (default: ``custom_nodes.mcf``).

        Args:
            dcid: Identifier token for the event type. Bare tokens are normalized to
                ``dcid:<token>``; already ``dcid:``-prefixed values are passed through
                verbatim. Names must be valid dcid tokens (no whitespace).
            name: Human-readable name for the event type.
            description: Optional human-readable description. (Optional)
            sub_class_of: Parent class DCID. Bare tokens are normalized to ``dcid:<token>``.
                Defaults to ``"dcid:Event"``. (Optional)
            included_in: Bare provenance name (or list of names) the event type is
                defined in. **Important:** this takes the bare provenance name (not a
                dcid, unlike the other ref params). The provenance must already be
                registered via ``add_provenance``. The builder emits ``includedIn`` for
                **both** the provenance and its linked Source (one bare name → two
                dcids out). (Optional)
            additional_properties: Additional MCF properties, passed as a dictionary
                with the target property as key. (Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf).
                Defaults to ``"custom_nodes.mcf"``.

        Returns:
            CustomDataManager object

        Raises:
            ValueError: If Node contains whitespace, if a node with the same id already
                exists and ``override`` is False, if the file name is invalid, or if any
                provenance referenced by ``includedIn`` has not been registered.
        """
        dcid = ensure_dcid(dcid)
        sub_class_of = ensure_dcid(sub_class_of)
        if included_in is not None:
            included_in = self._expand_included_in(included_in)
        props = _parse_kwargs_into_properties(locals())
        node = EventTypeNode(**props)
        mcf_name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(mcf_name, Nodes()).add(node, override=override)
        return self

    def add_property(
        self,
        *,
        dcid: str,
        name: str,
        domain_includes: str | list[str] | None = None,
        range_includes: str | list[str] | None = None,
        sub_property_of: str | list[str] | None = None,
        description: str | None = None,
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_STATVAR_MCF_NAME,
    ) -> CustomDataManager:
        """Add a custom Property MCF node.

        Emits a ``dcid:Property`` node to the MCF collection (default: ``custom_nodes.mcf``).

        Args:
            dcid: Identifier token for the property. Bare tokens are normalized to
                ``dcid:<token>``; already ``dcid:``-prefixed values are passed through
                verbatim. Names must be valid dcid tokens (no whitespace).
            name: Human-readable name for the property.
            domain_includes: DCID(s) of classes the property applies to. Bare tokens or
                lists are normalized to ``dcid:`` (same as ``Node``); already
                ``dcid:``-prefixed values are passed through verbatim. (Optional)
            range_includes: DCID(s) of classes that are the value type. Bare tokens or
                lists are normalized to ``dcid:`` (same as ``Node``); already
                ``dcid:``-prefixed values are passed through verbatim. (Optional)
            sub_property_of: DCID(s) of parent properties. Bare tokens or lists are
                normalized to ``dcid:`` (same as ``Node``); already ``dcid:``-prefixed
                values are passed through verbatim. (Optional)
            description: Optional human-readable description. (Optional)
            additional_properties: Additional MCF properties, passed as a dictionary
                with the target property as key. (Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf).
                Defaults to ``"custom_nodes.mcf"``.

        Returns:
            CustomDataManager object

        Raises:
            ValueError: If Node contains whitespace, if a node with the same id already
                exists and ``override`` is False, or if the file name is invalid.
        """
        dcid = ensure_dcid(dcid)
        if domain_includes is not None:
            domain_includes = ensure_dcid(domain_includes)
        if range_includes is not None:
            range_includes = ensure_dcid(range_includes)
        if sub_property_of is not None:
            sub_property_of = ensure_dcid(sub_property_of)
        props = _parse_kwargs_into_properties(locals())
        node = PropertyNode(**props)
        mcf_name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(mcf_name, Nodes()).add(node, override=override)
        return self

    def add_unit(
        self,
        *,
        dcid: str,
        name: str,
        short_display_name: str | None = None,
        description: str | None = None,
        type_of: str = "dcid:UnitOfMeasure",
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_STATVAR_MCF_NAME,
    ) -> CustomDataManager:
        """Add a custom unit-of-measure MCF node.

        Emits a ``dcid:UnitOfMeasure`` node (or the overridden ``typeOf``) to the MCF
        collection (default: ``custom_nodes.mcf``).

        Args:
            dcid: Identifier token for the unit. Bare tokens are normalized to
                ``dcid:<token>``; already ``dcid:``-prefixed values are passed through
                verbatim. Names must be valid dcid tokens (no whitespace).
            name: Human-readable name for the unit.
            short_display_name: Optional short display name (e.g. ``"$"``). (Optional)
            description: Optional human-readable description. (Optional)
            type_of: Type DCID. Bare tokens are normalized to ``dcid:<token>``. Defaults to
                ``"dcid:UnitOfMeasure"``; override for sub-types such as
                ``"dcid:CurrencyUnitOfMeasure"``. (Optional)
            additional_properties: Additional MCF properties, passed as a dictionary
                with the target property as key. (Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf).
                Defaults to ``"custom_nodes.mcf"``.

        Returns:
            CustomDataManager object

        Raises:
            ValueError: If Node contains whitespace, if a node with the same id already
                exists and ``override`` is False, or if the file name is invalid.
        """
        dcid = ensure_dcid(dcid)
        type_of = ensure_dcid(type_of)
        props = _parse_kwargs_into_properties(locals())
        node = UnitOfMeasureNode(**props)
        mcf_name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(mcf_name, Nodes()).add(node, override=override)
        return self

    def add_measurement_method(
        self,
        *,
        dcid: str,
        name: str | None = None,
        description: str | None = None,
        type_of: str = "dcid:MeasurementMethodEnum",
        additional_properties: dict[str, str] | None = None,
        override: bool = False,
        mcf_file_name: MCFFileName | str = DEFAULT_STATVAR_MCF_NAME,
    ) -> CustomDataManager:
        """Add a custom measurement-method MCF node.

        Emits a ``dcid:MeasurementMethodEnum`` node (or the overridden ``typeOf``) to the
        MCF collection (default: ``custom_nodes.mcf``). Unlike the other four builders,
        ``name`` is optional here — only ``Node`` is required.

        Args:
            dcid: Identifier token for the measurement method. Bare tokens are normalized
                to ``dcid:<token>``; already ``dcid:``-prefixed values are passed through
                verbatim. Names must be valid dcid tokens (no whitespace).
            name: Optional human-readable name. (Optional)
            description: Optional human-readable description. (Optional)
            type_of: Measurement-method enum type DCID. Bare tokens are normalized to
                ``dcid:<token>``. Defaults to ``"dcid:MeasurementMethodEnum"``; override
                for sub-types such as ``"dcid:CensusSurveyEnum"``. (Optional)
            additional_properties: Additional MCF properties, passed as a dictionary
                with the target property as key. (Optional)
            override: If True, overwrite the existing node if it exists. Defaults to False.
            mcf_file_name: Name of the MCF file (must end in .mcf).
                Defaults to ``"custom_nodes.mcf"``.

        Returns:
            CustomDataManager object

        Raises:
            ValueError: If Node contains whitespace, if a node with the same id already
                exists and ``override`` is False, or if the file name is invalid.
        """
        dcid = ensure_dcid(dcid)
        type_of = ensure_dcid(type_of)
        props = _parse_kwargs_into_properties(locals())
        node = MeasurementMethodNode(**props)
        mcf_name = validate_mcf_file_name(mcf_file_name)
        self._mcf_nodes.setdefault(mcf_name, Nodes()).add(node, override=override)
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
        Read a CSV containing StatVar nodes and parse them into StatVarNode objects.

        Args:
            csv_file_path: Path to the CSV file.
            mcf_file_name: Name of the MCF file. Defaults to "custom_nodes.mcf".
            column_to_property_mapping: Optional map from CSV column names to
                ``StatVarNode`` attribute names.
            parse_groups: If True, parse groups into StatVar nodes. That means the `memberOf`
                attribute of each StatVar node in `stat_vars`, which is expected to be a
                slash-separated string path describing its group hierarchy
                (e.g.,"Economic/Employment/Unemployment"), gets transformed into StatVarGroupNode
                objects for each group level. This sets up their parent-child relationships,
                and updates the original memberOf attribute to reference the deepest group DCID.
                Defaults to False.
            group_namespace: Namespace for the groups. If not provided, an empty string is used.
                This is only used if parse_groups is True.
            csv_options: Extra keyword arguments forwarded verbatim to
                ``pandas.read_csv``.
            ignore_columns: List of columns to ignore in the CSV file.
            override: If True, overwrite the existing nodes if they exist. Defaults to False.

        Raises:
            ValueError: If ``group_namespace`` is set while ``parse_groups`` is False, or
                if ``parse_groups`` is True and the CSV has no ``memberOf`` column.
        """
        stat_vars = csv_metadata_to_nodes(
            file_path=csv_file_path,
            column_to_property_mapping=column_to_property_mapping,
            csv_options=csv_options,
            ignore_columns=ignore_columns,
            parse_groups=parse_groups,
            group_namespace=group_namespace,
        )

        if not parse_groups and group_namespace:
            raise ValueError(
                "group_namespace should not be set if parse_groups is False"
            )

        name = validate_mcf_file_name(mcf_file_name)
        for node in stat_vars.nodes:
            self._mcf_nodes.setdefault(name, Nodes()).add(node, override=override)

        return self

    def _data_override_check(self, file_name: str, override: bool) -> None:
        """Check if the data already exists and override is not set"""
        if file_name in self._data and not override:
            raise ValueError(
                f"Data for file '{file_name}' already exists. "
                "Use a different name or set override as `True`."
            )

    def add_input_file(
        self,
        file_name: str | None = None,
        *,
        provenance: str,
        data: pd.DataFrame | None = None,
        column_mappings: dict[str, str] | None = None,
        observation_properties: dict[str, str] | None = None,
        ignore_columns: list[str] | None = None,
        pattern: str | None = None,
        override: bool = False,
    ) -> CustomDataManager:
        """Add an inputFile to the config and optionally register the data as pandas DataFrame.

        This method registers an input file in the config. Optionally it also registers the
        data that accompanies the input file registered. The registration of the data is made
        optional in cases where a user wants to edit the config file without the
        accompanying data. The data can be registered later using the add_data method.

        Data must be in variable-per-row form (one observation per row). Read more about
        the input file format here:
        https://docs.datacommons.org/custom_dc/custom_data.html

        Exactly one of ``file_name`` or ``pattern`` must be provided. Pattern entries are
        config-only: ``data=`` is not accepted with ``pattern=``.

        Args:
            file_name: Exact name of the file (must have a .csv extension). Mutually
                exclusive with ``pattern``.
            provenance: Provenance name for the data. Bare name → minted as
                ``dcid:provenance/<name>``; pass an already ``dcid:``-prefixed value to
                use it verbatim. Names must be valid dcid tokens (no whitespace).
            data: Data to register (optional; only valid with ``file_name``).
            column_mappings: Column mappings. Match the headings in the CSV file to the
                allowed properties. Allowed keys are [variable, observationAbout, date, value, unit,
                scalingFactor, measurementMethod, observationPeriod, custom:<name>].
                Use custom:<name> keys to map each entity dimension for multi-entity observations.
            observation_properties: Optional file-level constant observation properties applied
                to every observation (e.g. ``{"unit": "USDollar"}``). Standard keys are
                ``unit``/``scalingFactor``/``measurementMethod``/``observationPeriod``; custom
                keys are preserved verbatim.
            ignore_columns: List of columns to ignore (optional).
            pattern: Glob pattern matching one or more input files. Mutually exclusive
                with ``file_name``. Pattern entries carry no local data.
            override: If True, overwrite the existing entry if it exists. Defaults to False.

        Raises:
            ValueError: If neither or both of ``file_name``/``pattern`` are provided,
                if ``data`` is passed together with ``pattern``, or if a duplicate entry
                exists and ``override`` is False.
        """

        if (file_name is None) == (pattern is None):
            raise ValueError(
                "Exactly one of 'file_name' or 'pattern' must be provided."
            )
        if pattern is not None and data is not None:
            raise ValueError("'data' cannot be provided together with 'pattern'.")

        entry = InputFile(
            filename=file_name,
            pattern=pattern,
            provenance=provenance,
            column_mappings=ColumnMappings.model_validate(column_mappings or {}),
            observation_properties=(
                ObservationProperties(**observation_properties)
                if observation_properties is not None
                else None
            ),
            ignore_columns=ignore_columns,
        )

        # Upsert into the list keyed by filename or pattern
        existing_idx: int | None = None
        for i, e in enumerate(self._config.input_files):
            if file_name is not None and e.filename == file_name:
                existing_idx = i
                break
            if pattern is not None and e.pattern == pattern:
                existing_idx = i
                break

        if existing_idx is not None:
            if not override:
                key = file_name if file_name is not None else pattern
                raise ValueError(
                    f"Input file '{key}' already registered. "
                    "Use override=True to replace it."
                )
            self._config.input_files[existing_idx] = entry
        else:
            self._config.input_files.append(entry)

        # Register data if provided (filename path only).
        # file_name is non-None here: the pattern+data guard and XOR check above ensure it.
        if data is not None:
            assert file_name is not None
            self._data_override_check(file_name=file_name, override=override)
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

        if not any(e.filename == file_name for e in self._config.input_files):
            raise ValueError(
                f"File '{file_name}' not found in the config file. Please register the "
                "file in the config file before adding data, using the "
                "add_input_file method."
            )

        self._data_override_check(file_name=file_name, override=override)

        self._data[file_name] = data
        return self

    def rename_variable(
        self, old_name: str, new_name: str, *, mcf_file_name: str | None = None
    ) -> CustomDataManager:
        """Rename a variable across any loaded MCF files.

        Args:
            old_name: The name of the variable to rename. A bare token is normalized
                to ``dcid:<token>``, the same rule ``add_variable_to_mcf`` applies to
                ``Node``.
            new_name: The new name for the variable. Same normalization as
                ``old_name``.
            mcf_file_name: Optional name of the MCF file from which to rename the variable.
                If omitted, all managed MCF files are searched.
        Raises:
            ValueError: If the variable is not found in any searched MCF file, or if the
                new name already exists in any searched MCF file.

        """

        old_name = ensure_dcid(old_name)
        new_name = ensure_dcid(new_name)

        file_names = (
            [validate_mcf_file_name(mcf_file_name)]
            if mcf_file_name
            else list(self._mcf_nodes.keys())
        )

        found_old = any(
            node.dcid == old_name
            for name in file_names
            for node in (self._mcf_nodes.get(name) or Nodes()).nodes
        )
        found_new = any(
            node.dcid == new_name
            for name in file_names
            for node in (self._mcf_nodes.get(name) or Nodes()).nodes
        )

        if not found_old:
            raise ValueError(f"Variable '{old_name}' not found")
        if found_new:
            raise ValueError(f"Variable '{new_name}' already exists")

        for name in file_names:
            nodes = self._mcf_nodes.get(name)
            if not nodes:
                continue
            if any(node.dcid == old_name for node in nodes.nodes):
                nodes.rename(old_name, new_name)

        return self

    def remove_variable(
        self, dcid: str, *, mcf_file_name: str | None = None
    ) -> CustomDataManager:
        """Remove a single variable from the manager.

        This removes the variable from any loaded MCF files. If
        ``mcf_file_name`` is provided, only that MCF file is searched;
        otherwise all MCF files will be inspected.

        Args:
            dcid: DCID of the StatVar to remove.
            mcf_file_name: Optional name of the MCF file from which to remove the
                node. If omitted, all managed MCF files are searched.

        Raises:
            ValueError: If the variable is not found in any MCF file.
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
                nodes.remove(dcid)
                found = True
            except ValueError:
                pass

        if not found:
            raise ValueError(f"Statistical variable '{dcid}' not found")

        return self

    def _require_provenance_exists(self, provenance: str, provenance_link: str) -> Node:
        """Return the Provenance MCF node with id ``provenance_link``, or raise ValueError.

        Args:
            provenance: The bare user-facing provenance ref (used in the error message).
            provenance_link: The minted dcid for the provenance (used for the lookup).
        """
        for nodes in self._mcf_nodes.values():
            for n in nodes.nodes:
                if n.type_of == "dcid:Provenance" and n.dcid == provenance_link:
                    return n
        raise ValueError(
            f"Provenance '{provenance}' not found. "
            f"Call add_provenance(dcid={provenance!r}, url=..., source=...) "
            f"before referencing it in includedIn."
        )

    def _expand_included_in(self, included_in: str | list[str]) -> list[str]:
        """Expand provenance reference(s) into includedIn dcids.

        For each reference: mint to ``dcid:provenance/<name>``, require the Provenance node
        to exist, and emit includedIn for BOTH the provenance and its linked Source
        (``sourceLink``). Order is preserved and duplicate dcids are collapsed (so two
        provenances sharing a source emit that source once).

        Args:
            included_in: A bare provenance name or list of names. Each name is minted to
                ``dcid:provenance/<name>``; the referenced Provenance node must already
                exist (added via ``add_provenance``).

        Returns:
            Ordered list of unique dcid strings (provenances + their sources).

        Raises:
            ValueError: If any referenced provenance has not been registered.
        """
        refs = [included_in] if isinstance(included_in, str) else list(included_in)
        expanded: list[str] = []
        seen: set[str] = set()
        for ref in refs:
            prov_link = mint_dcid(prefix="provenance", token=ref)
            prov_node = self._require_provenance_exists(ref, prov_link)
            for dcid in (prov_link, getattr(prov_node, "source_link", None)):
                if dcid is not None and dcid not in seen:
                    seen.add(dcid)
                    expanded.append(dcid)
        return expanded

    def _require_source_exists(self, source: str, source_link: str) -> None:
        """Raise ValueError if no Source MCF node with id ``source_link`` exists.

        Args:
            source: The bare user-facing source name (used in the error message).
            source_link: The minted dcid for the source (used for the lookup).
        """
        if not any(
            n.type_of == "dcid:Source" and n.dcid == source_link
            for nodes in self._mcf_nodes.values()
            for n in nodes.nodes
        ):
            raise ValueError(
                f"Source '{source}' not found. "
                f"Call add_source(dcid={source!r}, url=...) before add_provenance()."
            )

    def _validate_provenances(self) -> None:
        """Raise ValueError if any inputFile references a provenance with no matching node.

        Scans all MCF files for ``dcid:Provenance`` nodes and checks that every
        ``inputFiles`` entry with a ``provenance`` ref has a corresponding node.
        """
        known = {
            n.dcid
            for nodes in self._mcf_nodes.values()
            for n in nodes.nodes
            if n.type_of == "dcid:Provenance"
        }
        for entry in self._config.input_files:
            if entry.provenance and entry.provenance not in known:
                bare = entry.provenance.removeprefix("dcid:provenance/")
                raise ValueError(
                    f"Input file references unknown provenance '{bare}' "
                    f"('{entry.provenance}'). "
                    f"Call add_provenance(dcid={bare!r}, url=..., source=...) first."
                )

    def export_config(self, dir_path: str | PathLike[str]) -> None:
        """Export the config to a JSON file

        Before exporting, the config is validated to ensure that all required fields
        are present and that the config is valid.

        Args:
            dir_path: Path to the directory where the config will be exported.

        Raises:
            ValueError: If the config is not valid
        """

        self._validate_provenances()
        self._config.validate_config()

        # Default importName to the export directory name (matching the prep job's
        # fallback) for this export only, without mutating manager state, so
        # re-exporting to another directory picks up that directory's name.
        config = self._config
        if config.import_name is None:
            config = config.model_copy(update={"import_name": Path(dir_path).name})

        output_path = Path(dir_path) / "config.json"
        with output_path.open("w") as f:
            f.write(config.model_dump_json(indent=4, exclude_none=True, by_alias=True))

    def export_mcf_file(
        self,
        dir_path: str | PathLike[str],
        mcf_file_name: str = DEFAULT_STATVAR_MCF_NAME,
        overwrite: bool = True,
    ) -> None:
        """Export the MCF file to a file

        Args:
            dir_path: Path to the directory where the MCF file will be exported.
            mcf_file_name: Name of the MCF file (must end in .mcf). Defaults to "custom_nodes.mcf".
            overwrite: If True, overwrite the file if it exists. Defaults to True.
        """
        mcf_file_name = validate_mcf_file_name(mcf_file_name)

        output_path = Path(dir_path) / mcf_file_name

        nodes = self._mcf_nodes.get(mcf_file_name)
        if not nodes:
            raise ValueError(f"No data available for '{mcf_file_name}'")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        nodes.export_to_mcf_file(file_path=output_path, overwrite=overwrite)

    def config_to_dict(self) -> dict:
        """Export the config to a dictionary

        Before exporting, the config is validated to ensure that all required fields are
        present and that the config is valid. Unlike ``export_config``, this is a raw
        state dump: it does not default ``importName`` (there is no directory to derive
        it from), so an unset ``importName`` is absent from the returned dict.

        Returns:
            Dict: The config as a dictionary

        Raises:
            ValueError: If the config is not valid
        """

        self._validate_provenances()
        self._config.validate_config()

        return self._config.model_dump(mode="json", exclude_none=True, by_alias=True)

    def export_data(self, dir_path: str | PathLike[str]) -> None:
        """Export the data to CSV files

        Args:
            dir_path: Path to the directory where the data will be exported.
        """

        if not self._data:
            raise ValueError("No data to export")

        for file, data in self._data.items():
            path = Path(dir_path) / file
            path.parent.mkdir(parents=True, exist_ok=True)
            data.to_csv(path, index=False)

    def export_vertical_specs(self, dir_path: str | PathLike[str]) -> None:
        """Export the vertical-specs file as ``{"specs": [...]}`` JSON.

        Written to the name in the config's ``verticalSpecsFile`` (falling back to
        ``"vertical_specs.json"``). ``export_all`` calls this automatically when any
        spec has been added.

        Args:
            dir_path: Path to the directory where the file will be exported.

        Raises:
            ValueError: If no vertical specs have been added.
        """

        if not self._vertical_specs:
            raise ValueError("No vertical specs to export")

        file_name = self._config.vertical_specs_file or DEFAULT_VERTICAL_SPECS_NAME
        payload = {
            "specs": [spec.model_dump(mode="json") for spec in self._vertical_specs]
        }
        output_path = Path(dir_path) / file_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            f.write(json.dumps(payload, indent=4))

    def validate_all_input_files_have_data(self) -> CustomDataManager:
        """Validate that every declared input file has a corresponding data entry.

        Pattern entries (glob-matched files) are skipped; only ``filename`` entries
        require a registered dataframe.

        Raises:
            ValueError: If one or more input files declared in the config do not have
                associated data registered in this manager.
        """

        missing = [
            entry.filename
            for entry in self._config.input_files
            if entry.filename is not None and entry.filename not in self._data
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
        validate_data: bool = False,
    ) -> None:
        """Export the config, MCF file, and data to a directory

        ``export_all`` overwrites the complete bundle. To export only the config
        (deferring MCF export), use ``export_config`` directly. To export a single MCF
        file, use `export_mcf_file`.

        Args:
            dir_path: Path to the directory where the config and data will be exported.
            validate_data: If True, raise a ValueError before exporting if any input
                file declared in the config does not have a corresponding data entry.
                Defaults to False.

        Raises:
            ValueError: If an input file has no data entry.
        """

        if validate_data:
            self.validate_all_input_files_have_data()

        self.export_config(dir_path)

        if self._data:
            self.export_data(dir_path)

        if self._vertical_specs:
            self.export_vertical_specs(dir_path)

        for mcf_file_name in self._mcf_nodes:
            self.export_mcf_file(
                dir_path=dir_path, mcf_file_name=mcf_file_name, overwrite=True
            )

    def validate_config(self) -> CustomDataManager:
        """Validate the config

        This method checks the config for any issues and ensuring all the fields and values are valid. It raises
        an error if there are any issues with the config.

        Raises:
            pydantic.ValidationError if the config is not valid
        """

        self._validate_provenances()
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
            mcf_files: Path to one or more MCF files. If not provided, a new Nodes object
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
