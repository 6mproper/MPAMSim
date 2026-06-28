# MC QoS组合路径对比

参考输入：`request_qos R=7`，`mpam_config_qos C=4`，`mpam_adjust_qos A=-3`。

| case | 公式raw QoS | grant raw范围 | soft控制raw范围 | 最后活跃raw均值 | 最后活跃R/C/A均值 | soft事件 | P0/P1总带宽Gbps | 最后活跃带宽Gbps |
| --- | ---: | --- | --- | ---: | --- | ---: | --- | ---: |
| qos_combiner_path1_replace | 1 | 4..4 | 0..0 | 4.00 | 7.00/4.00/0.00 | 0 | 7.680/7.885 | 16.000 |
| qos_combiner_path1_max | 7 | 7..7 | 7..7 | 7.00 | 7.00/4.00/-3.00 | 152 | 15.462/0.102 | 16.000 |
| qos_combiner_path1_average | 4 | 4..5 | 4..4 | 4.00 | 7.00/4.00/-3.00 | 152 | 15.462/0.102 | 16.000 |
| qos_combiner_path2_replace | 1 | 4..4 | 0..0 | 4.00 | 7.00/4.00/0.00 | 0 | 7.680/7.885 | 16.000 |
| qos_combiner_path2_max | 4 | 7..7 | 0..0 | 7.00 | 7.00/4.00/0.00 | 0 | 7.680/7.885 | 16.000 |
| qos_combiner_path2_average | 2 | 2..5 | 2..2 | 2.00 | 7.00/4.00/-3.00 | 152 | 15.462/0.102 | 16.000 |

验证读法：
- `公式raw QoS` 是同一组R=7、C=4、A=-3下的确定性公式检查，应作为组合逻辑是否正确的主判据。
- `P0/P1总带宽` 来自可导入配置跑出的端到端结果，用于观察公式差异是否在竞争下改变服务份额。
- `soft控制raw范围` 只统计P0在soft BMAX降档已生效时仍拿到grant的窗口；`0..0`表示该run里P0在soft状态下没有再拿到grant，通常说明背景PARTID赢得仲裁。
- `replace`：两条路径在该参考输入下等价，都是1。
- `max`：路径1可能让高request_qos覆盖soft BMAX降档；路径2把MC adjust放在最后，降档仍可见。
- `average`：路径2同样把MC adjust作为最后控制动作，因此raw QoS比路径1更低。
