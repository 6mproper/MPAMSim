## 背景

P1已经定义为最小闭环MVP，但当前界面和预设仍存在两个会误导验证的问题：

- 部分UI标签仍用`P0/P1/P2`表示`PARTID 0/1/2`，和P1阶段命名冲突。
- `MC BMIN / QoS 竞争`预设中两个顺序流从相同地址0开始，L3同line MSHR合并会让
  `PARTID 1`作为waiter完成，而MC只看到owner `PARTID 0`的请求，导致`PARTID 1`
  MC带宽显示为0。

## 修改目标

- UI可见PARTID标签统一显示为`PARTID N`或紧凑的`ID N`，不再显示`P0/P1/P2`。
- 常规workload支持可配置`address_base_bytes`，用于给不同PARTID配置不同地址窗口。
- 控制效果预设为不同PARTID设置不同地址基址，避免非目标的同line合并掩盖MC/L3归因。
- 增加P1最小闭环MVP测试，覆盖：
  1. L3 CMAX限制新增allocation；
  2. MC BMAX改变effective QoS或产生hard block；
  3. CBusy返回RN后降低对应requester内同PARTID effective OSTD，MC ID仅作来源和诊断字段。

## 非目标

- 不新增`validation_stage`运行模式。
- 不新增P1专用数据面或UI通路。
- 不关闭真实L3同line merge机制。
- 不扩展NoC QoS、credit/VC或完整DRAM模型。
