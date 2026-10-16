# 游伴 CLUB · 微信小程序基础交互

> 2026-10-16：频道已接入公开图文、点赞、评论和真实完成单量榜单；订单与客服会话存后端；提交订单页内选择陪陪底部弹窗已完成。仍为本地联调，收付款与退款未接真实渠道。现行功能以 [项目总览](../../PROJECT_OVERVIEW.md) 为准，发布缺口见 [发布准备](../../notices/正式发布准备与差距评估.md)。

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

在微信开发者工具中导入 `apps/miniapp/dist/dev/mp-weixin`（开发）或 `apps/miniapp/dist/build/mp-weixin`（发行）。`src/manifest.json` 已配置开发使用的 AppID；发布前确认属于正式主体，重新构建。不要在前端填写 AppSecret。工具登录、真机预览和账号授权由项目所有者完成。

## 当前交互

| 设计 | 路由 | 已实现交互 |
| --- | --- | --- |
| 首页 | `/pages/home/index` | 游戏选择、可展开商品搜索、轮播、四个快捷入口、商品详情、特价更多 |
| 频道 | `/pages/channel/index` | 左侧仅游戏，公开图文、点赞、评论；热度/累计接单榜、前三名与完整排名 |
| 消息 | `/pages/messages/index` | 订单与在线客服统一列表，搜索栏置顶、最近消息排序、未读／待回复标记 |
| 订单会话 | `/pages/chat/index` | 双方私信；陪玩开始／申请完成，客户确认；结构化服务事件 |
| 在线客服 | `/pages/support-chat/index` | 用户／陪玩与后台客服文字互通，支持订单咨询及一般咨询 |
| 我的 | `/pages/profile/index` | 真实昵称头像、设置／通知、订单分类直达、服务入口 |
| 特价 | `/pages/specials/index` | 游戏筛选、价格升降序、商品详情 |
| 订单 | `/pages/orders/index?tab=待付款` | 真实进度、陪玩资料及售后退款结果；横排客服／售后／主操作按钮，移除联系接单陪玩按钮；付款后返回首页，显示期间自动刷新 |
| 服务 | `/pages/services/index` | 余额说明、收藏、积分说明、加入说明 |
| 登录 | `/pages/login/index` | 协议未勾选拦截、协议页、微信登录（微信端）/开发登录（H5）、返回来源、先逛逛 |
| 二级内容 | `/pages/detail/index?kind=...&id=...` | 商品、规格/数量选择、收藏、设置、通知、流程说明等 |
| 提交订单 | `/pages/checkout/index` | 仅显示商品支持的游戏平台，角色资料、留言、备注、单一指定入口及底部弹窗，提交后进入待付款 |

公共内容可直接浏览。会话、订单和互动写操作要求登录（微信端真实登录，H5 开发登录）。用户已取消独立陪玩工作台，群内接单协调和通知由客服人工完成；后台确认接单；实际陪玩在订单会话开始服务、申请完成，客户在会话或订单页最终验收。登录返回参数由应用内生成，不接收任意外部路由。

## 当前数据联调

小程序开发环境默认请求 `http://127.0.0.1:8000/api/v1`，并在 `src/manifest.json` 中关闭微信开发者工具的 `urlCheck`，用于本机演示。启动后端后，使用 `backend/manage.py seed_demo` 创建游戏和商品数据；小程序登录、商品目录、订单创建、订单查询、模拟付款、客户验收、订单会话都会访问后端。正式环境必须将 API 地址改为 HTTPS 环境配置、恢复 `urlCheck: true`，并在微信公众平台配置合法 request 域名，不能把本地地址直接用于发布。

已接入后端：商品目录、登录（微信/开发）、下单、订单查询、取消、模拟付款、客户验收、收藏、昵称/头像、订单私信、频道图文/点赞/评论及榜单。陪玩履约、评价、售后文字申请与结果已接入；陪玩入驻入口、售后图片凭证及真实结算仍按首发范围补齐。会员、余额、积分等仍为未开放/示例能力。

## 演示边界

- 每页显示“交互演示 · 非真实交易”。H5 登录走开发账号，微信端走 `uni.login` 真实微信登录。
- 订单为真实后端数据（快照、状态、金额以后端为准），支付为模拟支付。
- `src/domain.ts` 与 `src/store.ts` 集中维护页面状态与演示行为；业务真值在后端。
- 订单会话消息及频道互动以服务端为准；发帖文字草稿仅存当前设备，按账号/游戏隔离。
- 活动抽奖、考核、会员、余额、积分不提供真实资金或发奖能力。陪玩申请接口存在，入口与履约流程仍需验收。站内客服通过后台客服会话接待；微信／企业微信为额外配置渠道。

## 验证

```sh
pnpm type-check
pnpm test
pnpm build:mp-weixin
pnpm build:h5
```

`tests/domain.test.ts` 验证组合筛选、金额格式、演示订单重复付款／取消后变更等无效转换。

`scripts/smoke.cjs` 使用 Playwright 检查 H5 的快捷入口、搜索空态、登录勾选与返回、演示订单、会话草稿、收藏、退出及响应式布局。运行前启动 `pnpm dev:h5`；通过 `PLAYWRIGHT_MODULE` 指定可用的 Playwright 包，`CHROME_PATH` 指定浏览器路径（默认 Windows Chrome）。测试截图输出至已忽略的 `test-results/`。

当前多角色规则与复验步骤见 [客服与履约联调](../../notices/客服互通与售后联调说明.md)，固定账号见 [测试账号](../../notices/固定测试账号与使用约定.md)。原 `scripts/smoke.cjs` 对应早期演示页面，不能替代现行多角色验证。

已验证情况见 [频道验收](../../notices/频道社区与榜单验证.md)、[陪陪弹窗验收](../../notices/选择陪陪弹窗验证.md) 及 `Agent.md`。微信身份已有开发者工具真实联调记录；本次新增界面通过类型检查、H5/微信构建和 H5 操作验证，尚未真机验收。

依赖版本参考 [uni-app 官方 Vue3/TS 模板](https://github.com/dcloudio/uni-preset-vue/tree/vite-ts)，构建命令参考 [官方 CLI 文档](https://uniapp.dcloud.net.cn/quickstart-cli)。
