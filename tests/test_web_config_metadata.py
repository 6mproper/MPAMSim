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


def test_policy_ui_only_exposes_uncontrolled_and_controlled_modes() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    policy_values = re.findall(
        r'name="policy" value="([^"]+)"',
        index_html,
    )
    assert policy_values == ["no_control", "static_mpam"]
    assert "闭环 QoS" not in index_html
    assert "max_bw_step_percent" not in index_html
    assert "p99_hysteresis" not in index_html
    assert "min_hold_intervals" not in index_html


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


def test_resctrl_config_workspace_is_inside_mpam_tab() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
    ).read_text(encoding="utf-8")

    config_tabs = re.findall(r'data-tab="([^"]+)"', index_html)
    assert "resctrl" not in config_tabs
    assert 'data-panel="resctrl"' not in index_html
    assert 'data-tab="mpam"' in index_html
    for snippet in (
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
    mpam_start = index_html.index('data-panel="mpam"')
    resctrl_start = index_html.index('id="resctrlGroupTable"')
    partid_start = index_html.index('id="partidConfigTable"')
    assert mpam_start < resctrl_start < partid_start
    for snippet in (
        "function renderResctrlConfig(",
        "function collectResctrlGroups(",
        "function resctrlAssignments(",
        "function renderResctrlMonData(",
        "tasks > cpus_list > root",
    ):
        assert snippet in app_js


def test_soc_thread_topology_controls_drive_stimulus_rows() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
    ).read_text(encoding="utf-8")

    assert 'data-param="active_cores" type="number" min="1" max="16"' in index_html
    assert 'data-param="threads_per_core" type="number" min="1" max="4"' in index_html
    assert 'data-param="active_cores" type="number" value="8" readonly' not in index_html
    assert 'data-param="threads_per_core" type="number" value="2" readonly' not in index_html
    for snippet in (
        "function hardwareThreadCount(",
        "function requesterForSlot(",
        "function normalizeStimulusRows(",
        "function syncStimulusTopology(",
    ):
        assert snippet in app_js


def test_mpam_rows_show_resctrl_managed_badge() -> None:
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
    ).read_text(encoding="utf-8")
    styles = (
        PROJECT_ROOT / "src/web/static/styles.css"
    ).read_text(encoding="utf-8")

    for snippet in (
        "由resctrl接管",
        "function updateResctrlManagedRows(",
        "function resctrlManagedPartids(",
        "data-resctrl-managed-badge",
    ):
        assert snippet in app_js
    for snippet in (
        ".resctrl-managed-badge",
        ".resctrl-managed-row",
        ".partid-cell",
    ):
        assert snippet in styles


def test_control_overview_chart_layers_are_configurable() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
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
    for snippet in (
        "published monitor",
        "sampled-owner",
        "高级证据层默认关闭",
    ):
        assert snippet in index_html
    assert 'data-overview-layer="targetBand" type="checkbox" checked' in index_html
    assert 'data-overview-layer="controlInput" type="checkbox" checked' in index_html
    assert 'data-overview-layer="actual" type="checkbox" checked' in index_html
    assert 'data-overview-layer="events" type="checkbox" checked' in index_html
    assert 'data-overview-layer="filtered" type="checkbox" checked' not in index_html
    assert 'data-overview-layer="raw" type="checkbox" checked' not in index_html
    for snippet in (
        "Published Sampled",
        "published sampled",
        "latest filtered BW",
        "sampled-owner counter bank",
    ):
        assert snippet in app_js


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


