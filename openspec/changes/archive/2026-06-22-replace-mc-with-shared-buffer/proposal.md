## 为什么

当前MC为每PARTID FIFO，只比较每个队首，并用token bucket和逐请求时间戳aging控制服务。这不符合
已确认的共享buffer全候选、3-bit QoS、旋转slot、上一监控周期带宽控制和低PPA class deficit。

## 修改内容

- 每个MC使用一个固定深度共享buffer，所有valid/ready entry参与调度。
- 同line包含write时保持sequence顺序；read/read可以重排。
- 有效QoS由base、BMIN提升、soft BMAX降低和可选service deficit组成。
- 同最高QoS使用rotating buffer-slot scan，不用enqueue时间比较。
- 每256个MC本地拍计算raw和滤波带宽，下一周期控制读取该发布值。
- BMIN/soft BMAX只在至少两个PARTID竞争时改变QoS。
- hard BMAX按整个监控周期门控该PARTID所有entry，保留请求并允许过冲/锯齿。
- 增加可配滞回、monitor clock/period/filter和低PPA service deficit。
- CBusy使用每PARTID buffer count、滤波带宽和hard block状态。

## 影响能力

- `soc-flow-simulation`：替换MC buffer和调度数据面。
- `mpam-memory-bandwidth`：替换BMIN/BMAX执行算法。
- `interactive-simulation-console`：增加MC监控周期、滤波、滞回和aging配置及证据。

## 影响范围

- 修改MemoryControllerMSC、配置、监控、Web和机制验证。
- 仍不建模DRAM bank/row timing；ready mask目前只含ordering和hard BMAX。
