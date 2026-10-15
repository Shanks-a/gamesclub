# 游伴 CLUB · 游戏陪玩俱乐部系统 — 全功能文档

> 本文档为项目当前实现的**完整功能清单**，覆盖后端 API、微信小程序（uni-app）、运营管理后台（Vue3 + Element Plus）三端。数据与实现以代码为准，更新于 2026-10-14。

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

22 个模型，按业务域分组：

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
| 售后 | `Evidence` | 售后凭证（私有存储） |
| 结算 | `Settlement` | 结算批次 |
| 结算 | `SettlementItem` | 结算明细（一单一笔） |
| 配置 | `SystemConfig` | 系统配置（抽成比例、售后时限等） |
| 首页 | `HomeEntry` | 首页投放位（轮播/特价/人气） |
| 审计 | `AuditLog` | 关键写操作留痕 |

数据库迁移：`0001` ~ `0010` 共 10 个。

---

## 4. 小程序端功能

### 页面清单（12 个页面）

| 页面 | 路径 | 说明 |
|---|---|---|
| 首页 | `pages/home` | 轮播、限时特价、人气热选 |
| 频道 | `pages/channel` | 游戏分区入口 |
| 消息 | `pages/messages` | 会话列表 |
| 我的 | `pages/profile` | 个人信息、收藏、订单入口 |
| 限时特价 | `pages/specials` | 特价商品列表 |
| 人气热选 | `pages/popular` | 人气商品列表 |
| 游戏商品 | `pages/game-products` | 某游戏下商品 |
| 商品详情 | `pages/detail` | 详情 + 下单 |
| 我的订单 | `pages/orders` | 订单列表 + 操作 |
| 服务中心 | `pages/services` | 售后入口 |
| 登录 | `pages/login` | 登录/微信登录 |
| 陪玩工作台 | `pages/partner` | 陪玩接单/履约（后端已就绪，页面待完善） |

### 用户侧功能

**商品浏览**
- 首页轮播 / 特价 / 人气（仅展示已上架 `is_available` 商品，下架自动隐藏）
- 按游戏分区浏览商品分类与商品
- 商品详情：价格、原价、数量范围、收藏

**收藏**
- 收藏 / 取消收藏
- 我的收藏列表

**下单与支付**
- 下单选预约时段（日期 + 上午/下午/晚上三档）
- 数量（受商品 min/max 约束）
- 订单金额快照（下单时固化商品名、游戏名、单价）
- 模拟付款（`mock-pay`）

**订单管理**
- 订单列表、详情
- 取消订单
- 服务完成后**确认验收**
- 验收后**评价**（星级 + 内容，一单一评）
- 验收后**售后申请**（金额 + 理由，受售后时限约束）

**账号**
- 微信登录（真实，`WechatIdentity` 归并，重登不重复建号）
- dev-login（本地模拟账号）
- 昵称 / 头像编辑

### 陪玩侧功能（`me/partner/orders`）

- 查看派给自己的订单
- 接单 / 拒单
- 开始服务 / 完成服务

---

## 5. 运营管理后台功能

登录账号：`accept-admin`。11 个 section：

| Section | 功能 |
|---|---|
| **运营概览** | 商品总数、上架数、订单数、各状态订单分布 |
| **游戏分区** | 增删改查（名称、图标、排序、启用开关） |
| **商品类型** | 增删改查（名称、所属游戏、说明、排序、启用） |
| **商品管理** | 增删改查、上下架、首页投放（勾选轮播/特价/人气即自动投放）、封面上传 |
| **首页配置** | 轮播/特价/人气投放位的增删改查与跳转配置 |
| **订单查询** | 列表（筛选：用户名/状态/日期）、新增订单、编辑（改商品数量自动重算）、删除、**派单** |
| **陪玩申请** | 入驻申请审核（通过/驳回，通过自动建陪玩档案） |
| **陪玩档案** | 档案管理（绑分区、接单开关、编辑、删除） |
| **售后复核** | 售后案件列表、复核（通过→生成退款单/驳回）、退款执行（成功/失败/未知） |
| **结算批次** | 发起结算、查看结算批次与明细 |
| **抽成与售后配置** | 抽成比例（基点）、售后时限（小时）配置 |

