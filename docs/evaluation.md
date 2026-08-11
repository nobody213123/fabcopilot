# 评测方法与实测结果

评测日期：2026-08-12。环境：Windows 11、WSL 2 Docker Desktop、Python 3.13.7、PostgreSQL 17.10、pgvector 0.8.2、Redis 7.2.15。数据为合成数据。

## 自动化测试

```powershell
python -m pytest -q
python -m pytest -m integration -q
```

- 非集成测试：66 passed。
- 真实基础设施集成测试：11 passed。
- 集成测试覆盖真实 PostgreSQL、pgvector、Redis、API 跨请求持久化、混合检索、只读 NL2SQL、Agent 审批状态机和演示数据幂等性。
- `alembic check`：无新的迁移操作。
- `pip check`：无依赖冲突。

## 多语言混合检索

```powershell
python -m fabcopilot.evaluation.retrieval --provider hashing
python -m fabcopilot.evaluation.retrieval --provider fastembed
```

固定评测集包含 15 篇合成扩散炉维护文档和 60 条人工编写的中英查询。每次评测在事务中清空知识表、写入隔离语料并在结束时回滚，避免本地演示文档污染指标。

| 检索方式 | Top-1 Recall | Top-3 Recall | Top-5 Recall | MRR | p95 查询延迟 |
|---|---:|---:|---:|---:|---:|
| pg_trgm/FTS lexical | 78.3% | 85.0% | 86.7% | 0.821 | 4.012 ms |
| Hashing vector | 90.0% | 98.3% | 98.3% | 0.939 | 2.266 ms |
| Hashing hybrid RRF | 86.7% | 100.0% | 100.0% | 0.928 | 6.651 ms |
| Multilingual MiniLM vector | 86.7% | 98.3% | 98.3% | 0.914 | 47.608 ms |
| Multilingual MiniLM hybrid RRF | **91.7%** | 98.3% | 98.3% | **0.947** | 54.320 ms |

真实多语言模型提升了混合检索的 Top-1 与 MRR，但并未在每个 K 上都超过 hashing 基线，而且增加约 48 ms p95 查询时间。5 个 Top-1 失败样例由评测脚本直接输出，主要涉及温区输出与温度均匀性、管路泄漏与炉管裂纹、装片位置与滑片等相邻概念，说明下一步应增加领域同义词、困难负样本与 reranker，而不是宣称检索已经解决。

该评测集规模小、由项目作者构造且全部为合成内容，只用于比较同仓库版本和防止回归，不能外推为真实晶圆厂召回率。

## SQL 安全攻击集

```powershell
python -m fabcopilot.evaluation.sql_safety
```

23 条固定用例包含 8 条合法分析 SQL 与 15 条 DML/DDL、系统表、文件读取、资源消耗函数和 LIMIT 绕过攻击。当前结果：合法查询接受率 8/8，危险查询拒绝率 15/15。函数策略由危险函数拒绝列表改为分析函数允许列表，降低遗漏新危险函数的风险。固定集合上的 100% 只表示已知回归集通过，不代表能够替代数据库最小权限与安全审计。

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

容器内运行单个 Uvicorn worker。健康接口仍使用宿主机顺序 200 请求；诊断接口另使用并发压测脚本：

```powershell
python scripts/benchmark_api.py --url http://127.0.0.1:8000/health --requests 200
python scripts/benchmark_api.py --url http://127.0.0.1:8000/ready --requests 200
python scripts/benchmark_agent.py --requests 50 --concurrency 10
```

| 端点 | 吞吐（req/s） | p50 | p95 | max |
|---|---:|---:|---:|---:|
| `/health`（200 次顺序请求） | 310.89 | 1.760 ms | 2.595 ms | 8.790 ms |
| `/ready`（200 次顺序请求） | 230.23 | 3.120 ms | 4.183 ms | 8.900 ms |
| `/agent/diagnose`（50 次，并发 10） | 56.10 | 173.740 ms | 207.185 ms | 214.462 ms |

Agent 压测成功 50/50、失败 0 次，且每个响应都通过结构化证据断言。`/ready` 每次都访问 PostgreSQL 与 Redis。FastEmbed 首次请求会下载约 241 MiB 模型缓存；本机弱网络下首次预热超过 240 秒，下载完成后模型文件保存在非 root 可写的 Docker volume，以上诊断指标只统计热态请求。结果受机器、Docker、后台负载和合成数据规模影响，不应作为生产 SLA。
