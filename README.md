# ExmemoServer

## 简介

ExmemoServer 是 Exmemo 生态的共用后端服务，基于 FastAPI 构建。目前提供语音识别（ASR）和文本整理（LLM）两个模块，供 ExRecord 等 App 通过 HTTP 接口调用。底层模型可随时在配置中切换，无需修改 App 端代码。

## 主要功能

- **语音识别**：接收音频文件，调用 OpenAI Whisper API 进行语音转文字
- **文本整理**：将识别出的原始文字交给 LLM 润色整理，自动提炼标题和正文
- **健康检查**：`/health` 接口，方便监控服务状态
- **可扩展架构**：`asr/`、`llm/` 各模块独立，后续可按需新增功能模块
- **Docker 化部署**：支持 production / development 两种模式，开发模式支持热重载

## 接口说明

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查，返回 `{"status": "ok"}` |
| POST | `/asr/transcribe` | 上传音频文件，返回识别文字 |
| POST | `/llm/organize` | 传入原始文字，返回整理后的标题和正文 |
| POST | `/record/process` | **主接口**：上传音频，内部串联 ASR→LLM，一次返回全部结果 |

### POST /record/process（推荐）

- 请求：`multipart/form-data`，字段名 `file`，支持 m4a、mp3、wav、webm、ogg 等格式
- 返回：`{"text": "原始识别文字", "title": "标题", "content": "整理后的正文"}`
- 服务端内部串联 ASR → LLM，客户端一次调用即可，底层模型或 prompt 变更无需改动客户端

### POST /asr/transcribe

- 请求：`multipart/form-data`，字段名 `file`，支持 m4a、mp3、wav、webm、ogg 等格式
- 返回：`{"text": "识别出的文字"}`

### POST /llm/organize

- 请求：`{"text": "原始识别文字"}`
- 返回：`{"title": "标题", "content": "整理后的正文"}`

## 快速开始

### 1. 准备配置文件

```bash
cd ExmemoServer
cp env_default .env
```

编辑 `.env`，至少填写 `OPENAI_API_KEY`：

```
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. 启动服务

**开发模式**（代码修改后自动热重载，推荐本地调试使用）：

```bash
docker-compose --profile development up
```

**生产模式**（使用预构建镜像，稳定运行）：

```bash
docker-compose --profile production up -d
```

服务启动后默认监听 `http://localhost:8100`。

### 3. 验证服务

```bash
curl http://localhost:8100/health
```

返回 `{"status":"ok"}` 表示服务正常。

也可以打开 `http://localhost:8100/docs` 使用 FastAPI 自带的交互式文档页面测试所有接口。

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API Key（必填） | — |
| `OPENAI_BASE_URL` | 自定义 API 地址，使用代理时填写 | 留空使用官方地址 |
| `ASR_MODEL` | Whisper 模型名 | `whisper-1` |
| `LLM_MODEL` | 文本整理模型名 | `gpt-4o-mini` |
| `SERVER_PORT` | 服务监听端口 | `8100` |
| `HTTP_PROXY` | HTTP 代理（可选） | 留空 |

## 安装（不使用 Docker）

```bash
pip install -r requirements.txt
cp env_default .env  # 填写配置
uvicorn main:app --host 0.0.0.0 --port 8100 --reload
```

## 系统要求

- Docker + Docker Compose，或 Python 3.11+
- 网络可访问 OpenAI API（或配置代理 / 自定义 base URL）

## TODO

- [ ] **鉴权**：为接口加 `Authorization: Bearer <token>` 验证，token 在 `.env` 中配置
- [ ] **与 exmemo 主项目合并**：作为 exmemo 的一个子服务纳入其 `docker-compose.yml`

## 注意

- 在一些临时代码中注释：“先写死”