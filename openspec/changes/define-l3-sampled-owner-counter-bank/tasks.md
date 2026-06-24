## 1. 规格

- [x] 1.1 定义L3 sampled-owner counter-bank硬件契约。
- [x] 1.2 明确rotating sampling读取counter bank，不表示一个周期扫描tag/way。
- [x] 1.3 明确L3 UI应使用sampled/published/control input命名，MC继续使用latest filtered bandwidth。

## 2. 实现

- [x] 2.1 CacheMSC在fill/replacement时维护per-offset owner counter。
- [x] 2.2 raw/control sampled owner从当前offset counter bank读取。
- [x] 2.3 UI和帮助文案消除L3 latest filtered命名歧义。

## 3. 验证

- [x] 3.1 增加测试证明sampled owner由counter bank维护，非当前offset变化不提前进入控制输入。
- [x] 3.2 运行L3、Web metadata、OpenSpec和关键回归测试。
- [x] 3.3 浏览器检查控制总览L3图例/卡片命名。
