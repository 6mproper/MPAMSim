## ADDED Requirements

### Requirement: MC QoS Combiner
MC scheduler MUST combine request-carried QoS, MPAM configured QoS, and MPAM adjust QoS through explicit configurable fields before optional 8-to-4 mapping.

`request_qos` MUST come from the Transaction request field and MUST NOT be inferred from actual service outcome.
`mpam_config_qos` MUST come from the per-PARTID MC QoS setting when enabled.
`mpam_adjust_qos` MUST be the signed sum of authorized MC-local adjustments: BMIN promote, soft BMAX demote, and service-deficit aging.

The combiner order MUST support:
- `adjust_before_request_combine`: `Q = combine(clamp(C + A, 0..7), R)`
- `adjust_after_request_combine`: `Q = clamp(combine(C, R) + A, 0..7)`

The combine operation MUST support:
- `replace`: use the left MPAM value and ignore `request_qos` for inter-PARTID QoS.
- `max`: use the maximum of the two inputs.
- `average`: use integer floor average of the two inputs.

The final scheduler QoS MUST still apply optional `mc_qos_map_8_to_4_enable` after raw 0..7 effective QoS is computed.

#### Scenario: Replace is equivalent across orders
- **GIVEN** `R=7`, `C=4`, and `A=-3`
- **WHEN** `mc_qos_combine_op` is `replace`
- **THEN** both combiner orders MUST produce raw effective QoS `1`

#### Scenario: Max exposes request override risk in path1
- **GIVEN** `R=7`, `C=4`, and `A=-3`
- **WHEN** `mc_qos_combine_op` is `max`
- **THEN** `adjust_before_request_combine` MUST produce raw effective QoS `7`
- **AND** `adjust_after_request_combine` MUST produce raw effective QoS `4`

#### Scenario: Average shows control dilution in path1
- **GIVEN** `R=7`, `C=4`, and `A=-3`
- **WHEN** `mc_qos_combine_op` is `average`
- **THEN** `adjust_before_request_combine` MUST produce raw effective QoS `4`
- **AND** `adjust_after_request_combine` MUST produce raw effective QoS `2`

### Requirement: QoS Combiner Evidence
MC monitor and request timeline evidence MUST expose enough fields to explain the effective QoS calculation.

#### Scenario: QoS inputs visible
- **WHEN** MC grants a request
- **THEN** the exported evidence MUST include request QoS, MPAM configured QoS, signed MPAM adjust QoS, combiner order, combiner operation, raw effective QoS, final effective QoS, and whether 8-to-4 mapping was enabled.
