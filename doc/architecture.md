# ExmemoServer 架构设计

## 定位

ExmemoServer 是 Exmemo 知识管理系统的统一后端，基于 FastAPI，逐步接管旧 Django 后端（exmemo/backend）的核心功能。

**核心原则**：只做知识管理。笔记的存储、输入输出、AI 辅助整理是不可动摇的核心；旧后端里的饮食记录、翻译、论文辅助等外围功能一律不迁入。

## 整体架构：一后端、多前端、多调用方

```
┌─────────────────────────────────────────┐
│              ExmemoServer               │
│  (FastAPI + PostgreSQL + 文件存储)       │
│                                         │
│  dataforge/  ── 数据 CRUD + 文件存取     │
│  asr/        ── 语音识别 (Whisper)       │
│  llm/        ── 大模型文本处理           │
│  record/     ── 录音处理流水线           │
└──────────┬──────────┬──────────┬────────┘
           │          │          │
     ┌─────┴──┐  ┌────┴───┐  ┌──┴──────────┐
     │ Android │  │  Web   │  │ Agent Skill │
     │  Apps   │  │ 前端   │  │ (CLI/API)   │
     └────────┘  └────────┘  └─────────────┘
     ExRecord     旧 Vue3      exmemo_backend
     ExReader     (过渡期)     等第三方脚本
     ExmemoApp
```

## 关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Web 框架 | FastAPI（弃 Django） | 异步友好、轻量、类型提示好 |
| 数据库 | 保留 PostgreSQL，与旧后端共用 | 零迁移风险 |
| ORM | SQLAlchemy 映射现有 `store_entry` 表 | 不改表结构，新旧共存 |
| 向量化 | 移除 | 使用率低，增加运维复杂度 |
| 文件存储 | **待定**（MinIO 或本地文件系统） | 见下方说明 |
| 迁移策略 | 绞杀者模式（Strangler Fig） | 新旧并存，逐步替换 |
| AI 模块部署 | 代码分模块，部署不分进程 | 见下方说明 |

## 文件存储方案（待定）

当前有两个候选方案，尚未最终确定：

**方案 A：MinIO / S3 对象存储**
- 优点：S3 兼容，可迁移到云存储；支持预签名 URL 直传大文件
- 代价：多一个运维组件；双写逻辑更复杂

**方案 B：本地文件系统**
- 优点：零额外依赖；文件可直接用编辑器打开；与 Obsidian 本地 vault 天然兼容
- 代价：备份靠自己；不支持预签名 URL

**两个方案共同的设计原则**：
- **文件是数据之源**：正文以 Markdown 文件形式持久存储，数据库只存索引和元数据
- **数据库可重建**：只要文件还在，扫描文件即可重建数据库索引
- **读取 fallback**：有 `path` 字段的从文件读，没有的从旧 `raw` 字段读

代码中通过 `dataforge/storage.py` 抽象存储接口，切换方案只需替换实现，不影响上层逻辑。

## AI 模块部署方式

`asr/`、`llm/`、`record/` 三个模块都是对 OpenAI API 的薄包装，没有自己的数据库依赖，代码层面已经各自独立。

**当前策略：代码分模块，部署不分进程。**

三个模块作为独立的 FastAPI router 挂载在同一个 ExmemoServer 进程里，不单独部署。理由：

- 总代码量约 200 行，拆出去多一个进程、一套 Docker 配置、一套健康检查，运维成本远大于收益
- 调用方当前只有 ExRecord，没有跨项目共享的需求
- 代码已经解耦，`asr/`、`llm/` 作为内部函数被 `record/` 复用，将来拆只需把函数调用改成 HTTP 调用

**何时值得拆成独立服务**：
- ASR 切换到本地模型（如 faster-whisper），需要独占 GPU 资源
- 其他项目也需要调用 ASR / LLM，有共享服务的需求
- 调用量大到需要独立扩缩容

## API 消费者

ExmemoServer 的 API 需要同时服务三类调用方：

### 1. Android 客户端（ExRecord / ExReader / ExmemoApp）
- 通过 `exmemo_android_sdk` 统一封装调用
- 使用 JWT 认证
- 核心场景：上传录音文本、上传书摘、浏览笔记

### 2. Web 前端
- 过渡期继续使用旧 Django 后端
- 切换时机：ExmemoServer CRUD 完全稳定后

### 3. Agent Skills（CLI / 脚本调用）
- 如 `exmemo_backend` skill，通过 HTTP API 直接操作数据
- 场景：搜索文档、下载文件、批量查询、数据导出
- **对 API 的要求**：
  - 接口路径和参数命名要稳定，skill 不应因后端重构而频繁改动
  - 列表接口必须有标准分页（`count` / `next` / `previous`）
  - 搜索参数兼容旧后端命名（`keyword` 而非 `search`）
  - 下载接口的 `Content-Disposition` 必须包含正确文件名（含扩展名）
  - 认证方式需文档化，skill 侧维护 session 文件自动续期

## 前端设计原则

- **多端独立**：ExRecord（录音）、ExReader（阅读）、ExmemoApp（浏览整理）各自独立，不糅合成超级 App
- **离线优先**：各 App 通过本地 Room 数据库独立工作，同步是增强而非前置条件
- **SDK 统一**：通过 `exmemo_android_sdk` 封装登录 + CRUD，避免各 App 重复实现

## 模块边界

**属于 ExmemoServer 的**：
- 数据 CRUD（dataforge）
- 语音识别（asr）
- 文本整理（llm）
- 录音处理流水线（record）
- 后续：Obsidian 同步、异步任务队列

**不属于 ExmemoServer 的**（旧后端的，直接废弃）：
- `app_diet` — 饮食记录
- `app_translate` — 翻译
- `app_paper` — 论文辅助
- `app_bm_keeper` — 网页书签抓取
- `app_bm_syncex` — 书签同步
- `app_message` — 消息/聊天
- `app_web` — Web 前端路由
