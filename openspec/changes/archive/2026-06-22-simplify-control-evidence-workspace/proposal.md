## Why

当前Web界面使用多个等权页签展示控制证据，用户需要在页签间切换查看L3占用、MC带宽、CBusy状态和控制事件，缺乏统一时间游标和因果对照视图。将页签收敛为以PARTID为维度的单页证据工作区，在共享时间游标下并行显示target、actual、raw、filtered、state和event，消除认知碎片。

## What Changes

- 用配置驱动主工作区替代等权页签
- 默认突出：启用控制、活动PARTID、违规、饱和和不可达状态
- PARTID选择条支持单选/多选/聚合视图
- 共享时间游标：3-5张自适应时间图 + 控制事件时间线
- 保留CPU/Ring/L3/MC/filter/CBusy诊断入口

## Capabilities

### Modified Capabilities

- `interactive-simulation-console`: 证据工作区从多页签收敛为PARTID驱动的统一视图

## Impact

- `src/web/static/index.html`: 重构主布局
- `src/web/static/app.js`: 重构渲染逻辑
- `src/web/static/styles.css`: 自适应布局样式
- `src/web/server.py`: 可能需要数据过滤端点
