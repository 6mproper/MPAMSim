## ADDED Requirements

### Requirement: QoS Combiner Configuration Import
The interactive console MUST preserve QoS combiner parameters and per-stimulus request QoS through import, edit, simulation run, and export.

#### Scenario: Importable combiner comparison files
- **GIVEN** a JSON config file using schema `mpamsim.config.parameters`
- **WHEN** it contains `mc_qos_combiner_order`, `mc_qos_combine_op`, and `stimulus_configs[*].request_qos`
- **THEN** importing the file MUST restore those fields in the UI
- **AND** running the simulation MUST pass them into the backend configuration.

### Requirement: QoS Combiner Comparison Assets
The repository output directory MUST contain importable comparison files for both combiner paths and all three combine operations.

#### Scenario: Six-case comparison
- **WHEN** the comparison assets are generated
- **THEN** there MUST be six JSON files covering `adjust_before_request_combine` and `adjust_after_request_combine` crossed with `replace`, `max`, and `average`
- **AND** the comparison summary MUST identify the expected raw effective QoS difference for the shared reference input `R=7, C=4, A=-3`.
