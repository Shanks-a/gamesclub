# 游伴 CLUB · 游戏陪玩俱乐部系统 — 全功能文档

## 客服互通与售后修复（2026-10-16，现行补充）

- 站内在线客服已接通用户、陪玩与后台共享收件箱；按咨询人和订单隔离，支持未读、待回复和文字消息重试去重。
- 后台业务列表、用户订单与会话按 5 秒轮询同步；编辑中的表单保留。付款后返回首页；下单去掉重复选陪玩入口。
- 售后通过后不可重复申请；驳回可在原期限和可退金额内重提。用户显示售后／退款结果，后台显示申请原因。已通过但退款未妥善完成的案件阻止结算。
- 新增迁移 0015_support_conversations；配置里的外部微信客服为选配，站内沟通不依赖该配置。
- 后端能力缺口、结算与配置用途、复验步骤见 [客服互通与售后联调说明](./notices/客服互通与售后联调说明.md)。本次不代表真实收付款或正式发布。

> 本文档覆盖后端 API、微信小程序（uni-app）、运营管理后台（Vue3 + Element Plus）三端。数据与实现以代码为准，更新于 2026-10-16。正式上线缺口见 [发布准备与差距评估](./notices/正式发布准备与差距评估.md)。

---

## 目录

1. [项目概览](#1-项目概览)
2. [技术栈与架构](#2-技术栈与架构)
3. [数据模型](#3-数据模型)
4. [小程序端功能](#4-小程序端功能)
5. [运营管理后台功能](#5-运营管理后台功能)
6. [后端 API 能力](#6-后端-api-能力)
7. [核心业务机制](#7-核心业务机制)
8. [工程化与质量保障](#8-工程化与质量保障)
9. [本地运行指南](#9-本地运行指南)
10. [环境变量与配置](#10-环境变量与配置)
11. [里程碑与当前边界](#11-里程碑与当前边界)

---

## 1. 项目概览

**游伴 CLUB** 是一个游戏陪玩俱乐部系统，提供游戏分区浏览、陪玩商品选购、下单预约、陪玩入驻、人工派单、履约验收、评价、售后、结算的完整业务闭环。

当前处于**本地模拟业务联调阶段**：真实微信登录已打通，但支付、派单后的真实资金流转为模拟实现（`ALLOW_MOCK_PAYMENT`），不涉及真实收付款。

**三端构成：**

| 端 | 技术 | 入口 | 说明 |
|---|---|---|---|
| 后端 API | Django 5.2 + DRF + PostgreSQL 17 | `http://127.0.0.1:8000` | 业务核心 + 管理 API |
| 小程序 | uni-app (Vue3 + TS) | H5 `:5173` / 微信小程序 | 面向用户/陪玩 |
| 管理后台 | Vue3 + Element Plus | `http://127.0.0.1:5174` | 面向运营/管理员 |

---

## 2. 技术栈与架构

### 后端
- **Django 5.2 + Django REST Framework**，PostgreSQL 17（Docker 容器 `backend-db-1`）
- **认证**：小程序走 Bearer Token；管理端走 Session + CSRF
- **API 文档**：drf-spectacular 自动生成 OpenAPI schema
- **金额**：一律整数分（`*_cents`）存储，避免浮点误差
- **抽成**：整数基点（`commission_bp`，10000 = 100%），整数运算 `(net*bp+5000)//10000` 四舍五入

### 小程序 / 管理端
- 小程序：uni-app + Vue 3 + TypeScript，H5 与微信小程序双端构建
- 管理端：Vue 3 + Element Plus，单文件应用（`App.vue` + 动态 section 路由）
- 包管理：pnpm 12

### 端口
| 服务 | 端口 |
|---|---|
| 后端 | 8000 |
| 小程序 H5 | 5173 |
| 管理后台 | 5174 |

---

## 3. 数据模型

30 个 core 模型，按业务域分组（不含 Django 内置模型）：

| 域 | 模型 | 说明 |
|---|---|---|
| 账号 | `UserProfile` | 用户资料（昵称、头像、角色） |
| 账号 | `WechatIdentity` | 微信身份 `(appid, openid)` 唯一归并 |
| 账号 | `AccessToken` | 登录令牌（可撤销） |
| 账号 | `PartnerApplication` | 陪玩入驻申请 |
| 账号 | `Partner` | 陪玩档案（绑分区 + 接单开关） |
| 商品 | `GamePartition` | 游戏分区 |
| 商品 | `ProductCategory` | 商品类型（属某游戏） |
| 商品 | `Product` | 服务商品（价格、上下架、首页投放） |
| 商品 | `Favorite` | 用户收藏 |
| 订单 | `Order` | 订单（8 态 + 金额快照 + 财务字段） |
| 订单 | `OrderStatusHistory` | 订单状态流转留痕 |
| 订单 | `PaymentAttempt` | 支付尝试记录 |
| 订单 | `IdempotencyRecord` | 幂等键记录 |
| 售后 | `Review` | 订单评价（一单一评） |
| 售后 | `AfterSaleCase` | 售后案件 |
| 售后 | `Refund` | 退款单 |
| 售后 | `Evidence` | 售后凭证（上传接口已有，私有下载鉴权待完善） |
| 结算 | `Settlement` | 结算批次 |
| 结算 | `SettlementItem` | 结算明细（一单一笔） |
| 配置 | `SystemConfig` | 系统配置（抽成比例、售后时限等） |
| 首页 | `HomeEntry` | 首页投放位（轮播/特价/人气） |
| 审计 | `AuditLog` | 关键写操作留痕 |
| 会话 | `Conversation` / `Message` | 订单参与者私信及消息 |
| 客服 | `SupportConversation` / `SupportMessage` | 按咨询人和订单隔离的客服会话、团队已读与消息 |
| 社区 | `CommunityPost` / `CommunityImage` | 游戏公开动态及所属图片 |
| 社区 | `CommunityLike` / `CommunityComment` | 唯一点赞、评论与隐藏状态 |

数据库迁移：`0001` ~ `0015` 共 15 个；`0015_support_conversations` 新增客服会话与消息；`0014_service_chat_progress` 新增服务开始/申请完成时间及结构化消息类型。本地已应用，其他环境部署需执行 migrate。

---

## 4. 小程序端功能

### 页面清单（14 个已注册页面）

| 页面 | 路径 | 说明 |
|---|---|---|
| 首页 | `pages/home` | 轮播、限时特价、人气热选 |
| 频道 | `pages/channel` | 各游戏分区公开图文动态、点赞、评论；陪玩热度榜／接单榜，前三名及完整排名 |
| 消息 | `pages/messages` | 订单与客服统一列表、置顶搜索、未读／待回复、最近消息排序 |
| 在线客服 | `pages/support-chat` | 用户／陪玩与后台客服互发文字 |
| 我的 | `pages/profile` | 个人信息、收藏、订单入口 |
| 限时特价 | `pages/specials` | 特价商品列表 |
| 人气热选 | `pages/popular` | 人气商品列表 |
| 游戏商品 | `pages/game-products` | 某游戏下商品 |
| 商品详情 | `pages/detail` | 详情 + 下单 |
| 我的订单 | `pages/orders` | 订单列表 + 操作 |
| 服务中心 | `pages/services` | 售后入口 |
| 登录 | `pages/login` | 登录/微信登录 |
| 订单会话 | `pages/chat` | 订单关联私信与发送消息 |
| 提交订单 | `pages/checkout` | 角色资料、留言、意向陪玩底部选择弹窗 |

### 用户侧功能

**商品浏览**
- 首页轮播 / 特价 / 人气（仅展示已上架 `is_available` 商品，下架自动隐藏）
- 按游戏分区浏览商品分类与商品
- 商品详情：价格、原价、数量范围、收藏

**收藏**
- 收藏 / 取消收藏
- 我的收藏列表

**下单与支付**
- 当前提交订单页仅显示商品支持的游戏平台，填写角色名/ID、留言及备注；后端保留预约日期/时段字段，当前表单不提供对应选择控件
- 只保留上方指定陪陪选项：页内底部弹窗，名称/ID 搜索、头像及总接单信息，选中回填
- 付款后进入客服人工派单，指定陪玩作为意向参考；已移除“5分钟自动安排”文案，按客服人工确认安排
- 数量（受商品 min/max 约束）
- 订单金额快照（下单时固化商品名、游戏名、单价）
- 模拟付款（`mock-pay`）

**订单管理**
- 订单列表、详情
- 未付款可取消；付款后返回首页
- 操作按钮同高右对齐，窄屏可换行；移除联系接单陪玩按钮，从消息进入订单对话
- 服务完成后**确认验收**
- 验收后**评价**（星级 + 内容，一单一评）
- 服务中、待验收及完成后期限内**售后申请**（金额 + 理由）；显示售后／退款结果，通过后禁止重提，驳回可在原期限及剩余额度内重提

**账号**
- 微信登录（真实，`WechatIdentity` 归并，重登不重复建号）
- dev-login（本地模拟账号）
- 昵称 / 头像编辑

### 客服派单与会话履约

- 不恢复陪玩工作台；客服在系统外协调接单及通知。
- 后台确认接单后直接进入已接单，原子关联实际陪玩并建立订单会话。
- 实际接单陪玩在订单对话中开始服务、申请完成；客户同意后才完成订单并计算售后期限。
- 陪玩 accept/reject 写接口停用；start/complete 由实际陪玩在会话中调用。管理端 start/complete 停用；旧待陪玩确认订单仍由客服处理。
- 接口、校验及验收见 [客服与履约联调](./notices/客服互通与售后联调说明.md)。

---

## 5. 运营管理后台功能

人工测试使用 `test-staff-01` / `test-staff-02`；旧超级管理员仅用于维护。管理模块：

| Section | 功能 |
|---|---|
| **运营概览** | 商品总数、上架数、订单数、各状态订单分布 |
| **游戏分区** | 增删改查（名称、图标、排序、启用开关） |
| **商品类型** | 增删改查（名称、所属游戏、说明、排序、启用） |
| **商品管理** | 增删改查、上下架、首页投放（勾选轮播/特价/人气即自动投放）、封面上传 |
| **首页配置** | 轮播/特价/人气投放位的增删改查与跳转配置 |
| **订单查询** | 列表（筛选：用户名/状态/日期）、新增订单；仅未付款可编辑/删除；**客服确认接单**；服务进度由陪玩与客户推进 |
| **陪玩申请** | 入驻申请审核（通过/驳回，通过自动建陪玩档案） |
| **陪玩档案** | 档案管理（绑分区、接单开关、编辑、删除） |
| **售后复核** | 售后案件列表、复核（通过→生成退款单/驳回）、退款执行（成功/失败/未知） |
| **结算批次** | 发起结算、查看结算批次与明细 |
| **业务与客服配置** | 抽成比例、售后时限、可选外部客服渠道；普通员工只读，超级管理员可保存 |
| **客服会话** | 用户／陪玩共享收件箱，未读／待回复筛选、文字回复；保存具体发送员工 |

**其他能力**
- 操作日志（审计）查看
- 文件上传（商品封面、首页图）
- 业务列表与只读订单详情显示期间每5秒刷新；编辑表单不被轮询覆盖

---

## 6. 后端 API 能力

### 认证
- `POST /auth/dev-login/` — 本地模拟登录
- `POST /auth/wechat-login/` — 微信 code 换 token
- `POST /auth/logout/` — 退出撤销 token

### 用户端（Bearer，`/me` 前缀）
- `GET/PATCH /me/` — 个人资料
- `POST /me/avatar/` — 头像上传
- `POST /me/partner-application/` — 提交陪玩申请
- `GET /me/partner/orders/` + `start/complete` — 实际陪玩开始／申请完成（版本与幂等键）；旧 accept/reject 返回403
- `GET/POST /me/orders/` — 订单列表/创建
- `GET /me/orders/<id>/`、`cancel/`、`mock-pay/`、`confirm/`、`review/`、`aftersale/` — 订单操作
- `POST /me/aftersale-evidence/` — 售后凭证上传
- `GET/POST /me/favorites/`、`DELETE /me/favorites/<pid>/` — 收藏

### 公共（`/games`、`/products`、`/home`）
- 游戏列表、游戏分类、商品列表、商品详情、首页投放

### 频道社区与榜单（均以 `/api/v1` 为前缀）
- `GET/POST /games/<id>/posts/`：公开分页浏览，登录后发布图文（1000字、最多9图）
- `POST /community/images/`：认证上传、图片格式/大小校验、重新编码、上传者归属校验
- `PUT /community/posts/<id>/like/`：显式点赞或取消，唯一约束防重复
- `GET/POST /community/posts/<id>/comments/`：分页读取、登录后评论（300字）
- `DELETE /community/posts/<id>/`、`DELETE /community/comments/<id>/`：作者隐藏自己的内容
- `GET /games/<id>/leaderboard/?sort=heat|orders`：近30天完成单量/累计完成单量，前三名及完整分页榜单
- 公开读、认证写；管理员通过 Django Admin 隐藏违规动态及评论。举报、自动内容审核和防刷尚未接入
- 接口及验证详见 [频道社区与榜单验证](./notices/频道社区与榜单验证.md)

### 订单私信（Bearer）
- `GET /me/conversations/`、`GET /me/conversations/<id>/messages/`、`POST /me/conversations/<id>/send/`
- `GET /me/conversations/<id>/` 返回订单角色、服务状态／版本／时间及消息；仅订单双方访问
- 订单参与者授权访问，消息存后端；显示期间每5秒轮询，尚无 WebSocket／离线通知

### 站内客服
- `GET/POST /me/support-conversations/` 列表／开咨询；`GET/POST /me/support-conversations/<id>/` 读取／发送
- 员工对应 `/management/support-conversations/` 与 `/<id>/`，沿用 Session + CSRF
- 每位咨询人及订单独立会话，无订单也可咨询；文本1～2000字，UUID `client_key` 去重
- 员工共享团队已读，查看消除未读，回复改变待回复状态；不开放用户与陪玩的订单私聊给员工

### 管理端（`/management/`，Session + CSRF）
- 会话、登录、退出
- 概览、上传、订单 CRUD + 派单、客户列表
- 陪玩申请审核、陪玩档案 CRUD
- `POST /orders/<id>/assign/`：客服确认接单（带 version）；管理端 start/complete 返回403，改由陪玩接口推进服务
- `GET/PATCH /support-settings/`：客服配置，修改仅超级管理员；公开读取为 `/api/v1/support/`
- 售后列表/复核、退款执行、取消退款
- 结算批次列表/创建
- 系统配置读写
- 通用资源 CRUD（`<resource>/` 映射 games/categories/products/home）
- 审计日志

---

## 7. 核心业务机制

### 订单主流程（客服人工履约）

```
PENDING_PAYMENT      待付款
    ↓ 付款
PENDING_ARRANGEMENT  待派单
    ↓ 客服线下确认人选，后台确认接单
ACCEPTED             已接单
    ↓ 实际陪玩在订单会话开始服务
IN_SERVICE           服务中
    ↓ 实际陪玩在订单会话申请完成
PENDING_CONFIRMATION 待客户验收
    ↓ 客户确认
COMPLETED            已完成
```

历史 `PENDING_ACCEPTANCE` 归入待派单，由客服再次确认。未付款可取消；已付款的取消/退款沿售后流程处理。确认接单、陪玩开始及申请完成均要求当前版本，事务记录操作者、状态历史及审计；陪玩写操作同时要求幂等键，申请完成不会提前计入榜单。



### 幂等与并发保护
- 下单、付款、取消均需 `Idempotency-Key`，同键回放返回原结果，改参 409
- 乐观锁：目录写入、派单及陪玩服务等动作校验 `version`，旧版本返回409；通用未付款订单编辑／删除尚未校验请求版本，不能宣称全部写操作均受乐观锁保护
- 结算用 `select_for_update()` 行锁防重复结算

### 售后链路
1. 服务中、待验收及完成后售后期限内申请（金额 + 理由）
2. 客服查看原因并复核：通过 → 生成待退款单并预留金额；驳回 → 可在原期限内重提
3. 模拟退款结果同步至用户订单；处理中、已通过、已关闭的案件禁止重提
4. 失败／未知需跟进，现阶段缺少完整重试查单页面；已通过但未妥善退款的案件阻止结算

### 结算机制
- 管理员发起结算，输入数据库内部数字订单 ID 列表（不是 GC 订单号）
- 校验：已完成、已付款、过售后时限、无待处理或已通过待退款售后、无待退款或结果未知退款、未结算、有陪玩
- `抽成 = (净收益 × 抽成基点 + 5000) // 10000`（整数分，四舍五入）
- `陪玩收益 = 净收益 - 抽成`
- 历史订单已回填抽成比例 20%（基点 2000）

### 配置中心（`SystemConfig`）
- `commission_bp` 抽成基点（默认 2000 = 20%）
- `aftersale_window_hours` 售后时限（默认 48 小时），客户确认完成时生成截止时间
- `customer_support` 可选微信／企业微信渠道；关闭外部渠道不影响站内客服
- 抽成在下单时固化，修改配置不改老订单抽成或已有售后截止时间

---

## 8. 工程化与质量保障

### 测试
- **后端**：全量测试包括微信登录、并发幂等、订单 CRUD、派单、售后、结算、私信、频道社区及榜单；2026-10-16 全量136项通过，详见 [联调记录](./notices/客服互通与售后联调说明.md)
- **小程序**：node:test 单测（逻辑层）+ `vue-tsc` 类型检查 + H5/微信双端构建
- **管理端**：node:test 单测（API 层）+ `vue-tsc` 类型检查 + 构建
- 前端测试采用 **Node 内置 `node:test`**（零依赖，规避 pnpm 12 Windows 沙箱符号链接缺陷）

### CI（`.github/workflows/ci.yml`）
三任务流水线，push 到 `main` / `workbuddy/main-cf29d12c` 自动触发：
1. 后端测试（PostgreSQL 17 服务容器）
2. 小程序类型检查 + 单测 + 构建
3. 管理端类型检查 + 单测 + 构建

### 质量要点
- 依赖版本精确锁定（`requirements.txt`）
- 生产安全基线（`DEBUG=False` 时：安全 Cookie、HSTS、防嗅探、X-Frame-Options；SSL 跳转由 `DJANGO_SECURE_SSL_REDIRECT` 显式开启，默认交反代）
- 订单列表已消除 N+1 查询（`select_related` + `prefetch_related`）
- `.env` / 密钥不入库，`.gitignore` 覆盖敏感文件

---

## 9. 本地运行指南

### 前置
- Docker Desktop（PostgreSQL 17 容器）
- Python 3.12+（后端用 `.venv`）
- Node 22 + pnpm 12

### 启动步骤

**1. 数据库**
```bash
docker start backend-db-1   # 或 docker compose up -d（backend/ 下）
```

**2. 后端**
```bash
cd backend
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

**3. 小程序 H5**
```bash
cd apps/miniapp
pnpm install
pnpm dev:h5        # http://127.0.0.1:5173
```

**4. 管理后台**
```bash
cd apps/admin
pnpm install
pnpm dev           # http://127.0.0.1:5174
```

### 测试
```bash
# 后端
cd backend && .venv/Scripts/python.exe manage.py test

# 小程序
cd apps/miniapp && pnpm type-check && pnpm test

# 管理端
cd apps/admin && pnpm type-check && pnpm test
```

### 账号
- 管理后台：自行运行 `python manage.py createsuperuser` 创建独立账号，不使用历史文档中的演示凭据作为生产账号
- 小程序本地：仅开发环境允许 dev-login；生产使用真实微信身份

---

## 10. 环境变量与配置

### 后端 `.env`（见 `.env.example`）

| 变量 | 说明 | 默认 |
|---|---|---|
| `DJANGO_DEBUG` | 调试开关 | 1 |
| `DJANGO_SECRET_KEY` | 密钥 | — |
| `DJANGO_ALLOWED_HOSTS` | 允许主机 | 127.0.0.1,localhost |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | CSRF 白名单 | — |
| `DATABASE_URL` | 数据库连接串 | — |
| `ALLOW_DEV_LOGIN` | 是否允许模拟登录 | 0 |
| `ALLOW_MOCK_PAYMENT` | 是否允许模拟支付 | 0 |
| `WECHAT_APPID` / `WECHAT_APPSECRET` | 微信小程序凭据 | 空 |
| `DJANGO_SECURE_SSL_REDIRECT` | 应用层 SSL 跳转（默认交反代） | 0 |

### 小程序 `.env`
- `VITE_API_BASE_URL`：API 基地址（H5 用相对路径 `/api/v1` 走 vite 代理；非 H5 用 `http://127.0.0.1:8000/api/v1`）

---

## 11. 里程碑与当前边界

### 已完成
- [x] 第一阶段：后端数据层 + 核心模型
- [x] 第二阶段：小程序数据层 + 模拟真实产品功能
- [x] 第三阶段：运营后台 + 双端数据统一 + 端到端验收
- [x] **P3 客户数据**：真实微信登录 + 昵称/头像
- [x] **P4 订单与派单服务**：入驻审核、人工派单、8 态状态机、管理端订单增删改查
- [x] **P5 售后/结算**：评价、售后退款、陪玩结算、系统配置
- [x] **前端测试 + CI**：node:test 单测 + 三任务流水线
- [x] 质量提升：N+1 修复、依赖锁定、生产安全基线

### 当前边界 / 待完善
| 项 | 状态 |
|---|---|
| 客服人工确认接单 | 已实现客服确认人选、陪玩在订单会话开始/申请完成、客户同意后完成；站内客服已互通，外部微信渠道待配置／真机验证 |
| 生产部署（HTTPS/Nginx/备份/监控） | 未开发（P6 边界） |
| 真实支付接入 | 当前为模拟支付 |
| 真实退款与打款 | 后台模拟退款及账面结算，未连接资金渠道 |
| 公开社区治理 | 已有作者删除/后台隐藏；审核、举报、防刷及媒体下架需补齐 |
| 微信真机验收 | 本次频道及陪陪弹窗仅完成 H5 验证和微信构建 |
| 管理端组件化 | 客服收件箱、配置及订单动作已拆组件；其余可按实际维护需要拆分 |
| 售后凭证上传数量上限 | 需业务规则后加 |

### 关键提交记录
- `d7fdb5c` P5-A 评价
- `c9a929c` P5-B 售后退款
- `020cc5d` P5-C 陪玩结算
- `fbb6fe8` P5-D 前端测试 + CI
- `3c513f2` 质量提升（N+1 + 依赖锁定 + 安全基线）
- `744e680` 文档同步
- `ae38047` CI 修复（SSL 跳转默认关 + pnpm 12 对齐）
