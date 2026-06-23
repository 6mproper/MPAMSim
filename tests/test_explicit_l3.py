from __future__ import annotations

from src.cache.cache_msc import CacheMSC
from src.config.schema import CacheConfig
from src.contracts.transaction import Transaction
from src.mpam.settings import SettingsTable
from src.sim.kernel import SimulationKernel


def _config(
    *,
    sets: int = 8,
    ways: int = 2,
    merge: bool = True,
    fill_entries: int = 2,
    replacement: str = "lru",
    monitor_cycles: int = 256,
    history_weight: int = 192,
    current_weight: int = 64,
) -> CacheConfig:
    return CacheConfig(
        id="slc0",
        level="L3",
        size_bytes=sets * ways * 64,
        line_size=64,
        ways=ways,
        shared_by_cores=["cpu0"],
        hit_latency_ns=2,
        sets=sets,
        monitor_group_sets=8,
        queue_depth=8,
        lookup_parallelism=2,
        miss_detect_latency_ns=2,
        fill_latency_ns=3,
        mshr_entries=4,
        fill_buffer_entries=fill_entries,
        merge_same_line_misses=merge,
        replacement_policy=replacement,
        clock_mhz=1000,
        monitor_period_cycles=monitor_cycles,
        history_weight=history_weight,
        current_weight=current_weight,
    )


def _request(
    transaction_id: int,
    address: int,
    partid: int = 0,
) -> Transaction:
    return Transaction(
        transaction_id=transaction_id,
        workload_name="l3-test",
        workload_type="random_read",
        requester_id=f"cpu0.t{partid % 2}",
        partid=partid,
        pmg=partid,
        address=address,
        size_bytes=64,
        operation="read",
        issue_time_ns=0,
        working_set_bytes=4096,
        locality="medium",
        source_node="r0",
    )


def _cache(config: CacheConfig):
    kernel = SimulationKernel()
    returned = []
    misses = []
    cache = CacheMSC(
        kernel,
        config,
        SettingsTable(),
        seed=1,
        on_hit=returned.append,
        on_miss=misses.append,
    )
    return kernel, cache, returned, misses


def _fill(
    kernel: SimulationKernel,
    cache: CacheMSC,
    request: Transaction,
) -> None:
    assert cache.can_accept_fill(request)
    cache.accept_fill(request)
    kernel.run(kernel.now_ns + cache.config.fill_latency_ns)


def test_fill_creates_real_tag_and_next_access_hits() -> None:
    kernel, cache, returned, misses = _cache(_config())
    first = _request(1, 0)
    cache.receive(first)
    kernel.run(2)
    assert misses == [first]
    _fill(kernel, cache, first)
    assert returned == [first]

    second = _request(2, 0)
    cache.receive(second)
    kernel.run(kernel.now_ns + 2)

    assert second.cache_hit is True
    assert misses == [first]
    assert returned == [first, second]
    values = cache.monitor_snapshot(kernel.now_ns).payload[
        "per_partid"
    ]["0"]
    assert values["hits"] == 1
    assert values["misses"] == 1
    assert values["actual_occupancy_bytes"] == 64


def test_same_line_reads_merge_and_keep_first_owner() -> None:
    kernel, cache, returned, misses = _cache(_config(merge=True))
    first = _request(1, 0, partid=0)
    second = _request(2, 0, partid=1)
    cache.receive(first)
    cache.receive(second)
    kernel.run(2)

    assert misses == [first]
    assert cache.mshr_occupancy == 1
    _fill(kernel, cache, first)

    assert returned == [first, second]
    snapshot = cache.monitor_snapshot(kernel.now_ns).payload
    assert snapshot["per_partid"]["1"]["merged_misses"] == 1
    assert snapshot["per_partid"]["0"]["actual_line_count"] == 1
    assert snapshot["per_partid"]["1"]["actual_line_count"] == 0


