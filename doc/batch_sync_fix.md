# ExmemoServer 批量同步覆盖问题修复说明

## 问题现象

ExRecord 在批量同步时，客户端可能提示“同步 2 条成功”，但 ExmemoServer 最终只保留 1 条记录。

## 根因

ExmemoServer 在创建文本记录时，默认 `addr` 使用秒级时间戳生成：

- `record_YYYYMMDD_HHMMSS`

当批量同步中的两条请求落在同一秒内时，会得到相同的 `addr`。服务端保存层会将 `user_id + addr` 视为同一条记录，从而把后一次写入当成更新，覆盖前一次内容。

## 修复方案

本次仅修改 ExmemoServer：

1. `dataforge/router.py` 中，`NoteCreate` 增加可选 `addr` 字段
2. `POST /dataforge/data/` 在未显式传入 `addr` 时，默认生成微秒级地址：
   - `record_YYYYMMDD_HHMMSS_ffffff`
3. `main.py` 中兼容 ExRecord 的 `/api/entry/data` 入口，同样改为微秒级 `addr`

这样即使同一秒内连续提交多条记录，也不会因地址冲突被覆盖。

## 影响范围

- 影响：ExmemoServer 文本记录创建接口
- 不影响：旧版 Django `exmemo/backend/app_dataforge`
- 不影响：已有历史数据结构

## 相关文件

- `ExmemoServer/dataforge/router.py`
- `ExmemoServer/main.py`

## 备注

旧版后端当前**不在本次修复范围内**。如果客户端继续连接旧版 backend，仍可能遇到同秒覆盖问题；本轮建议优先切到 ExmemoServer 验证。