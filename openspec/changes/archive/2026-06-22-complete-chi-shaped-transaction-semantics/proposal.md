## Why
Transaction的CompletionCondition枚举存在但未使用。read应在最后DAT返回后完成，write应在RSP返回后完成。

## What Changes
- 在Request创建时根据operation设置completion_condition（READ_DATA或WRITE_RESPONSE）
- collector.on_complete读取completion_condition记录到timeline
