# Configuration Schema

## 1. Full Example

```yaml
simulation:
  time_ns: 10000000
  seed: 1234
  control_interval_ns: 100000

soc:
  clusters:
    - id: cluster0
      cores: [cpu0, cpu1, cpu2, cpu3]
      l3: slc0
    - id: cluster1
      cores: [cpu4, cpu5, cpu6, cpu7]
      l3: slc0
    - id: cluster2
      cores: [cpu8, cpu9, cpu10, cpu11]
      l3: slc1
    - id: cluster3
      cores: [cpu12, cpu13, cpu14, cpu15]
      l3: slc1
  core:
    threads_per_core: 2
  caches:
    - id: slc0
      level: L3
      size_bytes: 33554432
      sets: 32768
      line_size: 64
      ways: 16
      monitor_group_sets: 8
      queue_depth: 128
      lookup_parallelism: 16
      shared_by_cores: [cpu0, cpu1, cpu2, cpu3, cpu4, cpu5, cpu6, cpu7]
    - id: slc1
      level: L3
      size_bytes: 33554432
      line_size: 64
      ways: 16
      shared_by_cores: [cpu8, cpu9, cpu10, cpu11, cpu12, cpu13, cpu14, cpu15]
  noc:
    topology: mesh
    routers: 8
    link_bandwidth_gbps: 256
    router_latency_ns: 5
    queue_depth: 64
    virtual_channels: 4
  memory:
    controllers:
      - id: mc0
        channels: 2
        bandwidth_gbps_per_channel: 128
        scheduler: priority_rr
        queue_depth: 256
        token_bucket_window_ns: 100
        aging_ns: 500
        aging_priority_cap: 15
        bmin_priority_boost: 16
        softlimit_priority_penalty: 16
      - id: mc1
        channels: 2
        bandwidth_gbps_per_channel: 128
        scheduler: priority_rr

requesters:
  auto_expand_cpu_threads: true
  defaults:
    max_outstanding: 32
  core_attach_nodes:
    cpu0: r0
    cpu1: r0
    cpu2: r1
    cpu3: r1
    cpu4: r2
    cpu5: r2
    cpu6: r3
    cpu7: r3
    cpu8: r4
    cpu9: r4
    cpu10: r5
    cpu11: r5
    cpu12: r6
    cpu13: r6
    cpu14: r7
    cpu15: r7
  explicit:
    - id: dma0
      type: dma
      attach_node: r3
      max_outstanding: 128

mpam:
  partid_width: 8
  pmg_width: 8
  partitions:
    - partid: 0
      name: default
    - partid: 1
      name: latency_sensitive
    - partid: 2
      name: background_bandwidth
  msc_controls:
    - msc_id: slc0
      controls:
        - partid: 1
          cmin: 4
          cmax: 8
          cpbm: "00ff"
        - partid: 2
          cache_portion_bitmap: "ff00"
    - msc_id: slc1
      controls:
        - partid: 1
          cache_portion_bitmap: "00ff"
        - partid: 2
          cache_portion_bitmap: "ff00"
    - msc_id: mc0
      controls:
        - partid: 1
          bmin: 40
          bmax: 120
          limit_mode: hardlimit
          priority: 12
        - partid: 2
          bw_max_gbps: 80
          priority: 4
    - msc_id: mc1
      controls:
        - partid: 1
          bw_max_gbps: 120
          priority: 12
        - partid: 2
          bw_max_gbps: 80
          priority: 4

workloads:
  - name: latency_service
    type: pointer_chase
    requesters: [cpu0.t0]
    partid: 1
    pmg: 0
    request_size_bytes: 64
    injection_rate_mrps: 20
    read_ratio: 1.0
    working_set_bytes: 67108864
    target_p99_ns: 500
  - name: background_stream
    type: stream
    requesters: [cpu1.t0, cpu2.t0, cpu3.t0, cpu4.t0, cpu5.t0, cpu6.t0, cpu7.t0]
    partid: 2
    pmg: 0
    request_size_bytes: 64
    injection_rate_gbps: 200
    read_ratio: 0.8
    working_set_bytes: 1073741824

policies:
  - name: closed_loop_qos
    params:
      interval_ns: 100000
      max_bw_step_percent: 10
      priority_min: 0
      priority_max: 15
      background_partids: [2]
      protected_partids: [1]

outputs:
  dir: outputs/noisy_neighbor
  formats: [json, csv]
  trace_requests: false
  visualization:
    generate_report: true
    report_format: html
    plots:
      - latency
      - bandwidth
      - queue_occupancy
      - control_trace
      - topology
```

## 2. Mandatory User-Controlled Hardware Parameters

These must be supported in v1:

```text
clusters
cores
threads_per_core
L3/SLC instances
core-to-L3 mapping
cache size
cache ways
line size
NoC topology
NoC link bandwidth
NoC queue depth
NoC virtual channels
memory-controller count
channels per memory controller
bandwidth per channel
memory-controller scheduler
requester expansion mode
requester-to-NoC attachment
max outstanding per requester
```

## 3. Mandatory MPAM Parameters

```text
PARTID width
PMG width
partition list
MSC control list

Each MSC control may independently set:

```yaml
cpbm_enable: true
cmin_enable: true
cmax_enable: true
bmin_enable: true
bmax_enable: true
priority_enable: true
cbusy_enable: false
cbusy_l1_ostd: 24
cbusy_l2_ostd: 12
cbusy_l3_ostd: 4
```

Memory-controller instances may configure the CBusy detector:

```yaml
cbusy_sample_ns: 1000
cbusy_feedback_latency_ns: 50
cbusy_release_hold_samples: 3
cbusy_l1_bw_ratio: 1.0
cbusy_l2_bw_ratio: 1.1
cbusy_l3_bw_ratio: 1.25
cbusy_l1_queue_ratio: 0.25
cbusy_l2_queue_ratio: 0.50
cbusy_l3_queue_ratio: 0.75
```
cache portion bitmap
cache minimum ways
cache maximum ways
bandwidth max
bandwidth min or reservation approximation
bandwidth limit mode: softlimit or hardlimit
priority class
monitor enable
```

The interactive configuration requires exactly 16 unique PARTID rows,
covering PARTID 0 through 15. Cache controls are instantiated independently
for every L3 MSC, and bandwidth controls independently for every memory
controller MSC.

## 4. Mandatory Workload Parameters

```text
workload name
type
requester set
PARTID
PMG
request size
injection rate
read/write ratio
working set size
address distribution
SLA target
```

## 5. Mandatory Visualization Parameters

```text
output directory
output formats
whether to emit timeline trace
whether to generate static report
plot list
topology export enable
```

## 6. Interface References

- Use `docs/Stimulus_Model.md` for requester and workload stimulus details.
- Use `docs/Multicore_Model.md` for multicore hierarchy and requester expansion rules.
- Use `docs/User_Interface_and_Visualization.md` for CLI, report, and visualization outputs.
- Use `docs/MPAM_MSC_Behavior.md` for per-MSC control semantics.
