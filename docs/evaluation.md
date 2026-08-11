# 评测方法与实测结果

评测日期：2026-08-11。环境：Windows 11、WSL 2 Docker Desktop、Python 3.13.7、PostgreSQL 17.10、pgvector 0.8.2、Redis 7.2.15。数据为合成数据。

## 自动化测试

```powershell
python -m pytest -q
python -m pytest -m integration -q
```

- 非集成测试：52 passed。
- 真实基础设施集成测试：11 passed。
- 集成测试覆盖真实 PostgreSQL、pgvector、Redis、API 跨请求持久化、混合检索、只读 NL2SQL、Agent 审批状态机和演示数据幂等性。
- `alembic check`：无新的迁移操作。
- `pip check`：无依赖冲突。

## Agent 路由与审批安全

```powershell
python -m fabcopilot.evaluation.agent_routing
```

固定离线集包含 6 个扩散炉问题，其中 3 个要求高风险审批。结果：

| 指标 | 结果 |
|---|---:|
| 精确工具路由 | 6/6（100%） |
| 是否要求审批 | 6/6（100%） |

这是规则模型在小型固定集上的回归结果，只能证明当前基线没有退化，不能代表开放问题准确率。当前环境没有配置真实 OpenAI API 密钥，因此没有虚构模型在线评测结果。

## HTTP 基准

容器内运行单个 Uvicorn worker，宿主机顺序发送 200 个请求，无并发压测：

```powershell
python scripts/benchmark_api.py --url http://127.0.0.1:8000/health --requests 200
python scripts/benchmark_api.py --url http://127.0.0.1:8000/ready --requests 200
```

| 端点 | 吞吐（req/s） | p50 | p95 | max |
|---|---:|---:|---:|---:|
| `/health` | 372.05 | 1.500 ms | 2.004 ms | 15.416 ms |
| `/ready` | 281.59 | 2.379 ms | 3.224 ms | 6.741 ms |

`/ready` 每次都访问 PostgreSQL 与 Redis。结果受机器、Docker、后台负载和顺序请求方式影响，不应作为生产 SLA。后续应增加并发负载、RAG/NL2SQL/Agent 端到端延迟和真实模型质量评测。
