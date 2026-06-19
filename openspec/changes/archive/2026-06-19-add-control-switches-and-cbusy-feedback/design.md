# Design: Independent Controls And CBusy Feedback

## Independent Enable Semantics

Every PARTID has these switches:

- `cpbm_enable`
- `cmin_enable`
- `cmax_enable`
- `bmin_enable`
- `bmax_enable`
- `priority_enable`
- `cbusy_enable`

Disabled controls retain their configured values but use neutral effective behavior:

- CPBM disabled: every way is eligible.
- CMIN disabled: replacement protection is zero.
- CMAX disabled: maximum is the number of currently eligible ways.
- BMIN disabled: no under-minimum scheduling bonus.
- BMAX disabled: no hard token stall or soft over-limit penalty.
- Priority disabled: effective priority is zero.
- CBusy disabled: the MC reports level zero for that PARTID and releases any source cap.

The global `no_control` policy still disables every enforcement function while retaining monitors and configured values.

## CBusy Detector

Each memory controller evaluates every configured PARTID at a configurable fast sample period. The detector uses:

- serviced bandwidth divided by enabled BMAX;
- per-PARTID queued requests divided by MC queue depth;
- hard-limit block activity;
- whether the controller is contended.

Bandwidth over BMAX alone does not assert CBusy without contention. Queue thresholds or hard-block activity may assert CBusy directly.

The detector chooses the highest matching level:

- level 0: clear;
- level 1: light pressure;
- level 2: sustained pressure;
- level 3: severe pressure.

Rising levels take effect immediately. Falling levels require the configured release-hold sample count and recover one level at a time.

## Feedback And Source Enforcement

An MC level change is delivered after the configured feedback latency. CPU requester state keeps one level per MC/PARTID and aggregates:

```text
effective_level = max(level_by_mc)
effective_ostd = min(configured_max_ostd, cap_for_effective_level)
```

The source always preserves an OSTD floor of at least one. The generic requester-wide configured maximum remains an additional upper bound.

The generator attributes retry time to:

- configured OSTD stall when the requester-wide cap is reached;
- CBusy stall when the per-PARTID effective cap is reached first.

## Observability

CPU monitor rows add:

- effective maximum OSTD;
- CBusy level;
- CBusy stall time;
- feedback transition count.

MC monitor rows add per-PARTID:

- CBusy enabled and level;
- observed bandwidth/BMAX ratio;
- queue ratio;
- transition/assertion counts;
- effective OSTD cap sent for the level.

The resource dashboard shows switches/configured values in the MPAM editor and effective state in CPU/MC monitoring.

## Validation

Use the same topology, workload, duration, and seed for:

1. no BMAX and no CBusy;
2. BMAX only;
3. CBusy only;
4. BMAX plus CBusy.

CBusy must reduce queue area or peak and expose source stall/effective OSTD changes. Combined control must preserve forward progress and avoid rapid release oscillation.
