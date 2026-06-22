## 1. Transaction旁带

- [x] 1.1 Transaction增加`carry_cbusy_level: int = 0`字段

## 2. MC CBusy采样重构

- [x] 2.1 删除MC构造函数的`on_cbusy`参数
- [x] 2.2 将`_evaluate_cbusy`替换为`_sample_cbusy(partid) -> int`方法，只计算和返回档位，不触发回调
- [x] 2.3 删除`_publish_cbusy`方法
- [x] 2.4 删除MC初始化中的`cbusy-sample`定时调度
- [x] 2.5 在`_dispatch`完成时调用`_sample_cbusy`并将结果写入`request.carry_cbusy_level`

## 3. 返回路径旁带

- [x] 3.1 删除`Simulation._cbusy_feedback`方法
- [x] 3.2 删除MC构造中`on_cbusy=self._cbusy_feedback`参数
- [x] 3.3 在`Simulation._complete`中从`request.carry_cbusy_level`读取CBusy，若非零则调用`requester.set_cbusy`
- [x] 3.4 删除`Simulation._delivered_cbusy_levels`字典，CBusy状态移交RN维护

## 4. 配置清理

- [x] 4.1 标记`cbusy_feedback_latency_ns`为弃用（保留schema兼容，值不再生效）
- [x] 4.2 Web配置界面移除或灰化`cbusy_feedback_latency_ns`控件

## 5. 验证

- [x] 5.1 运行现有CBusy相关确定性测试，确认准入行为不变
- [x] 5.2 添加测试：MC状态变化但无返回时RN不更新
- [x] 5.3 添加测试：返回到达前CPU继续使用旧档位
- [x] 5.4 添加测试：RSP、单DAT和多flit DAT都只在终端返回时更新一次
- [x] 5.5 添加测试：CBusy不取消已发请求、不阻塞响应、不修改MC QoS
- [x] 5.6 运行完整回归`pytest`，所有测试通过
