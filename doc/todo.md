# ExmemoServer TODO

## 阶段一：dataforge CRUD 完整可用（当前）

目标：ExmemoServer 的 dataforge 模块能完整替代旧后端 `app_dataforge` 的读写功能。

### 认证

- [ ] 移除 `API_TOKEN` 简单鉴权（`env_default` 中的 `API_TOKEN=800811`），统一用 JWT
- [ ] 确认所有 router 都挂了 JWT 鉴权，不留未保护接口

### API 兼容（支持 skill 和旧客户端）

- [ ] 统一 API 路径：消除 `/api/entry/data` 和 `/dataforge/data/` 的重复入口
- [ ] 列表接口加标准分页：返回 `{count, next, previous, results}` 格式
- [ ] 搜索参数兼容：支持 `keyword`（映射到内部的 `search`）、`max_count`（映射到 `limit`）
- [ ] 下载接口文件名修复：从 `path` 取 basename（含扩展名），不用 `title`
- [ ] 接口错误返回格式统一

### 数据存储

- [ ] 完善 CRUD 接口（列表、按 ID 查、更新、删除都跑通）
- [ ] 文件存储的上传/下载/删除封装到 `dataforge/storage.py`
- [ ] 双写兼容逻辑（见 `compatibility.md`）
- [ ] 确定文件存储方案（MinIO vs 本地文件系统）

### 运维

- [ ] `docker-compose.yml` 补健康检查
- [ ] 启动时校验必填环境变量，缺失给明确报错
- [ ] 统一日志格式

## 阶段二：接口稳定 + Android SDK

前置条件：阶段一完成。

- [ ] ASR / LLM / record 模块接口版本化，契约稳定
- [ ] 创建 `exmemo_android_sdk`，封装登录 + CRUD
- [ ] ExRecord / ExReader 接入 SDK，移除各自独立的 client 代码

## 阶段三：暂缓，阶段一完成后再评估

- Obsidian 双向同步（`app_sync` 迁移）
- 异步任务队列（Celery / RQ）
- Web 前端切换到 ExmemoServer
