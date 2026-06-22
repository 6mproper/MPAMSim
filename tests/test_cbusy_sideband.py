from __future__ import annotations

import yaml

from src.config.loader import load_config
from src.contracts.transaction import Transaction
from src.sim.simulation import Simulation
from src.web.config_builder import build_config, default_parameters


def _config_with_two_same_partid_threads(tmp_path):
    parameters = default_parameters()
    parameters.update(
        {
            "duration_ns": 20_000,
            "control_interval_ns": 10_000,
            "memory_controllers": 2,
        }
    )
    for row in parameters["stimulus_configs"]:
        row["enabled"] = row["slot"] in {0, 1}
        row["partid"] = 3
    raw = build_config(parameters, str(tmp_path / "run"))
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(path)


def _returned_request(requester_id: str, mc_id: str) -> Transaction:
    request = Transaction(
        transaction_id=100,
        workload_name="thread_00",
        workload_type="random_read",
        requester_id=requester_id,
        partid=3,
        pmg=0,
        address=0,
        size_bytes=64,
        operation="read",
        issue_time_ns=0.0,
        working_set_bytes=4096,
        locality="medium",
        source_node="r0",
    )
    request.memory_controller_id = mc_id
    request.return_cbusy_source = mc_id
    request.return_cbusy_level = 2
    request.return_cbusy_ostd_cap = 5
    request.return_cbusy_sample_time_ns = 123.0
    return request


def test_cbusy_return_sideband_updates_only_return_destination(
    tmp_path,
) -> None:
    simulation = Simulation.from_config(
        _config_with_two_same_partid_threads(tmp_path)
    )
    returned = _returned_request("cpu0.t0", "mc0")

    simulation._deliver_return_cbusy(returned)

    cpu0 = simulation.requesters["cpu0.t0"]
    cpu1 = simulation.requesters["cpu0.t1"]
    assert cpu0.cbusy_level(3, "mc0") == 2
    assert cpu0.effective_max_outstanding(3, "mc0") == 5
    assert cpu0.cbusy_level(3, "mc1") == 0
    assert cpu1.cbusy_level(3, "mc0") == 0
    assert simulation.collector.control_rows[-1]["event_type"] == (
        "return_sideband_delivered"
    )
    assert simulation.collector.control_rows[-1]["details"][
        "transport"
    ] == "rsp_dat_sideband"
