# Simulator API and CLI Design

## 1. CLI

### Run one scenario

```bash
python -m src.sim.run --config examples/baseline_soc.yaml --scenario tests/noisy_neighbor/basic.yaml
```

### Run sweep

```bash
python -m src.sim.run_sweep --config examples/baseline_soc.yaml --sweep tests/qos/core_l3_sweep.yaml
```

### Generate report

```bash
python -m src.monitor.report --run outputs/noisy_neighbor --format html
```

### Validate configuration

```bash
python -m src.config.validate --config examples/baseline_soc.yaml
```

## 2. Python API

```python
from src.config.loader import load_config
from src.sim.kernel import Simulation

cfg = load_config("examples/baseline_soc.yaml")
sim = Simulation.from_config(cfg)
result = sim.run()
result.export("outputs/run_001")
result.render_report("outputs/run_001/report.html")
```

## 3. Policy Plug-in API

```python
class PolicyBase:
    def on_init(self, topology, mpam_config):
        pass

    def on_interval(self, time_ns, monitor_snapshot):
        return []
```

Returned updates:

```python
@dataclass
class ControlUpdate:
    target_msc: str
    partid: int
    field: str
    value: object
    reason: str

@dataclass
class MonitorSnapshot:
    time_ns: int
    per_partid: dict
    per_requester: dict
    per_msc: dict
    control_state: dict
```

## 4. Component API

```python
class Component:
    def receive(self, request):
        raise NotImplementedError

    def tick(self, time_ns):
        pass

    def monitor_snapshot(self):
        return {}
```

## 5. Request Object

```python
@dataclass
class Request:
    request_id: int
    requester_id: str
    partid: int
    pmg: int
    addr: int
    size_bytes: int
    op: str
    issue_time_ns: int
    qos_class: int = 0
    priority: int = 0
    source_attach_node: str | None = None
    target_msc: str | None = None
```

## 6. Output Schema

### run_summary.json

```json
{
  "scenario": "noisy_neighbor_basic",
  "seed": 1234,
  "simulation_time_ns": 10000000,
  "total_requests": 1000000,
  "completed_requests": 999900,
  "policies": ["closed_loop_qos"],
  "summary_metrics": {
    "total_throughput_gbps": 230.5,
    "max_p99_latency_ns": 812.2
  }
}
```

### metrics.csv

Columns:

```text
time_ns,partid,pmg,requests,bytes,avg_latency_ns,p99_latency_ns,p999_latency_ns,throughput_gbps,throttle_delay_ns
```

### per_cpu_partid.csv

Columns:

```text
time_ns,requester_id,partid,outstanding,peak_outstanding,max_outstanding,effective_max_outstanding,cbusy_level,cbusy_stall_ns,configured_ostd_stall_ns,cbusy_transitions,issued,completed,backpressure_ns
```

`outstanding` is sampled at the control-interval boundary. `peak_outstanding`
is the maximum observed since the previous boundary and resets to the current
outstanding value after capture.

### per_msc_utilization.csv

Columns:

```text
time_ns,msc_id,msc_type,utilization,queue_occupancy,bytes,requests
```

### control_trace.csv

Columns:

```text
time_ns,policy,target_msc,partid,field,old_value,new_value,reason
```

Fast feedback transitions use `policy=mc_cbusy`,
`field=cbusy_level`, and record the delivered effective OSTD cap in `reason`.

### timeline_trace.csv

Columns:

```text
time_ns,partid,requester_id,msc_id,noc_delay_ns,cache_delay_ns,cache_queue_delay_ns,mem_queue_delay_ns,mem_service_delay_ns,throttle_delay_ns,total_latency_ns
```

### topology.json

Contains requesters, clusters, cores, NoC attachment nodes, L3/SLC instances, memory controllers, and links for visualization.

## 7. Interactive Monitor-Group Snapshot

The interactive job API includes `monitor_groups` in every L3 and memory-controller snapshot. Keys use the stable `"<partid>:<pmg>"` form so software can correlate a configured stimulus row with one monitoring group.

L3 group records include sampled traffic, estimated bandwidth, sampled-way ownership, estimated occupancy bytes, allowed capacity bytes, and `occupancy_rate`. Occupancy is an approximation derived from the first set of each eight-set sample group and scaled to the configured cache geometry.

Memory-controller group records include serviced requests and bytes, queue and service delay, throttle delay, achieved bandwidth, controller bandwidth, and `bandwidth_utilization`.

PARTID remains the resource-control lookup key for CMIN, CMAX, CPBM, BMIN, BMAX, soft limit, and hard limit. PMG refines software-visible monitoring attribution only; it does not create an independent allocation or bandwidth-control partition.

## 8. Interactive CPU/PARTID Snapshot

The interactive job API includes a top-level `cpu` array in both partial and
completed results. Each row corresponds to one requester/PARTID/control
interval and contains the same fields as `per_cpu_partid.csv`.

The CPU monitor is a requester and flow-control view. It does not model CPU
pipeline occupancy, reorder buffers, SMT execution sharing, or coherency.

Memory-controller `per_partid` snapshots also include configured/effective
BMIN, BMAX, and priority values, their enable flags, and CBusy level,
bandwidth ratio, queue ratio, duty, OSTD cap, assertion count, and transition
count.

## 9. Interactive Experiment API

Submit a deterministic four-case mechanism experiment:

```http
POST /api/experiments
Content-Type: application/json

{"parameters": {...}}
```

The server derives and runs `reference`, `bmax_only`, `cbusy_only`, and
`combined` sequentially. All cases preserve topology, stimulus, duration,
configured control values, and random seed. The experiment forces
`static_mpam` and disables controls other than the BMAX/CBusy mechanism being
tested.

Poll progress and partial case summaries:

```http
GET /api/experiments/<job_id>
```

The completed result contains overall and per-PARTID evidence. Overall fields
include throughput, maximum P99, completion ratio, MC queue peak and
time-integrated queue area, throttle delay, hard blocks, CBusy source stall,
configured-OSTD stall, and CBusy transitions. Each case also links to its
static report under `/runs/experiment-<job_id>/<case>/report.html`.

## 10. Control Verification API

Submit the deterministic model-algorithm verification suite:

```http
POST /api/verifications
Content-Type: application/json

{"parameters": {...}}
```

Poll with:

```http
GET /api/verifications/<job_id>
```

The suite runs 11 microbenchmark cases and emits six checks:

- CMIN sampled replacement protection;
- CMAX sampled ownership bound;
- BMIN credit-based scheduler preference;
- BMAX soft-limit work conservation without contention;
- BMAX hard token blocking and throttle;
- BMAX soft-limit priority penalty under contention.

Each check contains `passed`, `expected`, and measured `evidence`. Case reports
are exported under `/runs/verification-<job_id>/<case>/`. The suite validates
this simulator's implementation; it is not an Arm MPAM architectural
compliance test. To isolate mechanisms, the suite uses a fixed one-L3,
one-MC microbenchmark topology with one sampled eight-set group and 32 Gbps
MC service capacity. It preserves the submitted random seed, L3 queue
parameters, and configurable MC algorithm constants.
