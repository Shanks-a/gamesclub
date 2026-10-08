# GamesClub API

第四阶段（P4）：已完成订单与派单服务、陪玩入驻审核、管理端订单增删改查。运行步骤与验收边界见根目录《第三阶段完成度与联调手册.md》与 [notices/P4-订单与派单服务设计.md](./notices/P4-订单与派单服务设计.md)。先配置 backend/.env 的 DATABASE_URL（PostgreSQL），显式启用本地 ALLOW_DEV_LOGIN/ALLOW_MOCK_PAYMENT；未配置数据库会报错，不再静默使用 SQLite。现有数据库更新只执行 migration，勿运行重置数据操作。独立 Web 在 apps/admin，Django Admin 目录和订单改为只读。

开发运行：

```powershell
python -m pip install -r requirements.txt
docker compose up -d db
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

本地开发也可用 SQLite 快速跑测试：`ALLOW_SQLITE_DEV=1 DATABASE_URL= python manage.py test`（并发用例会自动跳过）。

## 认证

- 开发登录：`POST /api/v1/auth/dev-login/`。开发登录仅在 `DEBUG=1` 时可用。
- 微信登录：`POST /api/v1/auth/wechat-login/`（小程序微信端）。
- 商品公开接口不需要登录；收藏、订单和模拟付款需要 `Authorization: Bearer <access_token>`。
- 创建订单和模拟付款必须带唯一 `Idempotency-Key`。

## 小程序端接口（Bearer）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/PATCH | `/me/` | 我的资料（昵称/头像，含 `is_partner`/`partner_active`） |
| POST | `/me/avatar/` | 上传头像 |
| POST/GET | `/me/partner-application/` | 提交/查询陪玩入驻申请 |
| POST | `/me/orders/` | 下单（支持 `appointment_date`/`appointment_slot`） |
| POST | `/me/orders/{id}/mock-pay/` | 模拟付款 |
| POST | `/me/orders/{id}/cancel/` | 取消订单 |
| POST | `/me/orders/{id}/confirm/` | 客户验收订单 |
| GET | `/me/partner/orders/` | 陪玩工作台：派给我的订单 |
| POST | `/me/partner/orders/{id}/accept/` | 陪玩接受派单 |
| POST | `/me/partner/orders/{id}/reject/` | 陪玩拒绝派单 |
| POST | `/me/partner/orders/{id}/start/` | 开始服务 |
| POST | `/me/partner/orders/{id}/complete/` | 完成服务 |

## 管理端接口（Session + CSRF）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/management/orders/` | 订单列表（分页、搜索、状态/用户/日期筛选） |
| POST | `/management/orders/create/` | 手动建单（客户/商品/数量/时段/状态/付款/陪玩） |
| PATCH | `/management/orders/{id}/edit/` | 编辑订单（改商品或数量自动重算金额） |
| DELETE | `/management/orders/{id}/delete/` | 删除订单（连带清理支付记录与状态历史） |
| POST | `/management/orders/{id}/assign/` | 派单（指定 partner_id，含时段冲突检查） |
| GET | `/management/customers/` | 列出客户（非管理员账号） |
| GET | `/management/partner-applications/` | 入驻申请列表 |
| POST | `/management/partner-applications/{id}/approve/` | 通过申请（自动建 Partner） |
| POST | `/management/partner-applications/{id}/reject/` | 驳回申请 |
| GET/POST/PATCH | `/management/partners/` | 陪玩档案列表 / 新增 / 编辑（绑分区、接单开关） |

订单状态机：`PENDING_PAYMENT`（待付款）→ `PENDING_ARRANGEMENT`（待派单）→ `PENDING_ACCEPTANCE`（待陪玩确认）→ `ACCEPTED`（已接单）→ `IN_SERVICE`（服务中）→ `PENDING_CONFIRMATION`（待验收）→ `COMPLETED`（已完成）；另有 `CANCELLED`（已取消）。陪玩拒绝回到 `PENDING_ARRANGEMENT` 可换人重派。
