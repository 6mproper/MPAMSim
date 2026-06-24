## MODIFIED Requirements

### Requirement: 每个monitor group采样1个set

L3 MUST 在每个monitor group中维护可轮转读取的sampled-owner counter bank，并把采样访问和
占用按monitor group比例估算。采样offset MUST 支持固定offset 0和按本地监控周期轮转两种模式。

#### Scenario: 访问固定采样set

- **WHEN** `sampling_mode=fixed_first`且`set_index modulo monitor_group_sets == 0`
- **THEN** 更新采样访问计数
- **AND** fill/replacement MUST 更新offset 0的sampled-owner counter bank

#### Scenario: 访问轮转采样set

- **WHEN** `sampling_mode=rotating`且`set_index modulo monitor_group_sets == sampling_offset`
- **THEN** 更新当前offset对应的采样访问计数
- **AND** fill/replacement MUST 更新`set_index modulo monitor_group_sets`对应的sampled-owner counter bank

#### Scenario: 访问非采样set

- **WHEN** 访问组内其他set
- **THEN** 当前窗口不为该访问更新采样访问计数

## ADDED Requirements

### Requirement: L3 sampled-owner counter bank

L3 MPAM occupancy监控 MUST 基于sampled-owner counter bank，而不是在监控边界瞬时扫描
所有tag/way owner。每条line的owner变化 MUST 在fill、replacement或后续invalidate路径上更新：

```text
offset = set_index mod monitor_group_sets
owner_count[offset][PARTID] += new_line_delta
owner_count[offset][old_PARTID] -= victim_delta
```

`fixed_first` MUST 固定读取offset 0的counter bank。`rotating` MUST 每隔
`sampling_rotation_period_monitor_cycles`个L3本地监控周期切换offset，并读取当前offset的
counter bank。该语义表示低PPA计数器监控近似，不表示硬件在一个监控边界内扫描所有sampled
set/way。

#### Scenario: Counter bank更新

- **WHEN** L3 fill替换一个valid victim line
- **THEN** victim owner对应offset/PARTID counter MUST 减1
- **AND** 新line owner对应offset/PARTID counter MUST 加1

#### Scenario: Rotating读取counter bank

- **WHEN** `sampling_mode=rotating`且offset在监控边界切换
- **THEN** raw sampled owner MUST 来自切换后窗口当前offset对应的counter bank
- **AND** 不得要求监控边界扫描所有sampled set/way才能得到该值

## MODIFIED Requirements

### Requirement: 三平面误差证据

监控 MUST 同时导出physical actual、raw sampled-owner、published/control sampled-owner及其差值。
L3 occupancy UI SHOULD 使用sampled owner或published sampled occupancy命名，不应把L3 occupancy
主语义显示为带宽式latest filtered；MC bandwidth等速率量 MAY 继续显示latest filtered。

#### Scenario: L3 occupancy命名

- **WHEN** UI显示L3 occupancy发布监控值
- **THEN** 文案 SHOULD 使用published sampled或sampled owner
- **AND** MUST NOT 暗示L3 occupancy控制输入使用带宽式递归滤波
