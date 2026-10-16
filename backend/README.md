# GamesClub API

更新：2026-10-16。Django + DRF + PostgreSQL 统一服务；当前为本地模拟交易，真实微信登录已联调，支付、退款及打款未接真实资金。

## 本地运行

在 backend 目录配置 `.env` 中的 `DATABASE_URL`；本地测试显式启用 `ALLOW_DEV_LOGIN` / `ALLOW_MOCK_PAYMENT`。未配置数据库时不会静默回退 SQLite。

```powershell
python -m pip install -r requirements.txt
docker compose up -d db
python manage.py migrate
# 仅首次空开发库补示例目录；已有数据勿重置
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
```

现有环境更新执行 migrate，当前迁移至 `0015_support_conversations`。`0014_service_chat_progress` 新增服务开始／申请完成时间和消息类型，0015 新增客服会话及消息；历史时间仅按已有状态历史回填。

人工测试账号初始化及保护约定见 [固定测试账号](../notices/固定测试账号与使用约定.md)。本机已初始化，不必反复执行；不得提交 `.env`、本地密码文件、数据库或媒体。

## 认证与共同约定

- 开发登录：`GET /api/v1/auth/dev-accounts/`、`POST /api/v1/auth/dev-login/`。同时要求 DEBUG 与 ALLOW_DEV_LOGIN；只允许固定测试组内5个用户／陪玩，拒绝客服及真实微信账号。
- 微信登录：`POST /api/v1/auth/wechat-login/`；服务端换取身份，不下发 AppSecret。
- 用户端 `Authorization: Bearer <access_token>`；管理端 Django Session + CSRF。
- 下单、模拟付款、取消、确认完成及陪玩服务操作使用 `Idempotency-Key`；派单和陪玩服务操作同时校验 `version`。字段以对应接口为准，不把所有写接口都视为同一幂等协议。
- 金额为整数分、抽成为基点；权限、金额、状态和版本由服务端决定。

## 当前履约流程

`PENDING_PAYMENT → PENDING_ARRANGEMENT → ACCEPTED → IN_SERVICE → PENDING_CONFIRMATION → COMPLETED`

付款后客服线下协调并在后台确认实际陪玩，建立订单会话；实际陪玩在会话中开始服务、申请完成，客户同意后才写入完成时间及售后截止时间、计入榜单。指定陪玩只是意向。无独立陪玩工作台、自动验收或群内抢单实现。

历史 `PENDING_ACCEPTANCE` 仍由客服确认，不自动改历史记录；未付款可取消。旧陪玩 accept/reject 与管理端 start/complete 接口返回403。

## 主要接口

下表均以 `/api/v1` 为前缀；完整路由见 `core/urls.py`。

| 方法 | 路径 | 作用与边界 |
| --- | --- | --- |
| GET/PATCH | `/me/` | 个人资料、陪玩身份 |
| POST | `/me/avatar/` | 头像上传 |
| GET/POST | `/me/partner-application/` | 入驻申请 |
| GET/POST | `/me/orders/` | 自己的订单／下单，游戏平台按商品配置校验 |
| POST | `/me/orders/{id}/mock-pay/`、`cancel/`、`confirm/` | 模拟付款、未付款取消、客户确认完成 |
| GET | `/me/partner/orders/` | 实际陪玩的订单读取，无独立工作台页面 |
| POST | `/me/partner/orders/{id}/start/`、`complete/` | 开始／申请完成，校验角色、状态、版本及幂等键 |
| GET | `/me/conversations/`、`/me/conversations/{id}/` | 订单会话列表、详情及履约信息 |
| GET/POST | `/me/conversations/{id}/messages/`（GET）、`send/`（POST） | 仅订单双方读取／发送；普通文字不能伪造服务事件 |
| GET/POST | `/me/support-conversations/`、`/me/support-conversations/{id}/` | 列表／开咨询、读取／发送客服文字 |
| GET/POST | `/management/support-conversations/`、`/management/support-conversations/{id}/` | 员工共享收件箱和回复，保存发送员工 |
| GET | `/management/orders/` | 分页、搜索、筛选、订单详情 |
| POST | `/management/orders/create/` | 人工建单，起点仅待付款或已付款待派单 |
| PATCH/DELETE | `/management/orders/{id}/edit/`（PATCH）、`delete/`（DELETE） | 仅待付款且未付款的订单；当前通用编辑／删除没有请求版本校验 |
| POST | `/management/orders/{id}/assign/` | 客服确认实际陪玩，版本、同游戏、接单资格、预约冲突及更换说明校验 |
| GET/PATCH | `/management/support-settings/` | 外部微信／企业微信客服配置，仅超级管理员可写 |
| GET | `/support/` | 外部渠道公开安全配置；站内客服不依赖外部配置 |

客服发送使用 `content` 和 UUID `client_key`，文字1～2000字。会话按咨询人和订单隔离，可无订单咨询；用户与陪玩的客服会话互不可见，员工不能借此读取双方订单私聊。读取清除团队未读，发送才改变待回复标记。前端显示期间每5秒轮询，尚无 WebSocket、离线通知和坐席分配。

目录、收藏、评价、售后、结算、社区和榜单接口见 [项目总览](../PROJECT_OVERVIEW.md) 与 [频道验证](../notices/频道社区与榜单验证.md)。售后通过后禁止重提，驳回可在原期限及剩余额度内重提；已通过但未妥善退款的案件阻止结算。凭证上传已有接口，私有下载鉴权与端内上传查看待完善。

## 验证与发布边界

```powershell
python manage.py test
python manage.py makemigrations --check --dry-run
```

2026-10-16 PostgreSQL独立测试库全量136项通过。SQLite不能替代事务、行锁与并发验证。两端类型、7项前端测试、H5／微信小程序／后台构建已通过；最新界面完成H5验证，仍需微信真机验证。

多角色复验、结算及配置说明见 [客服与履约联调](../notices/客服互通与售后联调说明.md)；真实收款上线缺口见 [发布准备](../notices/正式发布准备与差距评估.md)。历史P4的陪玩接受／拒绝派单及客服代操作流程已被现行规则替代。
