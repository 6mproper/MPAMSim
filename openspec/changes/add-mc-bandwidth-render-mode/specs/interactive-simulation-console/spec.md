## MODIFIED Requirements

### Requirement: 控制总览区分control input和latest filtered

控制总览 MUST 将控制器实际读取的锁存值显示为control input。L3 occupancy MUST 把最新发布值显示为
published sampled-owner；MC bandwidth等速率量 MAY 继续使用latest filtered。
控制总览 MUST 为MC目标带/监控/实际图提供显示模式选择，至少包括插值曲线和硬件阶梯。
显示模式 MUST 只改变前端画法，不得改变MC监控、滤波、控制输入、QoS调整或仿真结果。

#### Scenario: L3和MC主图

- **WHEN** 用户查看控制总览
- **THEN** 主图默认 MUST 显示目标带、control input、actual和控制事件
- **AND** L3 latest published sampled-owner SHOULD 可选显示
- **AND** MC actual MUST 表示完整统计窗口内的raw actual bandwidth，不得默认使用moving average
- **AND** MC actual MA MAY 作为独立可选趋势层显示，且默认关闭
- **AND** MC latest filtered bandwidth SHOULD 可选显示
- **AND** raw sampled-owner、raw bandwidth和控制事件仍按显示层开关控制

#### Scenario: 文案区分

- **WHEN** UI解释raw、published、control input或actual
- **THEN** L3 occupancy文案 MUST 说明raw sampled-owner来自当前采样offset counter bank
- **AND** published sampled-owner MUST 说明为监控边界对外发布的sampled-owner快照
- **AND** MC bandwidth文案 MUST 说明filtered表示最新发布滤波带宽
- **AND** control input MUST 表示控制器读取的锁存监控值
- **AND** actual MUST 标注为验证用观测值，不得描述为控制输入
- **AND** MC actual MA MUST 标注为前端趋势观察层，不得描述为actual raw或控制输入

#### Scenario: MC带宽显示模式

- **WHEN** 用户选择插值曲线模式
- **THEN** MC actual、raw、control input和latest filtered MUST 以折线连接采样点
- **AND** 图上 MUST 保留采样点提示，用于说明曲线来自离散采样而不是连续硬件状态
- **AND** 不创建新的仿真任务

#### Scenario: MC硬件阶梯回看

- **WHEN** 用户选择硬件阶梯模式
- **THEN** MC actual、raw、control input和latest filtered MUST 按周期锁存值绘制为阶梯线
- **AND** 不得改变MC监控、滤波或控制算法
