## MODIFIED Requirements

### Requirement: 反馈控制状态

控制台 MUST 显示所选时间每个可见PARTID的控制状态。控制模式 MUST 只提供“无控制”和“有控制”两档。
“有控制”必须执行当前表单中已配置并开启的L3、MC、CPU和CBusy硬件/模型机制；控制台不得提供P99软件慢闭环
自动改写MC QoS或BMAX的控制模式。
控制模式的两档选择 MUST 使用两段式布局，不得保留空白第三段；邻近的L3 QoS、3-bit QoS、CBusy反馈和地址交织入口
MUST 明确标为算法说明入口，不得显示成控制模式子选项。

#### Scenario: 有控制模式

- **WHEN** 用户选择“有控制”
- **THEN** 提交参数中的policy MUST 为`static_mpam`
- **AND** 所有已配置硬件机制参数 MUST 进入resolved config
- **AND** 不得生成P99软件慢闭环运行时设置更新
- **AND** 控制模式UI MUST 只把“无控制”和“有控制”显示为模式段
