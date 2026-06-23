## 1. 规格

- [x] 1.1 新增OpenSpec change，说明默认关闭L3 same-line read merge的原因。
- [x] 1.2 更新`soc-flow-simulation`，区分默认关闭和显式开启两种场景。
- [x] 1.3 更新`interactive-simulation-console`，要求UI默认关闭该开关。

## 2. 实现

- [x] 2.1 `CacheConfig`默认值改为`False`。
- [x] 2.2 YAML loader缺省值改为`False`。
- [x] 2.3 Web默认参数和构建fallback改为`False`。
- [x] 2.4 UI checkbox默认不勾选。

## 3. 验证

- [x] 3.1 更新Web配置测试，验证默认构建结果关闭合并。
- [x] 3.2 更新UI元数据测试，验证HTML默认checkbox未勾选。
- [x] 3.3 运行OpenSpec strict、pytest和前端语法检查。
