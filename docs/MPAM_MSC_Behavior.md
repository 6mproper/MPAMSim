# MPAM MSC Behavior Contract

## 1. Goal

This document defines the simulator behavior for MPAM-style Memory System Components (MSCs). It is a behavioral contract for architecture exploration, not a full Arm MPAM register implementation.

V1 MSCs:

- L3/SLC cache MSC.
- NoC queue/arbitration MSC.
- Memory-controller MSC.

## 2. Common MSC Interface

Every MSC must expose:

```python
class MSC:
    msc_id: str
    msc_type: str
    capabilities: set[str]

    def lookup_setting(self, partid: int) -> MPAMSetting: ...
    def apply_control(self, update: ControlUpdate) -> None: ...
    def receive(self, request: Request, time_ns: int) -> None: ...
    def monitor_snapshot(self, time_ns: int) -> dict: ...
```

Required capabilities include:

- `cache_portion`
- `bw_max`
- `bw_min`
- `priority`
- `monitor`
- `admission_control`
- `credit_backpressure`

An MSC may support only a subset. The validator must reject controls unsupported by the target MSC unless explicitly configured to ignore them.

## 3. L3/SLC Cache MSC Behavior

### 3.1 Lookup

On request arrival:

1. Read `request.partid`.
2. Lookup the L3/SLC MSC setting for that PARTID.
3. Derive allowed cache capacity or allowed ways from `cache_portion_bitmap`.
4. Estimate hit/miss and update occupancy.

### 3.2 Set/Way Model and Approximate Monitor

The cache geometry is explicitly configured with `sets`, `ways`, and
`line_size`. CPBM selects eligible ways, CMAX bounds allocation in the
sampled set, and CMIN protects an owner's sampled ways from replacement.

To keep system-level runs tractable, occupancy monitoring samples one set
from every group of eight consecutive sets:

```text
sampled_set = set_index % 8 == 0
estimated_occupancy_bytes = sampled_owned_ways * 8 * line_size
estimated_access_bytes = sampled_access_bytes * 8
allowed_capacity_bytes = sets * line_size * min(popcount(CPBM), CMAX)
hit_probability = f(allowed_capacity_bytes, working_set_bytes, locality, access_type)
```

This is an approximate monitor, not an exact tag-array model. Only the first
set in each eight-set group stores sampled way ownership and tags. The hit
probability remains a deterministic capacity/locality approximation under a
fixed seed.

### 3.3 L3/SLC Enforcement

L3/SLC enforcement effects:

- Limit per-PARTID effective occupancy.
- Change hit/miss rate.
- Convert misses into downstream memory requests.
- Record cache delay and miss penalty contribution.

V1 does not model coherency, snoops, invalidations, dirty sharing, or exact replacement state.

### 3.4 L3/SLC Monitors

Required counters:

- requests by PARTID/PMG.
- hits and misses by PARTID/PMG.
- occupancy bytes by PARTID.
- allowed capacity bytes by PARTID.
- evictions or allocation denials if modeled.
- cache delay by PARTID.

The implementation additionally exposes `monitor_groups` keyed by
`PARTID:PMG`. Each group reports sampled traffic, estimated bandwidth,
sampled-way ownership, estimated occupancy bytes, the PARTID's allowed
capacity, and:

```text
occupancy_rate = estimated_group_occupancy / PARTID_allowed_capacity
```

PMG affects monitor attribution only. CPBM, CMIN, and CMAX remain indexed by
PARTID.

## 4. NoC MSC Behavior

NoC behavior is included because MPAM-style priority and flow-control policies often need an interconnect enforcement point.

Required effects:

- Route request from source attach node to target MSC.
- Add fixed hop latency.
- Add queueing delay.
- Apply priority or class-based arbitration.
- Apply admission threshold or credit/backpressure when configured.

Required monitors:

- queue occupancy by router/link/class.
- utilization by link.
- dropped or delayed admissions if modeled.
- NoC delay by PARTID.
- backpressure time by requester or PARTID.

## 5. Memory-Controller MSC Behavior

### 5.1 Lookup

On memory-controller arrival:

1. Read `request.partid`.
2. Lookup memory-controller setting for that PARTID.
3. Apply token-bucket bandwidth cap or reservation approximation.
4. Map priority into scheduler class.
5. Schedule request onto a channel.

### 5.2 Bandwidth Cap

V1 uses a per-PARTID token bucket per memory-controller MSC:

```text
tokens_bytes += bw_max_gbps * elapsed_ns / 8
if request.size_bytes <= tokens_bytes:
    tokens_bytes -= request.size_bytes
    admit request
else:
    delay until enough tokens are available
```

Record token wait as `throttle_delay_ns`, separate from queue and service delay.

`hardlimit` blocks a request until tokens are available. `softlimit` applies
a priority penalty only under contention and remains work-conserving.

### 5.3 Bandwidth Minimum

`bw_min_gbps` is a reservation approximation in V1. The scheduler should use it as a floor when sharing service among contending PARTIDs, but it is not a full real-time guarantee unless a later model implements stricter admission control.

Each memory controller has an independent BMIN/BMAX setting and token state.
The interactive monitor displays the sum across memory-controller instances,
so a per-MC BMAX of 20 Gbps appears as 40 Gbps when two MCs are configured.

### 5.4 Priority

Priority affects arbitration among ready requests:

```text
higher priority -> earlier service when queues are contended
```

Priority must not allow permanent starvation. The scheduler must include aging, round-robin within class, or a configured minimum service share.

### 5.5 Memory-Controller Monitors

Required counters:

- requests by PARTID/PMG.
- bytes by PARTID/PMG.
- achieved bandwidth by PARTID.
- configured `bw_max_gbps` and `bw_min_gbps`.
- priority by PARTID.
- queue occupancy.
- throttle delay.
- queue delay.
- service delay.
- channel utilization.

The implementation also reports `monitor_groups` keyed by `PARTID:PMG`.
These include serviced requests/bytes, queue and service delay, limit events,
achieved bandwidth, controller capacity, and:

```text
bandwidth_utilization = group_bandwidth / controller_total_bandwidth
```

BMIN, BMAX, and priority remain PARTID controls; PMG does not create a
separate token bucket.

## 6. Control Update Semantics

Control updates are timestamped and applied at control intervals:

```python
ControlUpdate(
    target_msc="mc0",
    partid=2,
    field="bw_max_gbps",
    value=60.0,
    reason="protected partid p99 latency exceeded target",
)
```

All updates must be logged in `control_trace.csv` with old value, new value, policy, reason, and interval timestamp.

The `no_control` policy disables NoC priority mapping plus cache and
memory-controller enforcement, but does not remove the 16-entry settings
tables. Monitoring therefore remains available for all PARTIDs and reports
effective unrestricted cache settings and disabled memory-bandwidth controls.

## 7. Validation Expectations

- Reducing L3/SLC portion reduces occupancy and may reduce hit rate.
- Reducing memory-controller `bw_max_gbps` reduces achieved bandwidth and increases throttle delay.
- Raising protected PARTID priority reduces queueing delay under contention.
- Credit/backpressure reduces sustained queue occupancy.
- Monitors make the bottleneck visible instead of only reporting final latency.
