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

### doc/ 目录 - 项目文档
| 文件名 | 作用描述 |
|--------|----------|
| `architecture.md` | 系统架构设计文档，描述整体架构和设计理念 |
| `core_refactoring.md` | 核心模块重构设计文档，说明从 Django 迁移到 FastAPI 的策略 |
| `project_structure.md` | 项目文件结构说明文档（本文档） |

## API 端点总览

### 核心业务接口
- `POST /api/entry/data` - 笔记数据上传接口，接收 ExRecord 传来的文本并存储
- `GET /health` - 服务健康检查接口

### ASR 语音识别接口
- `POST /asr/transcribe` - 语音转文本接口，支持多种音频格式

### LLM 文本处理接口  
- `POST /llm/organize` - 文本整理接口，清理语音识别的原始文本

### 录音处理接口
- `POST /record/process` - 录音一体化处理接口，从音频直接生成标题和整理后内容

## 技术栈
- **Web 框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy ORM  
- **向量存储**: pgvector 扩展
- **AI 服务**: OpenAI API (Whisper + GPT)
- **容器化**: Docker + Docker Compose

## 数据流转
1. ExRecord 应用录制语音 → ASR 模块转文本 → LLM 整理 → 存储到 PostgreSQL
2. 支持直接文本上传和语音文件上传两种数据输入方式
3. 所有数据最终统一存储在 store_entry 表中，便于跨平台同步和检索

## 设计原则
- **核心聚焦**: 专注知识管理相关的存储、输入输出、关联思考功能
- **模块解耦**: ASR、LLM、存储等功能模块独立设计，便于扩展维护  
- **数据统一**: 采用统一的数据模型，避免数据孤岛问题
- **平滑迁移**: 保持与现有 Django 系统的数据兼容性，实现无缝过渡