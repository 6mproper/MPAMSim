## ADDED Requirements

### Requirement: 可配置L3 CBusy响应

L3 MUST 支持可配置的CBusy响应动作。开启时，L3在fill返回路径用MSHR owner本地上下文
把返回旁带中的CBusy level归因到PARTID，并仅限制同PARTID后续新miss的MSHR分配。

#### Scenario: 返回旁带归因PARTID

- **WHEN** MC返回的DAT/RSP携带CBusy level并完成某个L3 MSHR
- **THEN** L3 MUST 使用该MSHR owner request的PARTID更新本地CBusy状态
- **AND** MUST NOT 要求L3保存MC issue time作为控制输入

#### Scenario: 新miss MSHR被限制

- **WHEN** L3 CBusy响应开启、PARTID P的level大于0且P的当前MSHR数量达到该level cap
- **THEN** P的后续新miss MUST 等待MSHR准入
- **AND** hit、fill、response和已分配MSHR MUST NOT 被CBusy门控

#### Scenario: L3响应关闭

- **WHEN** L3 CBusy响应开关关闭
- **THEN** L3 MUST 忽略返回CBusy动作并按普通MSHR容量准入新miss
