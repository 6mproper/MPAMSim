# Change: Add 3-bit MC QoS, Proportional Cache Controls, And Effect View

## Why

The current MC scheduler uses a 0-15 numeric priority score shared implicitly
with NoC behavior. L3 CMIN/CMAX are configured as ways per sampled set rather
than cache-capacity proportions. Monitoring exposes counters but does not make
configured targets, enforcement state, achieved resource share, and workload
effect easy to compare over the full run.

## What Changes

- Replace per-PARTID MC priority with an independent 3-bit MC QoS value from
  zero through seven.
- Express BMIN promotion, soft-BMAX demotion, and aging as bounded QoS-level
  adjustments; hard BMAX remains an eligibility filter.
- Convert L3 CMIN and CMAX to percentages of the whole physical L3 instance.
- Enforce proportional CMIN/CMAX using aggregate ownership across all sampled
  sets while retaining CPBM as the reachable-way mask.
- Add a 16-PARTID control-effect overview and a selected-PARTID full-run view
  of L3 share, MC bandwidth, effective QoS, P99, and control events.
- Add anchored algorithm explanation windows for L3, MC, CBusy, source OSTD,
  and control-effect metrics.
- Update built-in verification cases and documentation to the new semantics.

## Impact

- Affected specs: `mpam-l3-control`, `mpam-memory-bandwidth`,
  `interactive-simulation-console`, and `soc-flow-simulation`.
- Affected code: MPAM settings/configuration, L3 and MC models, slow policy,
  monitor snapshots, web console, verification suite, tests, and docs.
