## ADDED Requirements

### Requirement: 控制验证优先默认界面

控制台 MUST 将默认结果界面组织为控制总览、因果链和高级证据三个层级，
默认视图只突出CPU OSTD控制与MSC监控/控制状态。

#### Scenario: 打开仿真结果

- **WHEN** 用户打开或完成一次仿真
- **THEN** 默认可见区域显示CPU OSTD控制、L3控制状态和MC控制状态
- **AND** NoC flit、MSHR、fill buffer、candidate/grant和完整日志不在默认首屏平铺

### Requirement: CPU OSTD控制总览

控制总览 MUST 按PARTID显示CPU源头控制是否生效，并在CBusy按目标MC生效时保留目标MC维度。

#### Scenario: CBusy限制源头

- **WHEN** 某PARTID收到目标MC返回的CBusy等级
- **THEN** CPU OSTD视图显示configured OSTD、effective OSTD cap、CBusy level、target MC、当前outstanding和source stall

### Requirement: MSC监控与控制总览

控制总览 MUST 对L3和MC显示目标、控制读取的filtered监控、actual观测值和控制状态。

#### Scenario: 查看MSC控制状态

- **WHEN** 用户选择一个PARTID
- **THEN** L3区域显示CMIN/CMAX目标范围、filtered MPAM占用、physical actual占用和替换压力事件
- **AND** MC区域显示BMIN/BMAX目标范围、filtered MPAM带宽、actual service带宽、queue、effective QoS和soft/hard状态

### Requirement: 固定图例语义

控制台 MUST 使用固定图形语义显示控制效果，避免同一图例同时表达过多含义。

#### Scenario: 查看单PARTID趋势

- **WHEN** 用户查看单个PARTID的控制趋势
- **THEN** 目标范围显示为目标带，filtered MPAM monitor显示为粗主线，actual显示为细灰线，控制动作显示为橙色事件标记
- **AND** raw monitor默认隐藏，disabled控制不显示为0目标线

### Requirement: 多PARTID避免曲线过载

控制台 MUST 在多PARTID比较时避免把多个PARTID和多个信号语义叠在同一张图。

#### Scenario: 选择多个PARTID

- **WHEN** 用户选择多个PARTID进行比较
- **THEN** 控制台使用单信号多PARTID小图、热力图或状态矩阵
- **AND** 不同时混画target、raw、filtered、actual和event的多PARTID全量曲线

### Requirement: 高级证据默认折叠

控制台 MUST 保留模型调试证据，但默认折叠到高级证据区域。

#### Scenario: 需要定位异常

- **WHEN** 用户打开高级证据
- **THEN** 可以查看raw MPAM、监控误差、MSHR、fill buffer、NoC ring、candidate/grant、deficit和完整控制日志