def test_non_sampled_set_exposes_monitor_error() -> None:
    kernel, cache, _, misses = _cache(_config(sets=8))
    request = _request(1, 64)
    cache.receive(request)
    kernel.run(2)
    _fill(kernel, cache, misses[0])

    values = cache.monitor_snapshot(kernel.now_ns).payload[
        "per_partid"
    ]["0"]
    assert values["actual_occupancy_bytes"] == 64
    assert values["estimated_occupancy_bytes"] == 0
    assert values["monitor_error_bytes"] == -64


def test_fill_buffer_readiness_blocks_when_full() -> None:
    kernel, cache, _, misses = _cache(
        _config(fill_entries=1, merge=False)
    )
    first = _request(1, 0)
    second = _request(2, 64)
    cache.receive(first)
    cache.receive(second)
    kernel.run(2)

    cache.accept_fill(misses[0])
    assert cache.fill_buffer_occupancy == 1
    assert not cache.can_accept_fill(misses[1])
    kernel.run(5)
    assert cache.fill_buffer_occupancy == 0


def test_duplicate_unmerged_fill_does_not_relabel_line() -> None:
    kernel, cache, returned, misses = _cache(
        _config(merge=False)
    )
    first = _request(1, 0, partid=0)
    second = _request(2, 0, partid=1)
    cache.receive(first)
    cache.receive(second)
    kernel.run(2)
    assert misses == [first, second]

    _fill(kernel, cache, first)
    _fill(kernel, cache, second)

    assert returned == [first, second]
    snapshot = cache.monitor_snapshot(kernel.now_ns).payload
    assert snapshot["per_partid"]["0"]["actual_line_count"] == 1
    assert snapshot["per_partid"]["1"]["actual_line_count"] == 0
    assert (
        snapshot["per_partid"]["1"]["redundant_memory_fetches"]
        == 1
    )


def test_lru_evicts_oldest_eligible_line() -> None:
    kernel, cache, returned, misses = _cache(
        _config(sets=1, ways=2, replacement="lru")
    )
    first = _request(1, 0)
    second = _request(2, 64)
    cache.receive(first)
    kernel.run(2)
    _fill(kernel, cache, first)
    cache.receive(second)
    kernel.run(kernel.now_ns + 2)
    _fill(kernel, cache, second)

    touch_first = _request(3, 0)
    cache.receive(touch_first)
    kernel.run(kernel.now_ns + 2)
    assert touch_first.cache_hit

    third = _request(4, 128)
    cache.receive(third)
    kernel.run(kernel.now_ns + 2)
    _fill(kernel, cache, third)

    evicted_second = _request(5, 64)
    cache.receive(evicted_second)
    kernel.run(kernel.now_ns + 2)
    assert evicted_second.cache_hit is False
    assert misses[-1] is evicted_second


def test_l3_control_reads_only_published_filtered_sample() -> None:
    kernel, cache, _, _ = _cache(
        _config(
            sets=8,
            ways=2,
            monitor_cycles=8,
            history_weight=0,
            current_weight=256,
        )
    )
    request = _request(1, 0, partid=3)
    cache._allocate_fill(request)

    assert cache._sampled_owner_counts()[3] == 1
    assert cache._control_owner_counts().get(3, 0) == 0
    kernel.run(8)
    assert cache._raw_sampled_counts[3] == 1
    assert cache._filtered_sampled_counts[3] == 1
    assert cache._control_owner_counts().get(3, 0) == 0
    kernel.run(16)
    assert cache._control_owner_counts()[3] == 1


def test_l3_monitor_exposes_physical_sample_error() -> None:
    kernel, cache, _, _ = _cache(
        _config(
            sets=8,
            ways=2,
            monitor_cycles=8,
            history_weight=0,
            current_weight=256,
        )
    )
    non_sampled = _request(1, 64, partid=4)
    cache._allocate_fill(non_sampled)
    kernel.run(8)

    values = cache.monitor_snapshot(8).payload["per_partid"]["4"]

    assert values["actual_occupancy_bytes"] == 64
    assert values["raw_occupancy_bytes"] == 0
    assert values["filtered_occupancy_bytes"] == 0
    assert values["monitor_error_bytes"] == -64
