# GamesClub API

开发运行：

```powershell
python -m pip install -r requirements.txt
docker compose up -d db
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

开发登录：`POST /api/v1/auth/dev-login/`。开发登录仅在 `DEBUG=1` 时可用。商品公开接口不需要登录；收藏、订单和模拟付款需要 `Authorization: Bearer <access_token>`。创建订单和模拟付款必须带唯一 `Idempotency-Key`。
