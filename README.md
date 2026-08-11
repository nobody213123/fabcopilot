# FabCopilot

FabCopilot 是一个面向芯片制造场景的良率诊断与维护协同智能体。项目首先聚焦扩散炉与热处理设备，逐步建设可检索、可调用工具、可人工审批、可评测和可观测的 AI Agent 服务。

## 项目目标

- 将设备告警、工艺上下文、维护知识与良率信息组织为可追溯的诊断依据。
- 为工程师生成诊断假设、证据和下一步检查建议，而不是替代工程师做高风险决策。
- 以真实测试结果记录正确率、延迟和稳定性等指标，不使用虚构的简历数据。

## 当前范围

当前已完成 Python 项目骨架、扩散炉设备领域模型、应用服务与 Repository 分层，以及带自动化测试的设备创建和按编号查询 API。接口能够返回 `201 Created`、`404 Not Found`、`409 Conflict` 和 `422 Unprocessable Entity` 等明确结果。

本地 PostgreSQL 17 + pgvector 0.8.2 容器环境已经建立；Python 数据访问适配器尚未实现，应用当前仍使用内存 Repository。RAG 和 Agent 功能将在数据层稳定后逐步加入。

首个业务范围是扩散炉/热处理设备，后续再扩展其他工艺模块。

## 目录结构

```text
fabcopilot/
├── src/
│   └── fabcopilot/
│       ├── api/             # FastAPI 应用入口、Schema 与 HTTP 路由
│       ├── application/     # 应用服务与 Repository 端口
│       ├── domain/          # 与框架无关的核心业务模型与规则
│       └── infrastructure/  # Repository 等基础设施实现
├── tests/                # 自动化测试
├── docker/postgres/init/ # PostgreSQL 首次启动初始化 SQL
├── .env.example          # 可提交的环境变量示例，不存放真实密钥
├── .gitignore            # Git 忽略规则
├── compose.yaml          # PostgreSQL/pgvector 本地容器
├── pyproject.toml        # Python 项目、依赖与工具配置
└── README.md             # 项目说明与开发入口
```

只提前建立当前阶段需要的目录。数据库、RAG、Agent 等目录将在对应能力开始实现时再创建。

## 本地开发

前置条件：Python 3.11 或更高版本。数据库开发还需要启用 WSL 2 的 Docker Desktop。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
python -m pytest
uvicorn fabcopilot.api.app:app --host 127.0.0.1 --port 8000
```

目前运行时依赖为 FastAPI 与 Uvicorn；开发依赖为 pytest、Ruff 和 HTTPX2。不要提交 `.env`、虚拟环境或任何真实凭据。

## 本地数据库

第一次启动前，从模板创建仅供本机使用的 `.env`，并修改其中的开发密码：

```powershell
Copy-Item .env.example .env
docker compose up -d
docker compose ps
```

`postgres` 服务显示 `healthy` 后，可以验证 pgvector 扩展：

```powershell
docker compose exec postgres psql -U fabcopilot -d fabcopilot -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
```

停止本地数据库但保留数据：

```powershell
docker compose stop
```

## 迭代原则

每个阶段遵循“概念讲解 → 小测 → 自己编写 → 运行测试 → 代码复盘”，并且只交付一个可验证的小增量。
