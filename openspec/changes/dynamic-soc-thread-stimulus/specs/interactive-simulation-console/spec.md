## MODIFIED Requirements

### Requirement: 动态硬件线程激励编辑器

控制台 MUST 根据SoC页签的`active_cores × threads_per_core`显示激励行，并按slot稳定映射到
`cpuN.tM` requester。修改SoC核数或每核线程数后，控制台 MUST 自动裁剪或补齐激励行；
16组PARTID控制表 MUST 保持固定。

#### Scenario: 检查映射

- **WHEN** `active_cores=4`且`threads_per_core=2`
- **THEN** 编辑器 MUST 显示8行并覆盖`cpu0.t0`到`cpu3.t1`

#### Scenario: 扩展到16C2T

- **WHEN** `active_cores=16`且`threads_per_core=2`
- **THEN** 编辑器 MUST 显示32行并覆盖`cpu0.t0`到`cpu15.t1`
