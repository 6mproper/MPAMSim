## Context

当前结果面板有10个等同权重的页签，控制证据分散在多个table和chart中。PARTID选择内嵌在单个页签内，无法跨视图联动。

## Goals / Non-Goals

**Goals:**
- 顶部PARTID选择器，影响所有视图
- 减少页签到4个核心视图
- 共享控制事件时间线
- PARTID用颜色区分，信号类型用线型区分

**Non-Goals:**
- 不改变仿真引擎
- 不改动配置面板
- 不引入新图表库

## Decisions

1. PARTID选择用chip按钮，支持多选/全部切换，颜色映射到图表
2. 控制事件时间线用canvas绘制（简单rect标记），颜色对应用PARTID
3. 保留现有effect chart grid但增加事件时间线canvas
