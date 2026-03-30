# ExmemoServer 项目文件结构说明

## 项目概述
ExmemoServer 是基于 FastAPI 的知识管理系统后端服务，负责处理语音记录、文本整理和数据存储等核心功能。

## 根目录文件

| 文件名 | 作用描述 |
|--------|----------|
| `main.py` | FastAPI 应用入口文件，定义路由和健康检查接口 |
| `database.py` | 数据库连接配置文件，管理 PostgreSQL 连接和会话 |
| `models.py` | SQLAlchemy 数据模型定义，映射 store_entry 表结构 |
| `requirements.txt` | Python 依赖包清单文件 |
| `Dockerfile` | Docker 镜像构建配置文件 |
| `docker-compose.yml` | Docker 容器编排配置文件 |
| `env_default` | 默认环境变量配置文件模板 |
| `README.md` | 项目说明文档 |

## 核心功能模块

### asr/ 目录 - 自动语音识别模块
| 文件名 | 作用描述 |
|--------|----------|
| `__init__.py` | Python 包初始化文件 |
| `transcribe.py` | 语音转文本服务，调用 OpenAI Whisper API 识别音频内容 |

### llm/ 目录 - 大语言模型处理模块
| 文件名 | 作用描述 |
|--------|----------|
| `__init__.py` | Python 包初始化文件 |
| `organize.py` | 文本整理服务，使用 LLM 清理和格式化语音识别结果 |

### record/ 目录 - 录音处理模块
| 文件名 | 作用描述 |
|--------|----------|
| `__init__.py` | Python 包初始化文件 |
| `process.py` | 录音处理一体化服务，串联 ASR 和 LLM 提供完整的语音到文本转换 |

### dataforge/ 目录 - 数据存储模块
| 文件名 | 作用描述 |
|--------|----------|
| `__init__.py` | Python 包初始化文件 |
| `router.py` | 数据 CRUD 路由，提供笔记的增删改查和下载接口 |
| `crud.py` | 数据库操作层，封装 SQLAlchemy 查询逻辑 |
| `storage.py` | 文件存储抽象层，封装文件的上传/下载/删除 |

### doc/ 目录 - 项目文档
| 文件名 | 作用描述 |
|--------|----------|
| `architecture.md` | 架构设计：定位、技术决策、模块边界、API 消费者 |
| `compatibility.md` | 过渡期数据兼容方案（双写机制） |
| `todo.md` | 分阶段待办事项 |
| `project_structure.md` | 项目文件结构说明（本文档） |

## API 端点总览

### 核心业务接口
- `POST /api/entry/data` - 笔记数据上传接口，接收 ExRecord 传来的文本并存储
- `GET /health` - 服务健康检查接口

### ASR 语音识别接口
- `POST /asr/transcribe` - 语音转文本接口，支持多种音频格式

### LLM 文本处理接口  
- `POST /llm/complete` - 通用 LLM 接口，客户端传入 system/user prompt，返回文本结果

### 录音处理接口
- `POST /record/process` - 录音一体化处理接口，从音频直接生成标题和整理后内容

## 技术栈
- **Web 框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy ORM
- **AI 服务**: OpenAI API (Whisper + GPT)
- **容器化**: Docker + Docker Compose
- **文件存储**: 待定（MinIO 或本地文件系统），通过 `storage.py` 抽象

## 数据流转
1. ExRecord 应用录制语音 → ASR 模块转文本 → LLM 整理 → 存储到 PostgreSQL
2. 支持直接文本上传和语音文件上传两种数据输入方式
3. 所有数据最终统一存储在 store_entry 表中，便于跨平台同步和检索

## 设计原则
- **核心聚焦**: 只做知识管理相关的存储、输入输出、AI 辅助整理
- **模块解耦**: ASR、LLM、存储功能独立，便于单独维护
- **数据统一**: 统一数据模型，所有前端和 Agent Skill 共享同一套 API
- **平滑迁移**: 保持与旧 Django 系统的数据兼容性（见 `compatibility.md`）