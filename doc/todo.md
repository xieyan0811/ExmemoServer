# ExmemoServer TODO

## 认证与安全

- [ ] **移除 API_TOKEN 简单鉴权**：`env_default` 中的 `API_TOKEN=800811` 及相关校验代码需删除，统一使用 JWT（fastapi-users）认证，不保留双轨认证
- [ ] 确认所有 router 都挂载了 JWT 鉴权依赖，不留未保护的接口

## 数据存储（阶段一）

- [ ] 完善 `dataforge/` 模块的完整 CRUD 接口（查询列表、按 ID 查询、更新、删除）
- [ ] MinIO 存取逻辑：上传/下载/删除文件，统一封装到 `dataforge/storage.py`
- [ ] 实现 `data_storage_compatibility.md` 中的双写兼容逻辑（新写入同时写 MinIO + 旧 `raw` 字段）
- [ ] 接口返回格式统一（统一错误结构、分页格式）
- [ ] 接口版本化（考虑 `/api/v1/` 前缀，为后续变更留余地）

## ASR / LLM

- [ ] 整理 `asr/`、`llm/`、`record/` 模块的接口文档（参数、返回值、错误码）
- [ ] 确认 Whisper 模型配置（`ASR_MODEL`）支持本地 Whisper 部署（不强依赖 OpenAI API）

## 运维 / 部署

- [ ] `docker-compose.yml` 补充健康检查（healthcheck）配置
- [ ] 环境变量校验：启动时检查必填项（`OPENAI_API_KEY`、`JWT_SECRET` 等），缺失时给出明确错误提示
- [ ] 日志配置：统一日志格式，区分 access log 和 application log

## Android SDK（exmemo-sync-sdk，待阶段一完成后启动）

- [ ] 创建 `exmemo-sync-sdk` Android Library 仓库
- [ ] 实现登录模块：`LoginActivity` + JWT Token 存储（`EncryptedSharedPreferences`）+ Token 刷新
- [ ] 封装 Entry CRUD 接口（对应 `dataforge/` 模块）
- [ ] 在 ExRecord 中替换现有 `ApiService` 为 SDK 调用
- [ ] 在 ExReader 中接入 SDK，实现书摘上传