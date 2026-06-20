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
- `mc_qos`
- `monitor`
- `admission_control`
- `credit_backpressure`

An MSC may support only a subset. The validator must reject controls unsupported by the target MSC unless explicitly configured to ignore them.

## 3. L3/SLC Cache MSC Behavior

### 3.1 Lookup

On request arrival:

1. Enter the bounded FIFO queue or retry when it is full.
2. Wait until one of `lookup_parallelism` lookup slots is available.
3. Read `request.partid` and lookup its L3/SLC setting.
4. Derive allowed cache capacity or allowed ways.
5. Estimate hit/miss, update sampled ownership, and hold the lookup slot for
   `hit_latency_ns`.

The queue is an abstract L3 transaction/MSHR-pressure model:

```text
waiting entries <= queue_depth
active lookups <= lookup_parallelism
cache_delay = admission_backpressure + queue_delay + lookup_latency
```

It does not model banks, ports, snoop slots, coherence transactions, or tag
and data pipeline timing separately.

### 3.2 Set/Way Model and Approximate Monitor

The cache geometry is explicitly configured with `sets`, `ways`, and
`line_size`. CPBM selects eligible ways. CMIN and CMAX are percentages of
the whole physical L3 capacity and are enforced through global sampled-owner
quotas.

To keep system-level runs tractable, occupancy monitoring samples one set
from every group of eight consecutive sets:

```text
sampled_set = set_index % 8 == 0
estimated_occupancy_bytes = sampled_owned_ways * 8 * line_size
estimated_access_bytes = sampled_access_bytes * 8
reachable_percent = popcount(CPBM) / ways * 100
effective_CMIN = min(configured_CMIN_percent, reachable_percent)
effective_CMAX = min(configured_CMAX_percent, reachable_percent)
allowed_capacity_bytes = size_bytes * effective_CMAX / 100
sampled_capacity_lines = ceil(sets / 8) * ways
hit_probability = f(allowed_capacity_bytes, working_set_bytes, locality, access_type)
```

This is an approximate monitor, not an exact tag-array model. Only the first
set in each eight-set group stores sampled way ownership and tags. The hit
probability remains a deterministic capacity/locality approximation under a
fixed seed.

The sampled replacement algorithm is:

```text
eligible = ways selected by effective CPBM
global_owned = ownership across every sampled set
if global_owned >= floor(sampled_capacity_lines * effective_CMAX / 100):
    replace requester's own eligible LRU way
else:
    use an empty eligible way, if present
    otherwise replace the eligible LRU victim whose global owner count is
    above ceil(sampled_capacity_lines * owner_CMIN / 100)
```

An owner at or below effective CMIN is skipped. CMIN is therefore replacement
protection, not immediate pre-allocation; a PARTID must first populate ways.
Enabled CMIN values must total at most 100% per L3 and each CMIN must fit
inside its CPBM-reachable percentage. CMAX values may overlap and total above
100%.

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
- queue delay and admission backpressure by PARTID/PMG.
- average/peak queue occupancy, queue-full events, and active lookup slots.

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

NoC behavior is included because MPAM-style flow-control policies often need
an interconnect enforcement point. The current change keeps NoC request
priority neutral; MC QoS is not implicitly copied into the NoC.

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
4. Compute the local 3-bit MC QoS.
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

Bucket capacity is:

```text
capacity_bytes = max(64, rate_gbps / 8 * token_bucket_window_ns)
```

`hardlimit` removes a request from eligible candidates until tokens are
available. `softlimit` lowers MC QoS only under contention and remains
work-conserving.

### 5.3 Bandwidth Minimum

`bw_min_gbps` is a reservation approximation in V1. The scheduler should use it as a floor when sharing service among contending PARTIDs, but it is not a full real-time guarantee unless a later model implements stricter admission control.

The current implementation uses an independent BMIN credit bucket. If the
head request can consume BMIN credit, it receives `bmin_qos_promote` QoS
steps. Credit is consumed when that request is dispatched.

Each memory controller has an independent BMIN/BMAX setting and token state.
The interactive monitor displays the sum across memory-controller instances,
so a per-MC BMAX of 20 Gbps appears as 40 Gbps when two MCs are configured.

### 5.4 MC 3-bit QoS

MC QoS affects arbitration among ready requests:

```text
effective_qos = clamp(
    configured_mc_qos
  + min(qos_aging_max_steps, floor(queue_age_ns / aging_ns))
  + bmin_qos_promote when BMIN credit covers the request
  - softlimit_qos_demote when over BMAX and contended,
  0, 7)
```

The highest QoS wins; sequence order provides oldest-first tie-breaking.
Hard-BMAX-ineligible requests are filtered first. These constants are
configurable model behavior, not architected MPAM encodings.

### 5.5 Memory-Controller Monitors

Required counters:

- requests by PARTID/PMG.
- bytes by PARTID/PMG.
- achieved bandwidth by PARTID.
- configured `bw_max_gbps` and `bw_min_gbps`.
- base and effective MC QoS by PARTID.
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

BMIN, BMAX, and MC QoS remain PARTID controls; PMG does not create a
separate token bucket.

### 5.6 Independent Control Enables

CPBM, CMIN, CMAX, BMIN, BMAX, MC QoS, and CBusy each have a per-PARTID
enable. Disabling a mechanism retains its configured value for software
inspection but selects a neutral effective behavior. Monitoring remains active.

### 5.7 Four-Level CBusy Feedback

Each MC may independently generate CBusy level 0 through 3 per PARTID. The
detector samples:

- interval bandwidth relative to enabled BMAX;
- queued requests for that PARTID relative to MC queue capacity;
- hard-limit block activity;
- controller contention.

Bandwidth over BMAX asserts a level only under contention. Queue pressure and
hard-block activity may assert directly. Rising levels are immediate; falling
levels require the configured hold samples and recover one level at a time.

After the configured feedback latency, CPU requesters aggregate multiple MC
responses with the maximum level and apply:

```text
effective_ostd = min(configured_ostd, cbusy_level_cap)
```

The cap is never below one. CBusy source stall is recorded separately from
the configured requester-wide OSTD stall. The four thresholds and OSTD caps
are simulator behavior parameters, not architected CBusy encodings.

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
- BMAX-only, CBusy-only, and combined runs can be isolated with independent
  enables and compared under identical workload and seed.
- The built-in verification suite isolates CMIN retention, CMAX ownership,
  BMIN preference, soft-limit work conservation/contended penalty, and hard
  BMAX token blocking with deterministic microbenchmarks.
- Monitors make the bottleneck visible instead of only reporting final latency.