**其他能力**
- 操作日志（审计）查看
- 文件上传（商品封面、首页图）

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
- `GET /me/partner/orders/` + `accept/reject/start/complete` — 陪玩订单履约
- `GET/POST /me/orders/` — 订单列表/创建
- `GET /me/orders/<id>/`、`cancel/`、`mock-pay/`、`confirm/`、`review/`、`aftersale/` — 订单操作
- `POST /me/aftersale-evidence/` — 售后凭证上传
- `GET/POST /me/favorites/`、`DELETE /me/favorites/<pid>/` — 收藏

### 公共（`/games`、`/products`、`/home`）
- 游戏列表、游戏分类、商品列表、商品详情、首页投放

### 管理端（`/management/`，Session + CSRF）
- 会话、登录、退出
- 概览、上传、订单 CRUD + 派单、客户列表
- 陪玩申请审核、陪玩档案 CRUD
- 售后列表/复核、退款执行、取消退款
- 结算批次列表/创建
- 系统配置读写
- 通用资源 CRUD（`<resource>/` 映射 games/categories/products/home）
- 审计日志

---

## 7. 核心业务机制

### 订单 8 态状态机

```
PENDING_PAYMENT     待付款
    ↓ 付款
PENDING_ARRANGEMENT 待派单
    ↓ 管理员派单
PENDING_ACCEPTANCE  待陪玩确认
    ↓ 陪玩接单          ↓ 陪玩拒单（回退待派单）
ACCEPTED            已接单
    ↓ 开始服务
IN_SERVICE          服务中
    ↓ 完成服务
PENDING_CONFIRMATION 待验收
    ↓ 客户确认验收
COMPLETED           已完成
（任一点客户取消 → CANCELLED 已取消）
```

### 幂等与并发保护
- 下单、付款、取消均需 `Idempotency-Key`，同键回放返回原结果，改参 409
- 乐观锁：写操作 `PATCH` 必带 `version`，旧版本 409 `VERSION_CONFLICT`
- 结算用 `select_for_update()` 行锁防重复结算

### 售后链路
1. 客户验收后、售后时限内发起申请（金额 + 理由）
2. 管理员复核：通过 → 生成待退款单并冻结金额；驳回 → 关闭
3. 退款执行：成功/失败/未知（失败释放冻结、未知待人工确认）
4. 可取消待退款单

### 结算机制
- 管理员发起结算，输入订单号列表
- 校验：已完成、已付款、过售后时限、无在途售后/退款、未结算、有陪玩
- `抽成 = (净收益 × 抽成基点 + 5000) // 10000`（整数分，四舍五入）
- `陪玩收益 = 净收益 - 抽成`
- 历史订单已回填抽成比例 20%（基点 2000）

### 配置中心（`SystemConfig`）
- `commission_bp` 抽成基点（默认 2000 = 20%）
- `aftersale_window_hours` 售后时限（默认 48 小时）

---

## 8. 工程化与质量保障

### 测试
- **后端**：70 项测试全绿（Django TestCase），覆盖微信登录、并发幂等、订单 CRUD、派单、售后、结算、首页投放同步、配置回归
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
- 管理后台：`accept-admin` / `Accept#2026gc`
- 小程序本地：dev-login（`dev-player`）

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
| 陪玩工作台小程序页 | 后端接口就绪，页面待完善 |
| 生产部署（HTTPS/Nginx/备份/监控） | 未开发（P6 边界） |
| 真实支付接入 | 当前为模拟支付 |
| 管理端 `App.vue` 单文件 | 可拆组件（非缺陷） |
| 售后凭证上传数量上限 | 需业务规则后加 |

### 关键提交记录
- `d7fdb5c` P5-A 评价
- `c9a929c` P5-B 售后退款
- `020cc5d` P5-C 陪玩结算
- `fbb6fe8` P5-D 前端测试 + CI
- `3c513f2` 质量提升（N+1 + 依赖锁定 + 安全基线）
- `744e680` 文档同步
- `ae38047` CI 修复（SSL 跳转默认关 + pnpm 12 对齐）
