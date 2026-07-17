## ADDED Requirements

### Requirement: CPU CBusy反馈单变量A/B配置

仓库 MUST 提供两份Web UI可导入的CPU CBusy反馈A/B配置。两份配置 MUST 使用相同拓扑、激励、PARTID、BMAX、CBusy阈值、OSTD档位、监控滤波参数、仿真时长和seed，并且 MUST 只以`cpu_cbusy_response_enable`区分开环和闭环。

#### Scenario: 开环基准

- **WHEN** 用户导入CPU不响应配置并运行仿真
- **THEN** MC MUST 仍然生成并返回PARTID 1的CBusy证据
- **AND** CPU effective OSTD MUST 保持configured OSTD
- **AND** CPU CBusy stall MUST 保持为0

#### Scenario: 闭环反馈

- **WHEN** 用户导入CPU响应配置并运行仿真
- **THEN** MC返回的CBusy MUST 降低PARTID 1的CPU effective OSTD
- **AND** PARTID 1 MUST 产生CPU CBusy stall
- **AND** PARTID 1带宽 SHOULD 降低，PARTID 0带宽 SHOULD 提升
- **AND** 目标未达、过冲或振荡 MUST 继续仿真并作为控制结果保留

#### Scenario: 排除其他控制路径

- **WHEN** 用户比较两份A/B配置
- **THEN** L3 CBusy响应、L3 QoS、BMIN、MC QoS、aging和Hard BMAX MUST 在两组中保持关闭
- **AND** Soft BMAX固定QoS降档 MUST 为0
- **AND** 带宽比较 MUST 使用相同统计窗口和纵轴单位
