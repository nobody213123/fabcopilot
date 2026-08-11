# 安全边界

## 已实现

- `.env`、虚拟环境和日志目录被 Git 忽略；`.env.example` 仅含占位值。
- OpenAI 密钥由 `SecretStr` 接收，不写入响应或日志。
- HTTP 日志不记录请求正文，使用请求 ID 关联问题。
- NL2SQL 使用 AST 白名单、只读事务、行数与执行时间限制。
- 停机等高风险动作只创建待审批提案，Agent 无直接执行能力。
- Docker 应用以非 root 用户运行。
- Redis 使用密码；PostgreSQL 与 Redis 的容器密码来自本机环境变量。

## 当前限制

- 尚未实现用户登录、RBAC、租户隔离、TLS 与密钥管理服务。
- Compose 为本地开发配置，数据库端口会暴露到 localhost。
- 离线 hashing embedding 不是生产语义模型。
- 审批目前只有状态机，没有对接企业 IAM、工单或通知系统。
- Prometheus 指标端点尚未鉴权，生产部署应限制在内部网络。

因此项目适合作为可验证的工程原型，不能直接接入生产设备控制网络。
