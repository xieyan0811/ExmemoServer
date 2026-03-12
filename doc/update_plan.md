# Exmemo 生态重构与演进计划

## 背景

当前 Exmemo 生态由以下项目组成：

- **exmemo**：旧主项目，Django 后端 + Vue3 前端，功能完整但耦合度高
- **ExmemoServer**：新 FastAPI 后端，目标是逐步接管 exmemo 后端的核心数据服务
- **ExmemoApp**：Android 客户端，功能待定
- **ExReader**：Android 阅读器，支持 EPUB/MD/TXT，含 TTS 和书摘
- **ExRecord**：Android 录音笔记，录音 → ASR → LLM 整理 → 同步

---

## 一、ExmemoServer 的演进策略

### 总体方向

采用**绞杀者架构（Strangler Fig Pattern）**，ExmemoServer 逐步接管 exmemo 旧后端，而不是一次性重写。

exmemo 旧后端在整个迁移期间保持运行，Web 前端、Obsidian 插件、微信机器人继续使用旧后端，直到 ExmemoServer 功能完备后再统一切换。

### 阶段一（当前优先级最高）：数据 CRUD + 文件存储稳定

目标：ExmemoServer 的 `/api/entry/data` CRUD 能完整替代 exmemo 后端的 `app_dataforge` 功能。

- 完善 dataforge 模块的增删改查接口
- MinIO 文件存储作为主存储，PostgreSQL 降级为索引库
- 按 `data_storage_compatibility.md` 的双写兼容方案，保证旧后端数据可读
- **不引入 pgvector 依赖**（在 ExmemoServer 侧放弃向量化功能）

### 阶段二：ASR / LLM 接口稳定

- ExmemoServer 已有 `asr/`、`llm/`、`record/` 模块，ExRecord 已在使用
- 此阶段重点是接口契约稳定（版本化），不做大改
- exmemo 旧后端的 ASR/LLM 功能保持不动，不迁移

### 阶段三：暂缓事项

以下内容推迟到阶段一完成后再评估：

- `app_sync`（Obsidian 双向同步引擎）的迁移
- 异步任务队列（Celery/RQ）的迁移
- Web 前端切换到 ExmemoServer

### 技术决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| Web 框架 | FastAPI（弃 Django） | 异步、轻量、类型友好 |
| 文件存储 | MinIO（弃本地存储） | 可扩展，S3 兼容 |
| 向量化 | 移除 | 使用率低，增加运维复杂度 |
| 数据库 | 保留 PostgreSQL | 零迁移，与旧后端共用同一实例 |

---

## 二、Android 同步 SDK（exmemo-sync-sdk）

### 问题背景

ExReader 需要上传书摘，ExRecord 需要上传录音文本，如果各自维护一套 ExmemoServer 的 client 代码，会造成重复和不一致。

用 Intent 调 ExmemoApp 中转的方案被否决：用户体验差，且引入对 ExmemoApp 安装状态的硬依赖，违背"离线优先"原则。

### 方案：共享 Android Library Module

创建独立仓库 `exmemo-sync-sdk`，作为 Android Library，被 ExReader、ExRecord、ExmemoApp 共同依赖。

**SDK 职责（只做这三件事）：**

1. **配置管理**：服务器地址、连接超时等
2. **认证**：提供开箱即用的 `LoginActivity`（用户名/密码 → JWT Token），Token 用 `EncryptedSharedPreferences` 安全存储，自动刷新
3. **数据接口**：封装 ExmemoServer `/api/entry/data` 的 CRUD 操作（上传条目、查询条目、更新/删除）

**SDK 不做的事：**

- 注册界面（引导用户去 Web 端注册）
- 文件管理 / 网盘 UI
- 特定业务逻辑（录音、阅读等）

**SDK 模块文件结构**

搬自 ExmemoApp 的现有代码（基本不需要改动）：

- `storage/TokenStore.kt` — 加密凭据存储（Token + 服务器配置）
- `network/BackendAdapter.kt` — 统一接口 + DataEntry/TreeNode 数据模型
- `network/AdapterFactory.kt` — 适配器工厂单例（init/set/get）
- `network/AuthApi.kt` / `NotesApi.kt` — 业务门面（静态方法，委托给 AdapterFactory）
- `network/ExmemoServerAdapter.kt` — 新版 FastAPI 适配器（需补完 tree/entry/update 三个方法）
- `network/LegacyAdapter.kt` — 旧版 Django REST 兼容层
- `ui/LoginScreen.kt` — 登录界面（含后端类型切换 + 服务器地址配置 + 用户名/密码输入）

ExmemoApp 完成迁移后只保留业务 UI（FileTreeScreen、MarkdownEditorScreen、MainActivity）。

**集成方式（当前阶段推荐方案）**

两种选择：

1. **Git Submodule**（规范方案，适合后续多人协作）：
```bash
git submodule add https://github.com/yourname/exmemo-sync-sdk.git exmemo-sync-sdk
```
每个项目（ExReader/ExRecord/ExmemoApp）各自 clone 一份。

2. **绝对路径引用**（快速迭代方案，适合当前单机开发）：
在各项目的 `settings.gradle.kts` 中：
```kotlin
include(":exmemo-sync-sdk")
project(":exmemo-sync-sdk").projectDir = File("/exports/exmemo/code/exmemo-sync-sdk")
```
只维护磁盘上的一份 SDK，三个项目同时指向，改一次立刻生效。换机器时需改绝对路径。

建议现阶段用方案 2，待稳定后迁至方案 1。后续若需开放给他人使用，再迁移到 Maven Central 发布。

### 前置条件

SDK 依赖 ExmemoServer 阶段一完成（CRUD API 稳定），因此 SDK 开发排在阶段一之后。

---

## 三、ExmemoApp 的定位

### 定位：数据浏览器 + 轻量整理工具

ExmemoApp **不是**网盘客户端，**不是**文件管理器（MinIO 是实现细节，不应暴露给用户）。

**要做的功能：**

- **浏览与检索**：按时间/类型/标签浏览所有 ExmemoServer 条目（笔记、书摘、录音记录、网页剪藏），支持全文搜索
- **轻量编辑**：支持对文本/Markdown 条目的标题、正文、标签的简单编辑
- **快速捕获**：接收系统 Share Intent，把文字/链接/图片快速存入 ExmemoServer（这是 ExmemoApp 相对 ExReader/ExRecord 的独特价值）

**不做的功能：**

- 富文本/Markdown 编辑器（深度编辑交给电脑端 Obsidian）
- 阅读器（有 ExReader）
- 录音（有 ExRecord）
- 文件树/网盘界面

---

## 四、优先级总结

```
阶段一（现在）：ExmemoServer 数据 CRUD + MinIO 存储稳定
      ↓
阶段二：exmemo-sync-sdk 开发（登录 + CRUD 封装）
      ↓
阶段三：ExReader / ExRecord 接入 SDK，移除各自的独立 client 代码
      ↓
阶段四：ExmemoApp 功能完善（浏览、搜索、Share Intent 捕获）
      ↓
长期：Web 前端切换到 ExmemoServer，旧 Django 后端退役
```