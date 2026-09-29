# 端到端验收报告（第三阶段 · 本地模拟业务）

> 执行时间：2026-09-29 09:45–10:20（GMT+8）
> 环境：Windows 10 · Docker Desktop（backend-db-1, PostgreSQL 17）· Django 5.2 runserver 127.0.0.1:8000 · 管理端 Vite 5174 · 小程序 H5 Vite 5173
> 验收账号：管理端 `accept-admin`；小程序端 dev-login（统一 dev-player）
> 结论：**8 项手动验收清单全部通过**（API/逻辑层 23/23 断言 PASS；UI 层关键页面截图留证）

## 一、验收方式

- **API/逻辑层**：`notices/e2e_verify.py`（可重复执行）直连后端驱动全部 8 项场景，结果落盘 `notices/e2e_verify_results.json`。**23/23 PASS**。
- **UI 层**：agent-browser（Chromium）操作管理 Web 与小程序 H5，截图存 `notices/e2e-screenshots/`。
- **过程中发现并修复 1 个真实缺陷**（见第四节），修复后全量复跑通过。

## 二、逐项结果

| # | 验收项 | 结果 | 关键证据 |
|---|---|---|---|
| 1 | Web 新建游戏/类型/商品并发布；小程序首页出现新游戏、详情可打开 | ✅ PASS | 三轮脚本累计：game_id=6(b9abb4),7(ea6852) / cat_id=15,16 / prod_id=6(b9abb4),7(ea6852) 创建 201；公共目录命中；H5 游戏 tab 出现全部验收游戏（06-h5-home.png）；商品卡点击跳转详情（12-h5-product-detail.png；API 层 GET /products/{id}/ 已验证） |
| 2 | 配置轮播/特价/人气；小程序显示一致；无虚构销量 | ✅ PASS | run2 配置 home_id=3(特价)/4(人气)→商品6；run3 配置 home_id=5/6→商品7；H5 限时特价+人气热选与后台一致（¥29/¥39，07-h5-specials-popular.png）；`product_detail` 无 sales 类虚构字段 |
| 3 | 创建订单记下订单号金额；Web 改价/下架后旧订单保留原快照 | ✅ PASS | 订单 GC9971e23744df49acad180574383c40（数量2，总价5800，快照单价2900）；改价至3000 后旧订单仍 2900；管理端订单查询页显示快照商品（03-admin-orders.png） |
| 4 | 模拟付款；Web 同订单出现 PAID 与状态历史；重复提交不产生第二笔成功付款 | ✅ PASS | 首次 mock-pay → PAID/PENDING_ARRANGEMENT；同幂等键重放 200（回放原结果）；异键再付 409；管理端订单详情含付款事件历史（04-admin-order-detail.png） |
| 5 | 收藏后退出再登录仍存在；退出后旧令牌 401 | ✅ PASS | 收藏 1 条；logout 后旧 token 请求 401；重新 dev-login 后收藏仍在 |
| 6 | Web 两处同时编辑商品，旧版本保存返回 409 | ✅ PASS | 旧 version PATCH → 409 VERSION_CONFLICT；操作日志记录改价/下架审计（05-admin-audit-log.png） |
| 7 | 网络断开显示失败、不出现付款成功；快速切换游戏不串列表 | ✅ PASS | 停后端后刷新 H5：空/错误状态、无任何「付款成功」文案、无付款成功接口调用（11-h5-backend-down.png）；恢复后端 200。快速连点「和平精英→王者荣耀」终态为王者荣耀且列表干净（08-h5-rapid-switch.png）；请求序号保护代码 home/index.vue:22-44 复核确认 |
| 8 | 停用游戏/类型/商品后旧页不能下单，历史订单可查 | ✅ PASS | 商品7（ea6852）下架 → 下单 409 PRODUCT_UNAVAILABLE；历史订单 GET 200；H5 该游戏分区显示「暂无商品」空态（09-h5-unpublished-game-empty.png）；首页特价/人气配置条目自动隐藏（下架商品的首页条目被 `is_available` 过滤） |

## 三、补充验证（超出清单）

- **管理端全流程 UI**：登录 → 概览（商品7/上架6/订单1）→ 订单查询 → 订单详情 → 操作日志（01–05 截图）。
- **审计日志**：create/update products、home、改价、下架均有 before/after 记录，actor=accept-admin。
- **CSRF 轮换**：登录后使用登录响应返回的新 token 写入成功（写操作全部带 X-CSRFToken）。
- **幂等回放**：创建订单/付款/取消的幂等键机制在真实服务上复验（同键回放、异键 409）。

## 四、发现并修复的缺陷

**[已修复] H5 端 API 基地址缺失 `/api/v1` 前缀**
- 现象：H5 首页游戏 tab 只剩「推荐」、限时特价/人气全空；后端日志无来自 H5 的 API 请求（仅图标静态资源）。
- 根因：`apps/miniapp/src/api/client.ts` 中 H5 分支 `BASE_URL=''`，请求路径变成 `/games/`（丢失 `/api/v1`），Vite 代理只匹配 `/api` 前缀，`/games/` 命中 SPA fallback 返回 index.html（200），前端 `.map` 解析失败静默清空列表。
- 修复：H5 分支改为 `'/api/v1'`（走 Vite 代理 → 8000，路径完整）。`pnpm type-check` 通过，热更新后首页数据完整。
- 影响：仅影响 H5 dev 形态；MP-WEIXIN 构建不受影响（仍用绝对地址或 VITE_API_BASE_URL）。

## 五、已知边界（本轮不变）

- 真实微信登录（P3）、派单/售后/结算、频道/消息后端化仍未开发——与本阶段边界一致。
- 模拟付款仅成功路径；开发登录为统一 dev-player。
- 微信开发者工具真机预览、合法域名配置需 AppID 凭据后由用户手动执行。

## 六、复跑指引

```bash
# 前置：Docker 引擎运行、backend-db-1 容器 Up；后端 8000、admin 5174、H5 5173 已启动
cd backend && .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000 --noreload
cd apps/admin && pnpm dev          # 5174
cd apps/miniapp && pnpm dev:h5     # 5173

# API 层全量复跑（23 项断言）
python notices/e2e_verify.py

# UI 层：打开 http://127.0.0.1:5174（accept-admin / Accept#2026gc）与 http://127.0.0.1:5173
```
