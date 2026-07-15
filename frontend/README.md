# 前端应用

Vue 3 + TypeScript 单页应用，提供普通用户商城与商家运营后台。界面基础组件使用 Ant Design Vue，布局使用 Tailwind CSS，页面切换与交互动画使用 Motion for Vue。

## 开发

要求 Node.js 20+，推荐使用项目锁文件安装：

```bash
npm ci
npm run dev
```

开发地址为 <http://localhost:5173>。Vite 会将 `/api` 和 `/health` 代理到 `http://localhost:8000`，因此通常不需要配置前端环境变量。

若后端不在默认地址，可创建不提交 Git 的 `.env.local`：

```env
VITE_API_BASE_URL=http://192.168.1.10:8000
```

## 常用命令

```bash
npm run dev       # 启动开发服务器
npm run build     # TypeScript 检查并生成生产产物
npm run preview   # 本地预览 dist
npm audit         # 检查依赖安全公告
```

## 代码结构

```text
src/
├── api.ts                 # 通用 API 请求封装
├── theme.ts               # Ant Design 主题与 Motion 动画参数
├── App.vue                # 登录状态、角色分流和异步页面入口
├── components/
│   ├── common/            # 导航、侧栏、客服等共享组件
│   ├── merchant/          # 商家后台页面
│   └── user/              # 用户商城页面
├── main.ts
└── style.css              # Tailwind 入口与少量全局基础规则
```

业务页面通过 `defineAsyncComponent` 按需加载；截图和 XLSX 导出库仅在用户触发导出时加载。生产构建使用 Vite 8/Rolldown 将 Vue、Ant Design 和 Motion 拆分为独立缓存块。

## 生产部署

根目录执行：

```bash
docker compose up --build -d
```

前端 Dockerfile 使用 Node 构建后复制到 Nginx。Nginx 负责 SPA fallback，并将 `/api`、`/health` 同源转发到后端，默认访问地址为 <http://localhost:8080>。
