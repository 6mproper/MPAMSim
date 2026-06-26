## MODIFIED Requirements

### Requirement: 直接配置

控制台 MUST 允许用户配置SoC、16线程激励、policy和16组PARTID控制，
无需修改源码。控制台初始默认值 MUST 使用可手动开启的无快反馈基线：

- `l3_qos_scheduler_enable=false`
- `l3_cbusy_response_enable=false`
- `cpu_cbusy_response_enable=false`
- `l3_sets=20480`
- `l3_ways=20`

#### Scenario: 加载默认几何和控制开关

- **WHEN** 控制台加载默认配置或请求默认参数
- **THEN** L3默认几何 MUST 为20480 sets、20 ways
- **AND** L3 QoS调度 MUST 默认为关闭
- **AND** L3响应CBusy MUST 默认为关闭
- **AND** CPU响应CBusy MUST 默认为关闭
- **AND** 用户仍 MUST 能通过现有开关手动开启这些控制功能
