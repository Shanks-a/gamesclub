# 游伴独立运营 Web

Vue 3 + TypeScript + Vite + Router + Pinia + Element Plus。

```powershell
pnpm install --frozen-lockfile
pnpm dev
```

访问 http://127.0.0.1:5174，使用 Django createsuperuser 创建的管理员登录。后端需先迁移并在127.0.0.1:8000运行；/api、/media、/static 通过本地代理转发。

`pnpm type-check` 检查类型，`pnpm build` 构建。根目录《第三阶段完成度与联调手册.md》包含模块完成情况、接口契约、数据备份和手动验收步骤。

当前订单详情和日志详情采用只读结构化展示。页面构建通过不等同于浏览器交互、微信真机或 PostgreSQL 并发验收通过。
