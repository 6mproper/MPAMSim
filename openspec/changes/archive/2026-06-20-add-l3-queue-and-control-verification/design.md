# Design: L3 Queue And Control Verification

## L3 Admission Model

Each L3 instance contains:

- a bounded FIFO waiting queue of `queue_depth` entries;
- `lookup_parallelism` concurrent lookup slots;
- fixed lookup service time equal to `hit_latency_ns`.

When the waiting queue is full, the request retries after a small model
interval and accumulates cache admission backpressure. Once admitted, queue
delay is measured until a lookup slot starts. Queue delay and lookup latency
both contribute to total cache delay.

This is an abstract transaction/MSHR-pressure model. It is not a banked cache
pipeline or coherent snoop-resource model.

## Sampled Cache Controls

For the sampled set:

- CPBM selects eligible physical way indexes.
- CMAX bounds the requester's owned eligible ways.
- If ownership is already at CMAX, a miss replaces the requester's LRU owned
  way.
- If ownership is below CMAX, replacement selects the global eligible LRU
  victim whose owner is above its effective CMIN.
- A victim owner at or below CMIN is protected from another PARTID.

## Memory Bandwidth Controls

The MC candidate score is:

```text
effective_priority =
    configured_priority
  + min(aging_cap, floor(queue_age_ns / aging_ns))
  + bmin_priority_boost when BMIN credit covers the request
  - softlimit_priority_penalty when over BMAX and contended
```

Hard BMAX makes the request ineligible until a per-PARTID token bucket has
enough bytes. Soft BMAX leaves the request eligible and applies its penalty
only under contention. Both BMIN and BMAX bucket capacity use
`max(64 bytes, rate_bytes_per_ns * token_bucket_window_ns)`.

## Verification Suite

The built-in suite uses deterministic microbenchmarks and the current
algorithm parameters:

- CMIN: prefill a protected PARTID, then start an aggressor; protection must
  retain at least the configured sampled ways and improve retained ownership.
- CMAX: compare full and limited sampled allocation; peak ownership per sampled
  set must respect CMAX.
- BMIN: compare equal-priority contention with BMIN disabled/enabled; BMIN
  credit must be consumed and improve the protected share.
- BMAX soft: verify an uncontended source remains work-conserving and a
  contended over-limit source receives penalty evidence.
- BMAX hard: verify token blocking, throttle delay, and achieved bandwidth near
  the configured cap.

Verification results are evidence for this simulator implementation, not proof
of conformance to an unspecified hardware implementation.
