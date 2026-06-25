from pathlib import Path

from dcp_tools.cli import main


def test_csv2mcf(tmp_path: Path) -> None:
    csv = tmp_path / "sv.csv"
    csv.write_text("Node,name,typeOf\ndcid:sv1,SV1,dcid:StatisticalVariable\n")
    out_mcf = tmp_path / "out.mcf"
    # Run cli
    exit_code = main(["csv2mcf", str(csv), str(out_mcf)])
    assert exit_code == 0
    assert out_mcf.exists()
    content = out_mcf.read_text()
    assert "Node: dcid:sv1" in content
    assert 'name: "SV1"' in content


def test_csv2mcf_with_options_and_mapping(tmp_path: Path) -> None:
    csv = tmp_path / "sv2.csv"
    csv.write_text(
        "identifier;name_col;type;ignore_me\n"
        "dcid:sv1;SV1;dcid:StatisticalVariable;junk\n"
    )
    out_mcf = tmp_path / "out.mcf"
    exit_code = main(
        [
            "csv2mcf",
            str(csv),
            str(out_mcf),
            "--column-mapping",
            "identifier=Node",
            "--column-mapping",
            "name_col=name",
            "--column-mapping",
            "type=typeOf",
            "--csv-option",
            "delimiter=;",
            "--ignore-column",
            "ignore_me",
        ]
    )
    assert exit_code == 0
    content = out_mcf.read_text()
    assert "Node: dcid:sv1" in content
    assert 'name: "SV1"' in content
    assert "typeOf: dcid:StatisticalVariable" in content
    assert "ignore_me" not in content


def test_csv2mcf_node_type_statvar_group(tmp_path: Path) -> None:
    csv = tmp_path / "group.csv"
    csv.write_text(
        "Node,name,specializationOf\ndcid:g/myGroup,My Group,dcid:dc/g/Root\n"
    )
    out_mcf = tmp_path / "group.mcf"
    exit_code = main(["csv2mcf", str(csv), str(out_mcf), "--node-type", "StatVarGroup"])
    assert exit_code == 0
    content = out_mcf.read_text()
    assert "Node: dcid:g/myGroup" in content
    assert 'name: "My Group"' in content
    assert "typeOf: dcid:StatVarGroup" in content
    assert "specializationOf: dcid:dc/g/Root" in content


def test_csv2mcf_append_and_override(tmp_path: Path) -> None:
    csv1 = tmp_path / "first.csv"
    csv1.write_text("Node,name,typeOf\ndcid:sv1,SV1,dcid:StatisticalVariable\n")
    csv2 = tmp_path / "second.csv"
    csv2.write_text("Node,name,typeOf\ndcid:sv2,SV2,dcid:StatisticalVariable\n")
    out_mcf = tmp_path / "out_append.mcf"
    main(["csv2mcf", str(csv1), str(out_mcf)])
    main(["csv2mcf", str(csv2), str(out_mcf)])
    content = out_mcf.read_text()
    assert content.count("Node: dcid:sv1") == 1
    assert content.count("Node: dcid:sv2") == 1
    main(["csv2mcf", str(csv1), str(out_mcf), "--override"])
    content_over = out_mcf.read_text()
    assert "Node: dcid:sv1" in content_over
    assert "Node: dcid:sv2" not in content_over
