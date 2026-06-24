from __future__ import annotations

import json
import re
from pathlib import Path

from src.web.config_builder import default_parameters
from src.web.config_metadata import (
    CONTROL_ALGORITHMS,
    CONTROL_FIELD_ALGORITHMS,
    PARAMETER_METADATA,
    REQUIRED_CONTROL_SECTIONS,
    audit_config_metadata,
    config_metadata_payload,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_all_default_web_config_fields_have_complete_metadata() -> None:
    assert audit_config_metadata(default_parameters()) == []


def test_control_algorithms_have_complete_hardware_logic() -> None:
    for name, algorithm in CONTROL_ALGORITHMS.items():
        assert all(
            str(algorithm.get(section, "")).strip()
            for section in REQUIRED_CONTROL_SECTIONS
        ), name


def test_every_control_field_maps_to_a_known_algorithm() -> None:
    for fields in CONTROL_FIELD_ALGORITHMS.values():
        for algorithm_name in fields.values():
            assert algorithm_name in CONTROL_ALGORITHMS


def test_metadata_payload_is_json_serializable() -> None:
    payload = config_metadata_payload()
    encoded = json.dumps(payload, ensure_ascii=False)
    assert payload["version"]
    assert "CMIN" in encoded
    assert "前向进展" in encoded


def test_every_static_parameter_control_has_metadata() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    parameter_names = set(
        re.findall(r'data-param="([^"]+)"', index_html)
    )
    assert parameter_names <= set(PARAMETER_METADATA)


def test_results_default_to_control_evidence_workspace() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    top_level_tabs = re.findall(r'data-result-tab="([^"]+)"', index_html)
    assert top_level_tabs == [
        "control-overview",
        "causal",
        "advanced-evidence",
    ]
    for element_id in (
        "presetSelect",
        "applyPresetButton",
        "presetExpected",
        "overviewChartLayers",
        "overviewCpuCard",
        "overviewL3Card",
        "overviewMcCard",
        "overviewL3Chart",
        "overviewMcChart",
        "overviewPartidMatrix",
        "advancedEvidenceBody",
    ):
        assert f'id="{element_id}"' in index_html
    assert 'data-overview-layer="controlInput"' in index_html
    assert "latest filtered" in index_html
    for advanced_target in (
        "resource-monitor",
        "control-effect",
        "monitor-group",
        "mpam-monitor",
        "controls",
    ):
        assert f'data-advanced-target="{advanced_target}"' in index_html


def test_resctrl_config_workspace_is_present() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
    ).read_text(encoding="utf-8")

    config_tabs = re.findall(r'data-tab="([^"]+)"', index_html)
    assert "resctrl" in config_tabs
    for snippet in (
        'data-panel="resctrl"',
        'data-param="resctrl_enabled"',
        'id="resctrlGroupTable"',
        'id="resctrlLastStatus"',
        'id="resctrlMonDataTable"',
        "CTRL_MON group",
        "schemata",
        "cpus_list",
        "mon_data",
    ):
        assert snippet in index_html
    for snippet in (
        "function renderResctrlConfig(",
        "function collectResctrlGroups(",
        "function resctrlAssignments(",
        "function renderResctrlMonData(",
        "tasks > cpus_list > root",
    ):
        assert snippet in app_js


def test_control_overview_chart_layers_are_configurable() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    layers = re.findall(r'data-overview-layer="([^"]+)"', index_html)
    assert layers == [
        "targetBand",
        "controlInput",
        "filtered",
        "actual",
        "raw",
        "events",
    ]
    for layer in layers:
        pattern = (
            rf'<label data-help="[^"]+">'
            rf'<input data-overview-layer="{layer}"'
        )
        assert re.search(pattern, index_html), layer


def test_l3_same_line_merge_is_unchecked_by_default() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    match = re.search(
        r'<input data-param="l3_merge_same_line_misses"([^>]*)>',
        index_html,
    )
    assert match is not None
    assert "checked" not in match.group(1)


def test_algorithm_explanations_use_compact_body() -> None:
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
    ).read_text(encoding="utf-8")
    styles = (
        PROJECT_ROOT / "src/web/static/styles.css"
    ).read_text(encoding="utf-8")
    assert "algorithm-compact-lines" in app_js
    assert ".algorithm-popover .algorithm-compact-lines" in styles


def test_result_charts_declare_axis_units() -> None:
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
    ).read_text(encoding="utf-8")
    for snippet in (
        "function axisLabel(",
        'xLabel: "时间"',
        'xUnit: "ns"',
        'yUnit: "ns"',
        'yUnit: "Gbps"',
        'yUnit: "entries"',
        'yUnit: "%"',
        'yUnit: "level"',
        'xLabel: "延迟来源"',
    ):
        assert snippet in app_js
    assert app_js.count("drawLineChart(") == app_js.count(
        'xUnit: "ns"'
    ) + 1


def test_soc_tab_has_capability_summaries_and_mc_clock() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    for element_id in (
        "socCpuCapability",
        "socL3Capability",
        "socNocCapability",
        "socMcCapability",
    ):
        assert f'id="{element_id}"' in index_html
    assert index_html.count('data-param="mc_clock_mhz"') == 1
    soc_panel = re.search(
        r'<section class="config-section active" data-panel="soc">(.*?)'
        r'<section class="config-section" data-panel="traffic">',
        index_html,
        re.S,
    ).group(1)
    policy_panel = re.search(
        r'<section class="config-section" data-panel="policy">(.*?)'
        r'</section>',
        index_html,
        re.S,
    ).group(1)
    assert 'data-param="mc_clock_mhz"' in soc_panel
    assert 'data-param="mc_clock_mhz"' not in policy_panel
