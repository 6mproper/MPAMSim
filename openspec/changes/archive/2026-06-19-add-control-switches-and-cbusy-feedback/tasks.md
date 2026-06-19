## 1. Specification

- [x] 1.1 Add and strictly validate the OpenSpec change.

## 2. Configuration And Settings

- [x] 2.1 Add per-control enable fields to schema, loader, validation, and settings.
- [x] 2.2 Add CBusy detector/feedback parameters and per-level OSTD caps.
- [x] 2.3 Add compact independent switches to the 16-PARTID web editor.

## 3. Enforcement

- [x] 3.1 Apply independent cache and MC enable semantics.
- [x] 3.2 Implement per-MC/per-PARTID four-level CBusy detection.
- [x] 3.3 Implement delayed max-level feedback and requester effective OSTD enforcement.
- [x] 3.4 Separate configured-OSTD and CBusy source-stall accounting.

## 4. Observability

- [x] 4.1 Export CPU effective OSTD, CBusy level/stall/transitions.
- [x] 4.2 Export MC detector inputs, levels, caps, and transitions.
- [x] 4.3 Display configured/enabled/effective controls and CBusy effects.

## 5. Verification

- [x] 5.1 Add switch-semantics and CBusy mechanism tests.
- [x] 5.2 Add deterministic no-control/BMAX/CBusy/combined comparison.
- [x] 5.3 Update official-model-boundary docs and skill conclusions.
- [x] 5.4 Run checks, pytest, OpenSpec strict validation, and browser verification.
