# MPAM Model Design

## 1. Modeling Scope

This simulator models MPAM at system-architecture level, not as an exact implementation of all architectural registers.

The per-MSC behavior contract is defined in `docs/MPAM_MSC_Behavior.md`.

Included:

- PARTID and PMG tagging.
- Per-MSC settings table.
- Cache portion partitioning.
- Memory bandwidth cap.
- Priority class.
- Resource monitors.
- Control update path.

Excluded in v1:

- Full exception-level register behavior.
- Full security-state semantics.
- Full ACPI/firmware table parsing.
- Full Linux resctrl implementation.

## 2. MPAM Identification Model

Each request carries:

```text
PARTID: resource-control partition ID
PMG: performance-monitoring group
Requester ID: source agent
Stream ID / PASID: optional future extension
QoS class: optional NoC/DDR class
```

### Mapping

```text
Tenant / VM / Process / Thread / DMA Stream
        ↓
Software policy mapping
        ↓
PARTID + PMG
        ↓
Request metadata
        ↓
MSC settings table lookup
```

## 3. MPAM Settings Table

Each MSC owns a settings table:

```python
settings_table[partid] = MPAMSetting(
    cache_portion_bitmap="ffff",
    bw_max_gbps=100.0,
    bw_min_gbps=10.0,
    priority=8,
)
```

One MSC may support only a subset of controls.

Example:

```yaml
mpam:
  partitions:
    - partid: 0
      name: default
    - partid: 1
      name: latency_service
    - partid: 2
      name: background_bw
  msc_controls:
    - msc_id: slc0
      type: cache
      controls:
        - partid: 1
          cache_portion_bitmap: "00ff"
        - partid: 2
          cache_portion_bitmap: "ff00"
    - msc_id: mc0
      type: memory_controller
      controls:
        - partid: 1
          bw_max_gbps: 80
          priority: 12
        - partid: 2
          bw_max_gbps: 30
          priority: 4
```

## 4. Cache Partitioning Model

### Option A: Way-mask model

Each cache has:

- `num_sets`
- `num_ways`
- `line_size`
- `portion_bitmap`

Each PARTID is allowed to allocate only in permitted ways or portions.

### Option B: Capacity approximation

For fast simulation, track per-PARTID occupancy and probabilistic hit rate using working-set size.

The implementation should support both:

- `mode: way_model`
- `mode: capacity_approx`

## 5. Bandwidth Control Model

Use token bucket per PARTID per MSC.

```text
tokens += bw_max_gbps * interval
if request.size <= tokens:
    allow
else:
    delay / throttle
```

The implementation should record throttle delay separately from service delay.

## 6. Priority Control Model

Each request has a priority field after MPAM lookup.

Memory controller scheduler can map priority into classes:

```text
0-5   low priority
6-10  medium priority
11-15 high priority
```

The exact ranges must be configurable.

## 7. Monitor Model

Per MSC, maintain counters:

```text
requests[partid]
bytes[partid]
hit[partid]
miss[partid]
occupancy_bytes[partid]
queue_occupancy[partid]
throttle_delay_ns[partid]
service_latency_ns[partid]
```

PMG support:

```text
requests[(partid, pmg)]
bytes[(partid, pmg)]
latency[(partid, pmg)]
```

## 8. Control Update Model

A control update changes a setting table entry:

```python
@dataclass
class ControlUpdate:
    target_msc: str
    partid: int
    field: str
    value: Any
    reason: str
```

Examples:

```text
mc0 PARTID=2 bw_max_gbps 60 → 30 due to cap violation
slc0 PARTID=1 cache_portion_bitmap 00ff → 0fff due to p99 violation
mc1 PARTID=1 priority 8 → 12 due to latency violation
```

## 9. Model Validation Expectations

The model is considered reasonable if:

- More cache portions improve hit rate until working set fits.
- Lower bandwidth cap reduces throughput and increases queueing delay.
- Higher priority reduces latency under contention.
- More memory controllers reduce back-end contention.
- More cores per L3 increase shared-cache interference when working sets overlap.
