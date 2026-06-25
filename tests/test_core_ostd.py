from __future__ import annotations

import yaml

from src.config.loader import load_config
from src.config.schema import RequesterConfig
from src.sim.simulation import Simulation
from src.traffic.requester import CoreOstdPool, RequesterRuntime
from src.web.config_builder import build_config, default_parameters


def _pool(
    policy: str = "shared",
    maximum: int = 4,
    reserve: int = 1,
) -> CoreOstdPool:
    return CoreOstdPool(
        core_id="cpu0",
        max_outstanding=maximum,
        policy=policy,
        thread_reserve=reserve,
        thread_limits={"cpu0.t0": 4, "cpu0.t1": 4},
    )


def _requester(
    pool: CoreOstdPool,
    thread_id: str = "cpu0.t0",
    cbusy_response_enable: bool = True,
) -> RequesterRuntime:
    return RequesterRuntime(
        config=RequesterConfig(
            id=thread_id,
            type="cpu_thread",
            attach_node="r0",
            max_outstanding=4,
            core="cpu0",
            thread=int(thread_id[-1]),
        ),
        core_pool=pool,
        configured_partids=(1,),
        destination_mc_ids=("mc0", "mc1"),
        cbusy_response_enable=cbusy_response_enable,
    )


def test_shared_pool_enforces_core_total_and_releases() -> None:
    pool = _pool(maximum=3)
    for thread_id in ("cpu0.t0", "cpu0.t0", "cpu0.t1"):
        pool.mark_pending(thread_id, True)
        assert pool.block_reason(thread_id) is None
        pool.allocate(thread_id)

    assert pool.outstanding == 3
    assert pool.peak_outstanding == 3
    pool.mark_pending("cpu0.t1", True)
    assert pool.block_reason("cpu0.t1") == "core_ostd"

    pool.release("cpu0.t0")
    assert pool.outstanding == 2
    assert pool.block_reason("cpu0.t1") is None


def test_static_partition_does_not_borrow_other_thread_share() -> None:
    pool = _pool(policy="static_partition", maximum=4)
    for _ in range(2):
        pool.mark_pending("cpu0.t0", True)
        pool.allocate("cpu0.t0")

    pool.mark_pending("cpu0.t0", True)
    assert pool.block_reason("cpu0.t0") == "core_ostd"
    assert pool.outstanding == 2


def test_reserve_borrow_preserves_other_thread_reserve() -> None:
    pool = _pool(
        policy="reserve_borrow",
        maximum=6,
        reserve=2,
    )
    for _ in range(4):
        pool.mark_pending("cpu0.t0", True)
        pool.allocate("cpu0.t0")

    pool.mark_pending("cpu0.t0", True)
    assert pool.block_reason("cpu0.t0") == "core_ostd"
    for _ in range(2):
        pool.mark_pending("cpu0.t1", True)
        pool.allocate("cpu0.t1")
    assert pool.outstanding_by_thread == {
        "cpu0.t0": 4,
        "cpu0.t1": 2,
    }


def test_pending_threads_use_deterministic_round_robin() -> None:
    pool = _pool(maximum=4)
    pool.mark_pending("cpu0.t0", True)
    pool.mark_pending("cpu0.t1", True)
    assert pool.block_reason("cpu0.t0") is None
    assert pool.block_reason("cpu0.t1") == "core_round_robin"
    pool.allocate("cpu0.t0")

    pool.mark_pending("cpu0.t0", True)
    assert pool.block_reason("cpu0.t1") is None
    assert pool.block_reason("cpu0.t0") == "core_round_robin"


def test_cbusy_limits_same_partid_across_destinations() -> None:
    requester = _requester(_pool(maximum=8))
    requester.set_cbusy("mc0", partid=1, level=3, cap=1)

    requester.on_generated(1)
    assert requester.can_issue(1, "mc0")
    requester.on_issue(1, "mc0")

    requester.on_generated(1)
    assert not requester.can_issue(1, "mc0")
    assert requester.last_block_reason(1, "mc0") == "cbusy"
    assert not requester.can_issue(1, "mc1")
    assert requester.last_block_reason(1, "mc1") == "cbusy"

    assert requester.outstanding_by_partid_mc[(1, "mc0")] == 1
    assert requester.outstanding_by_partid_mc[(1, "mc1")] == 0


def test_cbusy_cap_is_shared_by_same_partid_on_two_threads() -> None:
    pool = _pool(maximum=8)
    thread0 = _requester(pool, "cpu0.t0")
    thread1 = _requester(pool, "cpu0.t1")
    for requester in (thread0, thread1):
        requester.set_cbusy("mc0", partid=1, level=3, cap=1)
        requester.on_generated(1)

    assert thread0.can_issue(1, "mc0")
    thread0.on_issue(1, "mc0")
    assert not thread1.can_issue(1, "mc0")
    assert thread1.last_block_reason(1, "mc0") == "cbusy"
    assert not thread1.can_issue(1, "mc1")
    assert thread1.last_block_reason(1, "mc1") == "cbusy"


def test_cpu_cbusy_response_can_be_disabled() -> None:
    requester = _requester(
        _pool(maximum=8),
        cbusy_response_enable=False,
    )
    requester.set_cbusy("mc0", partid=1, level=3, cap=1)

    for mc_id in ("mc0", "mc1"):
        requester.on_generated(1)
        assert requester.can_issue(1, mc_id)
        requester.on_issue(1, mc_id)

    assert requester.cbusy_level(1) == 3
    assert requester.effective_max_outstanding(1) == (
        requester.config.max_outstanding
    )


def test_multiple_workloads_keep_thread_pending_until_all_admit() -> None:
    requester = _requester(_pool(maximum=4))
    requester.on_generated(1)
    requester.on_generated(1)

    assert requester.can_issue(1, "mc0")
    requester.on_issue(1, "mc0")
    assert requester.pending == 1
    assert "cpu0.t0" in requester.core_pool.pending_threads

    assert requester.can_issue(1, "mc1")
    requester.on_issue(1, "mc1")
    assert requester.pending == 0
    assert "cpu0.t0" not in requester.core_pool.pending_threads


def test_end_to_end_two_threads_share_core_limit(tmp_path) -> None:
    parameters = default_parameters()
    parameters.update(
        {
            "duration_ns": 20_000,
            "control_interval_ns": 5_000,
            "max_outstanding": 4,
            "core_max_outstanding": 3,
            "core_ostd_policy": "shared",
            "thread_ostd_reserve": 1,
        }
    )
    for row in parameters["stimulus_configs"]:
        row["enabled"] = row["slot"] in {0, 1}
        if row["enabled"]:
            row.update(
                {
                    "rate_value": 100,
                    "rate_unit": "mrps",
                    "working_set_mb": 1,
                }
            )

    raw = build_config(parameters, str(tmp_path / "run"))
    path = tmp_path / "shared_core.yaml"
    path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )
    result = Simulation.from_config(load_config(path)).run()

    rows = [
        row
        for row in result.collector.requester_rows
        if row["core_id"] == "cpu0"
    ]
    assert rows
    assert max(row["core_ostd_peak"] for row in rows) <= 3
    assert {
        row["requester_id"]
        for row in rows
        if row["issued"] > 0
    } == {"cpu0.t0", "cpu0.t1"}
    assert result.collector.requester_mc_rows
