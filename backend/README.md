# GamesClub API

第三阶段：先配置 backend/.env 的 DATABASE_URL（PostgreSQL），显式启用本地 ALLOW_DEV_LOGIN/ALLOW_MOCK_PAYMENT；运行步骤与验收边界见根目录《第三阶段完成度与联调手册.md》。未配置数据库会报错，不再静默使用 SQLite。现有数据库更新只执行 migration，勿运行重置数据操作。独立 Web 在 apps/admin，Django Admin 目录和订单改为只读。

开发运行：

```powershell
python -m pip install -r requirements.txt
docker compose up -d db
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

开发登录：`POST /api/v1/auth/dev-login/`。开发登录仅在 `DEBUG=1` 时可用。商品公开接口不需要登录；收藏、订单和模拟付款需要 `Authorization: Bearer <access_token>`。创建订单和模拟付款必须带唯一 `Idempotency-Key`。
