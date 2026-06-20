# Design: 3-bit QoS, Proportional Cache, And Control Effect

## MC QoS

Each MC settings table contains `mc_qos` in `[0, 7]`; seven is highest.
NoC request priority is independent and remains neutral in this change.

For each head-of-PARTID candidate:

```text
effective_qos = clamp(
    base_mc_qos
  + min(aging_max_steps, floor(queue_age_ns / qos_aging_ns))
  + bmin_qos_promote when BMIN credit covers the request
  - softlimit_qos_demote when over BMAX and contended,
  0, 7)
```

Hard-BMAX requests without tokens are excluded. Highest effective QoS wins;
oldest sequence wins ties. Monitor snapshots report base and selected
effective QoS plus promotion/demotion evidence.

## Proportional L3 Controls

`cmin_percent` and `cmax_percent` are percentages of the whole physical L3.
The one-in-eight-set model converts them to aggregate sampled-line targets:

```text
sampled_capacity_lines = ceil(sets / 8) * ways
reachable_percent = popcount(CPBM) / ways * 100
effective_cmin = min(configured_cmin, reachable_percent)
effective_cmax = min(configured_cmax, reachable_percent)
cmin_lines = ceil(sampled_capacity_lines * effective_cmin / 100)
cmax_lines = floor(sampled_capacity_lines * effective_cmax / 100)
```

CMIN is replacement protection after demand has populated cache lines, not
pre-allocation. CMAX prevents aggregate sampled ownership from growing beyond
the proportional limit. CMIN totals above 100% are invalid; CMAX totals may
exceed 100%.

## Control Effect

Every PARTID is evaluated along four layers:

```text
configured target -> enforcement state -> achieved resource share
                  -> workload result and control cost
```

The overview reports latest target/actual values and full-run target
adherence. The selected-PARTID view aligns:

- L3 actual share and CMIN/CMAX targets;
- MC achieved bandwidth and BMIN/BMAX targets;
- base/effective MC QoS and adjustment evidence;
- P99 target/actual, throughput, queueing, CBusy, and OSTD evidence;
- timestamped control updates.

CMIN and BMIN adherence are evaluated only when there is demand and measured
contention. Soft BMAX is classified as borrowing or demoted under contention,
not as a simple cap violation.

## Algorithm Explanations

One structured help registry supplies title, model version, scope, formula,
rules, evidence, and boundary. Hovering a tagged control or metric opens an
edge-aware, scrollable anchored window. The same registry is used for fields,
flow stages, and result columns.
