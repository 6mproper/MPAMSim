## 1. 规格

- [x] 1.1 新增resctrl-like软件组OpenSpec需求。
- [x] 1.2 更新当前中文模型spec中的软件配置接口章节。

## 2. 配置转换

- [x] 2.1 在默认参数中增加可选resctrl配置，不影响默认原始线程模式。
- [x] 2.2 解析CTRL_MON group的`schemata`、`tasks`和`cpus_list`。
- [x] 2.3 解析MON group并映射到同一PARTID作用域下的PMG。
- [x] 2.4 启用resctrl时把软件组转换为现有`stimulus_configs`和`partid_configs`。
- [x] 2.5 校验重复PARTID、非法schema、非法任务/CPU范围和unsupported模式。

## 3. UI

- [x] 3.1 新增resctrl配置页签和紧凑软件组编辑表。
- [x] 3.2 显示mount/options、info、group树、内部PARTID/PMG映射和last_cmd_status。
- [x] 3.3 显示resctrl风格`mon_data`，复用现有监控结果。
- [x] 3.4 每个新增配置控件提供点击解释。

## 4. 验证

- [x] 4.1 增加构建器单元测试，覆盖task优先于CPU组、schema映射和错误输入。
- [x] 4.2 增加UI静态测试，确认resctrl页签、层开关和帮助存在。
- [x] 4.3 运行相关pytest、OpenSpec校验和浏览器冒烟。
