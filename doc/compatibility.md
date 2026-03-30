# 过渡期数据兼容方案

## 背景

ExmemoServer 和旧 Django 后端共用同一个 PostgreSQL 数据库（`store_entry` 表）。旧后端依赖 `block_id` 和 `raw` 字段读取数据，不能直接砍掉这些字段。

本文档描述过渡期内 ExmemoServer 如何写入数据才能让旧后端正常读取。

## 写入：双写兼容

ExmemoServer 创建一条记录时：

1. **文件落盘**：将正文序列化为 Markdown，存入文件存储（路径格式 `<类型>/<年>/<月>/<UUID>.md`）
2. **写两条数据库记录**（模拟旧系统的分块逻辑）：
   - `block_id = 0`：`raw` 存前 200 字（充当摘要）
   - `block_id = 1`：`raw` 存完整文本
   - 两条记录都写入 `path` 字段，指向文件存储中的实际路径

旧 Django 后端读取时感知不到差异。

## 读取：fallback 机制

- 有 `path` → 从文件存储读完整内容
- 无 `path` → fallback 到 `raw` 字段（`block_id = 1` 的记录）

## 更新和删除

- **更新**：先更新文件存储，再同步刷新 `block_id = 0` 和 `1` 两条记录的 `raw`、时间戳、`path`
- **删除**：同时删除文件和该 UUID 下所有 `block_id` 的数据库记录

## 清理计划

这套双写是临时方案。旧后端完全停用后：

1. 洗数脚本：将只有 `raw` 没有 `path` 的历史数据批量导出为 Markdown 文件
2. 精简数据库：移除 `raw`、`block_id`、`embeddings` 等冗余字段
3. 删除双写代码
