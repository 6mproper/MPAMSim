# Model Assumptions

## 1. Simulation Level

This is a system-architecture simulator. It models abstract memory-system requests, shared-resource contention, MPAM-style identification, MSC enforcement, monitoring, and policy feedback. It is not an RTL model and not a cycle-accurate CPU, cache, NoC, or DRAM simulator.

## 2. Request Semantics

- Each request is independent for V1.
- Completion order may differ from issue order when priority, throttling, or queueing is modeled.
- No cache coherency, memory ordering, barriers, snoops, or invalidation traffic are modeled in V1.
- Address distributions are used for cache-hit approximation and memory-controller mapping, not for coherent ownership tracking.

## 3. MPAM Abstraction

- PARTID selects a resource-control partition.
- PMG provides monitoring sub-attribution.
- Each MSC has a settings table indexed by PARTID.
- V1 models behaviorally useful controls: cache portion, bandwidth max/min approximation, priority, and monitor enable.
- V1 does not model full architectural registers, trap behavior, security states, or firmware table parsing.

## 4. Cache/SLC Model

- Default V1 mode is capacity approximation.
- Per-PARTID allowed capacity is derived from cache portion configuration.
- Hit probability is a function of allowed capacity, working-set size, locality, and access pattern.
- Exact set/way replacement and coherency side effects are deferred.

## 5. NoC Model

- NoC latency is modeled as fixed per-hop delay plus queueing delay.
- Virtual channels and priority classes are modeled as arbitration resources, not full microarchitectural state.
- Credit/backpressure gates injection or admission to prevent unbounded queue growth.

## 6. Memory-Controller Model

- Bandwidth caps use per-PARTID token buckets.
- Priority affects scheduler choice under contention.
- Service time is derived from channel bandwidth and request size.
- Detailed DRAM timing is deferred.

## 7. Policy Model

- Policies read monitor snapshots only at configured control intervals.
- Control updates must be step-limited and bounded by configured floors and ceilings.
- Closed-loop policy must use hysteresis and minimum hold time to avoid oscillation.

## 8. Evidence and Calibration

All external technical claims should be traceable to official documentation, official technical support material, peer-reviewed papers, or patents. When no calibration data exists, mark the parameter as synthetic and use scenario sweeps rather than presenting numeric values as silicon-accurate.
