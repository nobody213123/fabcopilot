# 运行与排障手册

## 日常命令

```powershell
docker compose up -d app
docker compose ps
docker compose logs --tail 100 app
docker compose stop
```

`stop` 保留数据卷；除非明确要清空演示数据，不要执行带 `-v` 的删除操作。

## 健康检查

- `/health` 只证明进程能响应，适合作为 liveness。
- `/ready` 同时执行 PostgreSQL `SELECT 1` 和 Redis `PING`；任一失败返回 503。
- `/metrics` 输出 Prometheus 格式的请求数、延迟直方图与缓存操作计数。

## 常见问题

### Docker Desktop 显示未检测到虚拟化

确认 BIOS 虚拟化已启用，Windows 功能包含 WSL 2 与 Virtual Machine Platform，重启后运行 `wsl --status`。

### 迁移失败

```powershell
docker compose logs migrate
.\.venv\Scripts\alembic.exe current
.\.venv\Scripts\alembic.exe upgrade head
```

### `/ready` 返回 503

先看 `docker compose ps`。PostgreSQL 与 Redis 必须是 `healthy`；然后核对 `.env` 中连接串和 Compose 内部主机名。宿主机连接使用 `localhost`，容器内连接使用服务名 `postgres`/`redis`。

### IDE import 标红但测试通过

在 PyCharm/VS Code 中选择项目的 `.venv` 解释器。项目采用 `src` 布局，并以 editable 模式安装：`python -m pip install -e ".[dev]"`。

### Docker Hub 返回 EOF

通常是临时网络或代理问题，可稍后重试 `docker compose pull`。不要因为拉取失败改动业务代码。

## 数据备份

本地演示数据位于 Docker volume。正式环境应使用托管备份、恢复演练和迁移前快照；本仓库不把 volume 内容提交到 Git。
