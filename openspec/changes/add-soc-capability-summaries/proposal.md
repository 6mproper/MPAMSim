## 背景

SoC页签用于配置多核、L3、NoC和Memory Controller资源，但MC本地时钟目前放在策略页签，用户难以在同一位置理解MC能力。各资源分组也缺少根据当前配置实时计算的能力摘要。

## 目标

- 将MC本地时钟配置移动到SoC页签的Memory Controller分组。
- 在SoC页签的多核、L3、NoC、Memory Controller分组末尾增加单独能力摘要行。
- 摘要行根据当前表单实时计算，不触发仿真。

## 非目标

- 不改变仿真模型和配置schema。
- 不把摘要值写入提交给仿真的配置。
- 本次不上传Git。
