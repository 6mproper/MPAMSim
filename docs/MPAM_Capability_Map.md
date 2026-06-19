# MPAM Capability Map

## 1. Purpose and Evidence Boundary

This document maps the current simulator to the broader Arm MPAM capability
space. It distinguishes implemented behavior from approximations and reserved
interfaces; it does not claim full architectural register compliance.

The supplied analysis under
`/Users/a1/Documents/Codex/2026-06-13/arm-mpam/outputs/` was used as a routing
and synthesis aid. Architectural claims remain grounded in its cited official
sources:

- Arm A-profile Architecture Reference Manual, DDI0487.
- Arm MPAM Memory System Component Specification, IHI0099.
- Arm MPAM ACPI Table Specification, DEN0065.
- Arm Learn MPAM Overview 107768 and Hardware Guide 109252.

## 2. Capability Summary

| Capability area | Arm MPAM role | Current model status | Fidelity and gap |
| --- | --- | --- | --- |
| PARTID | Primary resource-control identity | Implemented, 4-bit, 16 values | Carried on every abstract request and used by L3/MC tables |
| PMG | Monitoring/filter identity | Implemented behaviorally | Carried and traced; L3 and MC expose live `PARTID+PMG` monitor groups while controls remain PARTID-indexed |
| PARTID space | Secure/Non-secure/Root/Realm namespace | Interface reserved | No security-state model or per-space tables |
| PE instruction/data tags | Separate PARTID/PMG for instruction and data accesses | Not implemented | Each workload emits one tag pair |
| Virtual PARTID mapping | Guest-to-physical identifier mapping | Not implemented | Hypervisor and register behavior are outside V1 |
| Transport | Preserve MPAM bundle through CHI/NoC/bridges | Behaviorally implemented | Abstract request metadata is preserved; no CHI flit encoding |
| NoC priority | PARTID-derived arbitration preference | Implemented | Request priority affects the modeled NoC bottleneck queue |
| NoC bandwidth MSC | Per-PARTID weighted/rate control at NoC | Interface reserved | Queue and backpressure hooks exist; no separate NoC MBW table |
| CPBM | Cache portion/way eligibility | Implemented | Controls sampled-set eligible ways and effective capacity |
| CMAX | Maximum cache allocation | Implemented approximately | Bounds sampled ways and capacity-based hit probability |
| CMIN | Minimum cache allocation preference/protection | Implemented approximately | Protects sampled ownership from replacement; not an architected full-cache guarantee |
| CASSOC | Per-set associativity maximum | Not implemented | Could extend sampled victim selection later |
| CSU | Cache storage usage monitor | Approximated | First set of each eight-set group is sampled and occupancy is scaled by eight |
| MBWU | Memory bandwidth usage monitor | Implemented behaviorally | Reports per-PARTID traffic at L3 and MC observation points |
| MBW_MAX hard limit | Stop service above a bandwidth maximum | Implemented | Per-MC, per-PARTID token bucket delays dispatch |
| MBW_MAX soft limit | Work-conserving cap under contention | Implemented approximately | Over-limit traffic receives a contention-only priority penalty |
| MBW_MIN | Prefer under-minimum traffic | Implemented approximately | Per-MC credit grants scheduler bonus; not a real-time guarantee |
| BWPBM | Bandwidth portion bitmap | Not implemented | Future alternative bandwidth actuator |
| Proportional stride | Relative bandwidth scheduling | Not implemented | Scheduler interface can host a later stride/DRR model |
| Internal/downstream priority | Conflict-time service preference | Implemented behaviorally | One priority field drives modeled NoC and MC arbitration |
| PARTID disable | Disable a partition at an MSC | Not implemented | Can be added as an admission-control state |
| PARTID narrowing | Map global PARTID to smaller local table | Interface reserved | Per-MSC settings tables provide the replacement boundary |
| RIS | Multiple resources behind one MSC feature page | Interface reserved | L3 and MC instances are separate model components today |
| Feature discovery | Software discovers controls and monitor capabilities | Documented only | No MPAMF_IDR/MMIO feature-page register model |
| Monitor filter/select | Select PARTID/PMG/read-write monitor inputs | Partial | PARTID rows are fixed; no architected monitor selector state |
| Capture/NRDY/overflow/MSI | Synchronized and robust monitor readout | Not implemented | Interval snapshots are immediate software-model events |
| Error reporting | Invalid IDs, mapping, or control errors | Partial validation | Configuration rejects invalid fields; no architected ESR/ECR |
| ACPI MPAM discovery | Firmware describes MSC topology | Not implemented | YAML/topology JSON serve as the model-side description |
| PE-side BW control | Shape injection before the memory system | Partial behavioral implementation | Per-PARTID MC CBusy can clamp requester effective OSTD; no architected PE bandwidth register/token-bucket model |
| CBusy feedback | Per-PARTID downstream pressure feedback | Implemented approximately, four configurable levels | MC bandwidth/queue detector, delayed feedback, max-across-MC aggregation, and stepwise release |
| HW_SCALE | Scale same-PARTID PE limits by active PE count | Not implemented | The new 16-thread stimulus enables future experiments |
| SMMU/device tagging | Assign PARTID/PMG to DMA and internal accesses | Generic requester interface reserved | Web scenario currently instantiates CPU threads only |
| MSC domains/DCTRL | Local namespace translation and default controls | Not implemented | Future chiplet/domain extension |
| Closed-loop policy | Monitor, decide, and update controls | Implemented as slow loop | P99-driven MC BMAX/priority policy with hysteresis and hold time |

## 3. Current End-to-End Closed Loop

```text
16 hardware-thread stimuli
  -> requester with PARTID/PMG
  -> NoC queue and priority
  -> L3 CPBM/CMIN/CMAX plus sampled CSU/traffic
  -> MC BMIN/BMAX/priority plus MBWU
  -> per-PARTID latency/bandwidth monitors
  -> optional closed-loop policy update
```

This is sufficient to study causal system flow control, but it is not a full
MPAM architecture emulator.

## 4. Recommended Next Capability Order

1. Add per-requester/per-PARTID PE-side injection shaping and stall monitors.
2. Separate PMG monitor aggregation from PARTID control aggregation.
3. Add BMIN violation duration, response time, and active-PARTID credit/debt.
4. Add NoC per-PARTID bandwidth/weight controls and congestion feedback.
5. Add SMMU/DMA requesters and service traffic classes.
6. Add monitor capture, overflow, and not-ready timing semantics.
7. Add RIS and local PARTID translation only when multi-resource/chiplet
   experiments require them.

## 5. Explicit Non-Claims

- CPBM and CMAX are allocation controls, not access permissions or security
  isolation.
- Sampled CSU is an estimate, not exact full-cache occupancy.
- BMIN is a service preference/reservation approximation, not a WCET or
  hard real-time guarantee.
- The model does not implement Arm system registers, feature pages, ACPI
  discovery, Linux resctrl, or cache coherency.
