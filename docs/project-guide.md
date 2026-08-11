# FabCopilot 项目设计学习指南

这份文档用于从零理解项目，也用于秋招面试前复习。建议先跑通一次请求，再按文末顺序阅读代码。

## 1. 项目要解决什么问题

扩散炉异常诊断需要同时查看设备、批次良率、报警和维修手册。FabCopilot 把这些信息组织为可审计证据，让 Agent 负责选择工具和综合证据，而不是让模型直接控制设备。

核心安全原则：

1. 数据查询只读。
2. 模型输出不是执行凭证。
3. 停机、调配方等高风险动作只生成待审批单。
4. 回答必须能追溯到知识文档或 SQL 结果。
5. 没有证据时明确返回证据缺口。

## 2. 分层与依赖方向

```text
api -> application -> domain
             ^
             |
      infrastructure
```

- `domain`：设备、批次、报警、审批和 Agent 结果等业务对象，不依赖 FastAPI、SQLAlchemy 或模型 SDK。
- `application`：实现用例，声明 Repository、Embedding、AgentModel、Cache 等端口。
- `infrastructure`：使用 PostgreSQL、pgvector、Redis、FastEmbed、OpenAI 和 SQLGlot 实现端口。
- `api`：完成 HTTP 校验、依赖注入和异常到状态码的转换。

这样设计的直接收益是：CI 可以使用哈希 embedding、规则模型和假 Repository 快速测试，部署时再换成真实本地 embedding、PostgreSQL 和外部模型。

## 3. 一次诊断请求如何执行

`POST /agent/diagnose` 的执行顺序：

1. API Key 依赖检查可选的共享密钥。
2. `CachedDiagnosticAgentService` 读取 Redis。缓存键包含 Prompt 摘要、模型配置和知识库版本。
3. 缓存未命中后，`DiagnosticAgentService` 调用 AgentModel。
4. AgentModel 请求 `search_knowledge`、`query_analytics`，必要时请求 `propose_maintenance_action`。
5. `FabAgentToolRegistry` 再次校验工具参数，并调用对应 Application Service。
6. 工具结果返回模型生成最终回答。
7. Application Service 从工具轨迹提取结构化 `evidence` 和 `missing_evidence`。
8. 含待审批 ID 的结果不缓存；普通结果按 TTL 缓存。

工具轨迹被完整返回是为了调试与审计，但生产环境还应按角色隐藏敏感字段。

## 4. 混合检索为什么这样设计

### 4.1 两路召回

关键词召回结合两种 PostgreSQL 信号：

- `TSVECTOR`：适合英文单词、型号和报警码。
- `pg_trgm`：不依赖中文分词，适合中文短语、近似字符串和设备编码。

语义召回使用 pgvector 余弦距离：

- CI 默认使用确定性 hashing embedding，避免下载和网络依赖。
- 投递版可使用 FastEmbed 的多语言 ONNX 模型，本地运行且无需 API Key。

数据库历史向量列为 1536 维，而本地模型输出 384 维。适配器在末尾补零；补零不会改变向量点积和余弦相似度，但会浪费存储。生产迁移应建立新的 384 维列、双写、回填并切换索引，而不是长期补零。

### 4.2 RRF 融合

全文分数和余弦距离的量纲不同，直接加权容易受分布影响。项目使用 Reciprocal Rank Fusion：

```text
score(d) = 1 / (k + lexical_rank) + 1 / (k + vector_rank)
```

它只依赖排名，工程上稳定、易解释。缺点是不能利用原始分数置信度，并且相邻文档的细粒度差别较弱。评测中的 Top-1 失败样例正是未来增加 reranker 的依据。

## 5. NL2SQL 的纵深防护

SQL 生成与 SQL 执行被刻意分开：即使生成器被 Prompt Injection 影响，执行边界仍然生效。

执行前：

- SQLGlot 解析 AST；
- 只允许单条 Query；
- 只允许三张业务表和 `public` schema；
- 禁止 `SELECT *`；
- 函数使用允许列表，而不是容易漏项的危险函数拒绝列表；
- 自动追加或收紧 LIMIT。

