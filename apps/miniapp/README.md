# 游伴 CLUB · 微信小程序基础交互

> 第四阶段（P4）更新：订单与派单服务已接入——陪玩入驻申请、下单选预约时段、订单 8 态展示与验收、陪玩工作台（接单/拒单/开始/完成）。下面早期“本地订单、无网络请求、五类示例订单”等描述不再代表当前数据层。启动、迁移及未验收项以根目录《第三阶段完成度与联调手册.md》和 [notices/P4-订单与派单服务设计.md](../../notices/P4-订单与派单服务设计.md) 为准。频道、聊天、会员、售后、结算等仍保留本地演示/未开放边界。

按用户已选的 `../../design/index.html` 温和配色 SVG 实现。使用 uni-app、Vue 3、TypeScript；`src/pages.json` 定义微信原生四项 TabBar。H5 仅用于快速检查同一套页面，不是正式客户 Web 产品。

## 运行与构建

推荐 Node.js 22.18+ 或 24，使用 pnpm。依赖与编译器版本已锁定，提交的 `pnpm-lock.yaml` 应随项目保留。

```sh
cd apps/miniapp
pnpm install --frozen-lockfile
pnpm dev:mp-weixin
# 发行构建
pnpm build:mp-weixin
# 浏览器交互预览
pnpm dev:h5
```

在微信开发者工具中导入 `apps/miniapp/dist/dev/mp-weixin`（开发）或 `apps/miniapp/dist/build/mp-weixin`（发行）。当前未填真实 AppID，编译器生成游客测试配置。正式调试请在 `src/manifest.json` 的 `mp-weixin.appid` 填入自己的小程序 AppID 后重新构建，不要填写 AppSecret。工具登录、真机预览和账号授权由项目所有者完成。

## 当前交互

| 设计 | 路由 | 已实现交互 |
| --- | --- | --- |
| 首页 | `/pages/home/index` | 游戏选择、可展开商品搜索、轮播、四个快捷入口、商品详情、特价更多 |
| 频道 | `/pages/channel/index` | 游戏切换、话题搜索、无结果提示、话题详情；左栏只保留游戏分区 |
| 消息 | `/pages/messages/index` | 演示登录引导、会话搜索、微信式单聊消息列表、发送消息、未读清除；消息保存在本机 |
| 我的 | `/pages/profile/index` | 真实昵称头像、设置／通知、订单分类直达、服务入口；已是陪玩时显示「陪玩工作台」入口 |
| 特价 | `/pages/specials/index` | 游戏筛选、价格升降序、商品详情 |
| 订单 | `/pages/orders/index?tab=待付款` | 真实订单 8 态（待付款/待派单/已接单/服务中/待验收…）、取消、模拟付款、客户验收 |
| 服务 | `/pages/services/index` | 余额说明、收藏、积分说明、加入说明 |
| 登录 | `/pages/login/index` | 协议未勾选拦截、协议页、微信登录（微信端）/开发登录（H5）、返回来源、先逛逛 |
| 二级内容 | `/pages/detail/index?kind=...&id=...` | 商品、数量选择、选预约日期/时段、收藏、创建订单、话题、微信式会话、设置、通知、流程／客服说明 |
| 陪玩工作台 | `/pages/partner/index` | 接单状态横幅、待处理（接单/拒单/开始/完成）、历史订单 |

公共内容可直接浏览。会话、订单、个人服务及写操作通过演示登录进入；受保护二级页直接访问也展示登录引导。登录返回参数由应用内生成，不接收任意外部路由。

## 当前数据联调

小程序开发环境默认请求 `http://127.0.0.1:8000/api/v1`，并在 `src/manifest.json` 中关闭微信开发者工具的 `urlCheck`，用于本机演示。启动后端后，使用 `backend/manage.py seed_demo` 创建游戏和商品数据；小程序登录、商品目录、订单创建、订单查询、模拟付款、客户验收、陪玩工作台都会访问后端。正式环境必须将 API 地址改为 HTTPS 环境配置、恢复 `urlCheck: true`，并在微信公众平台配置合法 request 域名，不能把本地地址直接用于发布。

已接入后端：商品目录、登录（微信/开发）、订单创建（含预约时段）、订单查询、取消、模拟付款、客户验收、收藏、陪玩入驻申请、陪玩工作台（接单/拒单/开始/完成）、昵称/头像。仍保留本地演示或未开放：频道、聊天、会员、余额、积分、售后、结算。

## 演示边界

- 每页显示“交互演示 · 非真实交易”。H5 登录走开发账号，微信端走 `uni.login` 真实微信登录。
- 订单为真实后端数据（快照、状态、金额以后端为准），支付为模拟支付。
- `src/domain.ts` 与 `src/store.ts` 集中维护页面状态与演示行为；业务真值在后端。
- 消息、未读和会话草稿通过 `uni` storage 保存，键名为 `gamesclub-local-data-v2`；服务端订单以 API 返回为准。
- 活动抽奖、考核、会员、余额、积分、加入均展示待开放说明，不发奖、不充值、不授予角色。客服入口展示流程与售后帮助，未连接真人客服。

## 验证

```sh
pnpm type-check
pnpm test
pnpm build:mp-weixin
pnpm build:h5
```

`tests/domain.test.ts` 验证组合筛选、金额格式、演示订单重复付款／取消后变更等无效转换。

`scripts/smoke.cjs` 使用 Playwright 检查 H5 的快捷入口、搜索空态、登录勾选与返回、演示订单、会话草稿、收藏、退出及响应式布局。运行前启动 `pnpm dev:h5`；通过 `PLAYWRIGHT_MODULE` 指定可用的 Playwright 包，`CHROME_PATH` 指定浏览器路径（默认 Windows Chrome）。测试截图输出至已忽略的 `test-results/`。

已验证情况以本次交付记录及 `Agent.md` 为准。微信产物可编译不等于已在微信开发者工具或真机执行；真实 AppID、平台登录、网络接口与真机测试是后续接入步骤。

依赖版本参考 [uni-app 官方 Vue3/TS 模板](https://github.com/dcloudio/uni-preset-vue/tree/vite-ts)，构建命令参考 [官方 CLI 文档](https://uniapp.dcloud.net.cn/quickstart-cli)。
