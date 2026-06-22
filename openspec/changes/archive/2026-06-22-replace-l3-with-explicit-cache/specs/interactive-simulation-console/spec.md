## ADDED Requirements

### Requirement: L3数据面资源配置和证据

控制台 MUST 配置replacement、miss detect、fill latency、MSHR、fill buffer和same-line merge，
并显示actual occupancy、sampled estimate、误差、merge和fill压力。

#### Scenario: 查看MSHR说明

- **WHEN** 用户指向MSHR、fill或merge配置
- **THEN** 显示分配、等待、合并、owner、完成、前向进展和监控证据
