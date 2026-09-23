# Docker 重装后的 PostgreSQL 检查记录

日期：2026-09-23。

## 现象与处理

- 沙箱访问 Docker 管道出现 permission denied；授权后读取正常，不将沙箱限制误判为引擎故障。
- Docker Engine 正常，检查时没有容器或数据卷。创建项目 postgres:17 容器 backend-db-1，数据卷 backend_gamesclub_pgdata。
- 新库执行全部迁移至 core.0005；seed_demo仅补演示目录，不覆盖旧商品。旧backend/dev.sqlite3未改动；未迁移旧账号、订单。
- 本地backend/.env配置数据库、DEBUG及开发登录/模拟付款开关，文件已被Git忽略。

## 验证证据

- PostgreSQL执行manage.py check通过；migrate --plan无待迁移。
- manage.py test：12项全部通过，无跳过。
- core.test_concurrency单独重跑：相同幂等键并发下单、不同键并发付款均通过。
- 实际开发库检查：4游戏、12类型、5商品、0首页配置、0订单；测试在独立test_gamesclub数据库运行，不留下业务测试订单。

## 注意事项

- 新库不包含旧SQLite管理员，使用createsuperuser自行设置；首页配置为空，需要在Web设置。
- 不执行docker compose down -v或删除数据卷来解决普通连接问题。
- 数据卷存在不是备份；备份恢复演练尚未完成。
- 不能因未找到旧卷断言旧数据完全无法恢复，应检查外部备份。
- 此记录不代表真机、完整浏览器验收或所有并发场景均通过。