执行时：

- PostgreSQL 事务设置为 READ ONLY；
- statement timeout 为 3 秒；
- 最多读取 200 行。

当前无密钥模式的 SQL 生成器仍是规则基线。项目真正有说服力的部分是安全执行边界；如要投递更偏算法的 Text2SQL 岗，需要补模型生成、Schema Linking 和执行准确率评测。

## 6. Agent 与 Human-in-the-loop

Agent 只看到三个能力明确的工具：知识检索、只读分析、高风险提案。工具参数既有 JSON Schema，也在应用代码中再次校验。

审批状态只能从 `pending` 变为 `approved` 或 `rejected`。数据库 Repository 使用带 `status = pending` 条件的原子 UPDATE，避免两个审批人并发操作时发生最后写入覆盖。

审批通过目前仍不执行设备动作。这是有意的信任边界：求职项目不应该伪装成已经接入真实控制网络。

## 7. 缓存一致性

缓存结果不能只按 Prompt 建键，否则知识更新后会继续返回旧诊断。当前缓存键包含：

```text
模型版本 + embedding provider/model + knowledge version + normalized prompt hash
```

知识写入成功后 Redis 中的 knowledge version 自增，旧缓存自然失效。含审批 ID 的结果从不缓存，因为审批 ID 是有生命周期的业务状态。

## 8. 安全边界

- 可选 `X-API-Key` 保护写入、诊断和审批接口。
- 密钥使用 `SecretStr`，日志不记录请求正文。
- SQL 只读和函数允许列表。
- 高风险动作必须审批。
- Docker 使用非 root 用户。
- FastEmbed 模型缓存使用非 root 可写的独立 volume。

共享 API Key 只适合个人作品部署。企业场景仍需要 IAM、RBAC、租户隔离、文档级 ACL、TLS 和审计主体。

## 9. 如何理解评测

项目包含三类离线评测：

1. 检索评测：15 篇合成文档、60 条中英查询，对比 lexical、vector 和 hybrid 的 Recall@K、MRR、延迟与失败样例。
2. SQL 安全评测：安全查询接受率、攻击查询拒绝率。
3. Agent 路由评测：工具选择和高风险审批判断的回归集。

检索数据规模仍小，且属于合成数据；指标用于证明改造方向和防止回归，不能外推为晶圆厂生产准确率。面试时应主动说明这个限制。

## 10. 推荐代码阅读顺序

1. `domain/equipment.py`、`domain/agent.py`、`domain/approval.py`。
2. `application/ports`，理解依赖倒置。
3. `application/services/diagnostic_agent.py`，理解 Agent 循环。
4. `infrastructure/agent_tools.py` 与 `agent_models.py`。
5. `infrastructure/repositories/sqlalchemy_knowledge_repository.py`，手算一次 RRF。
6. `infrastructure/nl2sql.py`，尝试设计绕过用例。
7. `api/dependencies.py`，理解对象如何被组装。
8. `evaluation/retrieval.py` 和评测集，理解每个数字怎么得到。
9. 迁移、Compose、Dockerfile 和 CI，理解代码如何成为服务。

## 11. 面试必须能回答的问题

- 为什么中文检索不能只使用 PostgreSQL `simple` 全文配置？
- 为什么选择 RRF，而不是把全文分数和余弦分数直接相加？
- 为什么 384 维向量补零到 1536 维不改变余弦相似度？长期方案是什么？
- 检索 Top-1 错了但 Top-3 对了，应该优化 embedding、知识内容还是 reranker？
- 为什么 SQL 危险函数拒绝列表不如允许列表安全？
- 为什么只读事务仍然需要 statement timeout？
- 两个人同时审批时，普通“先查再写”为什么会产生竞态？
- 为什么带审批 ID 的结果不能缓存？
- 知识库更新后，怎样避免缓存陈旧？
- 当前指标为什么不能代表真实生产效果？下一步怎样建立授权数据评测集？

能够独立画出请求时序、解释上述取舍、复现指标并分析失败样例，才算真正掌握这个项目。