def test_context_help_and_algorithm_explanations_open_on_click_only() -> None:
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
    ).read_text(encoding="utf-8")
    styles = (
        PROJECT_ROOT / "src/web/static/styles.css"
    ).read_text(encoding="utf-8")

    assert 'document.addEventListener("click", (event) =>' in app_js
    assert "showAlgorithmPopover(target);" in app_js
    assert "showHelp(target);" in app_js
    assert "function isNestedFormControlClick(event, target)" in app_js
    assert (
        "target === algorithmTarget && !isNestedFormControlClick(event, target)"
        in app_js
    )
    assert (
        "target === activeHelpTarget && !isNestedFormControlClick(event, target)"
        in app_js
    )
    for forbidden in (
        'document.addEventListener("mouseover"',
        'document.addEventListener("mouseout"',
        'document.addEventListener("focusin"',
        'document.addEventListener("focusout"',
        'addEventListener("mouseenter"',
        'addEventListener("mouseleave"',
        "algorithmTimer",
        "algorithmPinned",
    ):
        assert forbidden not in app_js
    assert "[data-help] {\n  cursor: pointer;" in styles
    assert "[data-algorithm] {\n  cursor: pointer;" in styles


def test_l3_qos_scheduler_is_explicit_switch_control() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    styles = (
        PROJECT_ROOT / "src/web/static/styles.css"
    ).read_text(encoding="utf-8")

    assert 'class="toggle-field switch-field" data-algorithm="l3-qos"' in index_html
    assert 'data-param="l3_qos_scheduler_enable" type="checkbox"' in index_html
    assert 'aria-label="L3 QoS调度开关"' in index_html
    for snippet in (
        ".switch-control",
        ".switch-slider",
        ".switch-text::before",
        'content: attr(data-on);',
    ):
        assert snippet in styles


def test_policy_mode_layout_has_two_segmented_modes_and_algorithm_label() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    styles = (
        PROJECT_ROOT / "src/web/static/styles.css"
    ).read_text(encoding="utf-8")

    assert 'class="policy-mode-row"' in index_html
    assert 'class="algorithm-guide-label">算法说明</span>' in index_html
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in styles
    assert ".policy-mode-row {\n  margin: 0 0 8px;\n  display: grid;\n  grid-template-columns: 1fr;" in styles
    assert ".policy-algorithm-guide" in styles
    assert ".policy-algorithm-guide button" in styles


def test_mc_qos_mapping_is_explicit_switch_control() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
    ).read_text(encoding="utf-8")

    assert "MC QoS 8->4映射" in index_html
    assert 'data-param="mc_qos_map_8_to_4_enable" type="checkbox"' in index_html
    assert 'aria-label="MC QoS 8级到4级映射开关"' in index_html
    assert "rawEffectiveQos" in app_js
    assert "qosMappingEvents" in app_js
    assert "QoS map" in app_js


def test_mc_error_weighted_qos_controls_are_configurable() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
    ).read_text(encoding="utf-8")

    assert 'data-param="mc_qos_adjust_mode"' in index_html
    assert "MC error-weighted QoS adjustment" in index_html
    assert 'data-param="mc_bmin_error_weight"' in index_html
    assert 'data-param="mc_bmax_error_weight"' in index_html
    assert 'data-param="mc_qos_error_deadband_percent"' in index_html
    assert 'data-param="mc_qos_error_max_delta"' in index_html
    assert 'data-param="mc_qos_error_quantization"' in index_html
    assert "error-weighted BMIN" in app_js


def test_config_import_export_workspace_is_present() -> None:
    index_html = (
        PROJECT_ROOT / "src/web/static/index.html"
    ).read_text(encoding="utf-8")
    app_js = (
        PROJECT_ROOT / "src/web/static/app.js"
    ).read_text(encoding="utf-8")

    for snippet in (
        'id="exportConfigButton"',
        'id="importConfigButton"',
        'id="importConfigFileInput"',
        'accept="application/json,.json"',
        "导出配置",
        "导入配置",
    ):
        assert snippet in index_html
    for snippet in (
        'CONFIG_FILE_SCHEMA = "mpamsim.config.parameters"',
        "function configFilePayload(",
        "function parseConfigFilePayload(",
        'throw new Error("配置文件类型不匹配。")',
        "payload.schema !== CONFIG_FILE_SCHEMA",
        "function exportCurrentConfig(",
        "async function importConfigFile(",
        "collectParameters()",
        "fillForm(parameters)",
    ):
        assert snippet in app_js


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
