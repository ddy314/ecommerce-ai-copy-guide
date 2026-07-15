#import "@preview/touying:0.7.4": *
#import themes.simple: *

#let navy = rgb("#17324D")
#let blue = rgb("#2563EB")
#let cyan = rgb("#0891B2")
#let mint = rgb("#0F766E")
#let ink = rgb("#172033")
#let muted = rgb("#64748B")
#let pale = rgb("#F1F5F9")
#let light-blue = rgb("#DBEAFE")
#let light-mint = rgb("#D1FAE5")
#let amber = rgb("#D97706")

#set text(font: "Noto Sans CJK SC", fill: ink, size: 20pt)
#set heading(numbering: none)
#show strong: set text(fill: navy)

#let pill(body, fill: light-blue, color: blue) = box(
  fill: fill,
  stroke: color.lighten(35%),
  radius: 6pt,
  inset: (x: 10pt, y: 5pt),
  text(size: 15pt, weight: "bold", fill: color, body),
)

#let stat(value, label, color: blue) = block(
  width: 100%,
  inset: 13pt,
  radius: 8pt,
  fill: color.lighten(87%),
  stroke: color.lighten(55%),
  [#text(size: 27pt, weight: "bold", fill: color)[#value]
   #v(3pt)
   #text(size: 14pt, fill: muted)[#label]],
)

#let card(title, body, color: blue) = block(
  width: 100%,
  inset: 13pt,
  radius: 8pt,
  fill: rgb("#FFFFFF"),
  stroke: color.lighten(55%),
  [#text(size: 18pt, weight: "bold", fill: color)[#title]
   #v(6pt)
   #text(size: 14.5pt, fill: ink)[#body]],
)

#let progress(label, value, color: blue) = grid(
  columns: (26%, 60%, 14%),
  gutter: 8pt,
  align: horizon,
  text(size: 14pt, weight: "bold", fill: navy, label),
  block(width: 100%, height: 10pt, radius: 5pt, fill: pale)[
    #block(width: value, height: 10pt, radius: 5pt, fill: color)
  ],
  align(right, text(size: 13pt, fill: muted)[#value]),
)

#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [电商 AI 商品文案生成与智能导购助手],
    subtitle: [课程项目答辩 · 从运营提效到购物决策的双角色闭环],
    author: [项目组（成员姓名待补充）],
    date: [2026-07-15],
  ),
)

#slide[
  #align(center + horizon)[
    #text(size: 13pt, weight: "bold", fill: cyan)[E-COMMERCE · AI · ASSISTANT]
    #v(9pt)
    #text(size: 34pt, weight: "bold", fill: navy)[电商 AI 商品文案生成与智能导购助手]
    #v(8pt)
    #text(size: 19pt, fill: blue)[从运营提效到购物决策的双角色闭环]
    #v(22pt)
    #grid(
      columns: (1fr, 1fr, 1fr), gutter: 10pt,
      pill([双角色]), pill([全流程], fill: light-mint, color: mint), pill([可离线演示], fill: rgb("#FEF3C7"), color: amber),
    )
    #v(24pt)
    #text(size: 14pt, fill: muted)[项目组（成员姓名待补充） · 2026-07-15]
  ]
]

== 为什么做这个项目

#grid(
  columns: (1fr, 1fr, 1fr),
  gutter: 14pt,
  card([运营内容生产慢], [商品信息分散，标题、卖点、详情和直播脚本需要反复整理。], color: cyan),
  card([用户决策成本高], [价格、评论、规格与售后信息需要跨页面比较，难以形成清晰建议。], color: blue),
  card([演示环境不稳定], [真实模型、网络与采集站点都可能不可用，课程项目必须有离线保底。], color: amber),
)

#v(18pt)
#block(width: 100%, inset: 15pt, radius: 8pt, fill: navy)[
  #text(size: 22pt, weight: "bold", fill: white)[我们的回答：一个双角色、全流程、可离线演示的电商 AI 助手]
]

== 项目范围：一套系统，两类用户

#grid(
  columns: (1fr, 1fr),
  gutter: 18pt,
  block(inset: 16pt, radius: 9pt, fill: light-mint, stroke: mint.lighten(45%))[
    #text(size: 23pt, weight: "bold", fill: mint)[商家端]
    #v(8pt)
    #text(size: 16pt)[
      • 营收看板与导出  
      • 商品、订单、用户管理  
      • AI 文案、评论洞察、直播脚本  
      • 知识库、问答统计、客服会话  
      • 京东 / 苏宁采集任务
    ]
  ],
  block(inset: 16pt, radius: 9pt, fill: light-blue, stroke: blue.lighten(45%))[
    #text(size: 23pt, weight: "bold", fill: blue)[用户端]
    #v(8pt)
    #text(size: 16pt)[
      • 商品浏览、搜索与收藏  
      • 购物车、下单、支付、收货  
      • 地址、评价与售后  
      • 商品智能问答与推荐  
      • 人工客服与历史记录
    ]
  ],
)

#v(14pt)
#align(center)[#pill([核心不是单点生成，而是把 AI 放进完整业务闭环])]

== 四类 AI 能力

#grid(
  columns: (1fr, 1fr),
  rows: (1fr, 1fr),
  gutter: 12pt,
  card([01 商品文案], [输入商品、类目、卖点、受众与风格；输出标题、核心卖点和详情文案。], color: cyan),
  card([02 智能导购], [结合需求、预算、偏好和候选商品，生成主推荐、理由与备选方案。], color: blue),
  card([03 评论分析], [提取情感、关键词、优缺点与改进建议，让评论变成运营信号。], color: mint),
  card([04 直播脚本], [按平台、时长与语气组织开场、卖点、互动、转化与收尾。], color: amber),
)

== 系统架构

#align(center)[
  #image("assets/system-architecture.png", width: 66%)
]

#v(2pt)
#align(center)[
  #grid(
    columns: (1fr, 1fr, 1fr), gutter: 10pt,
    pill([Vue 3 · TypeScript], fill: cyan.lighten(88%), color: cyan),
    pill([Flask 3 · SQLAlchemy], fill: light-blue, color: blue),
    pill([Compose · PostgreSQL], fill: light-mint, color: mint),
  )
]

== AI / RAG 处理链路

#align(center)[
  #image("assets/ai-flow.png", width: 88%)
]

#v(12pt)
#grid(
  columns: (1fr, 1fr), gutter: 14pt,
  card([稳定性设计], [结构化校验、Provider 抽象、Mock 保底、Redis 可降级。], color: mint),
  card([可追踪性设计], [生成任务、问答记录和来源写入数据库，便于运营分析。], color: blue),
)

== 数据模型支撑业务闭环

#grid(
  columns: (57%, 43%),
  gutter: 15pt,
  align(center + horizon, image("assets/data-relationships.png", width: 88%)),
  [
    #stat([14 张表], [用户、商品、交易、AI、知识库与客服], color: blue)
    #v(8pt)
    #text(size: 15pt)[
      #pill([快照策略], fill: rgb("#FEF3C7"), color: amber) 订单保存商品与地址快照。  
      #v(8pt)
      #pill([迁移策略], fill: light-mint, color: mint) SQLAlchemy + Alembic；本地可用 SQLite。
    ]
  ],
)

== 关键难点与突破

#text(size: 13pt)[#table(
  columns: (23%, 32%, 45%),
  inset: 9pt,
  stroke: rgb("#CBD5E1"),
  fill: (x, y) => if y == 0 { navy } else if calc.even(y) { pale } else { white },
  table.header(
    text(weight: "bold", fill: white)[难点],
    text(weight: "bold", fill: white)[问题],
    text(weight: "bold", fill: white)[解决方式],
  ),
  [AI 外部依赖], [密钥、配额、网络不可控], [Provider 抽象 + Mock AI；同一接口不改前端],
  [权限隔离], [用户与商家功能交叉], [JWT + 服务端角色校验；前端菜单只负责体验],
  [订单一致性], [状态、商品与地址会变化], [状态机式动作 + 商品/地址快照 + 售后时间线],
  [部署漂移], [开发与生产环境不同], [Compose、Nginx 同源代理、Alembic 启动迁移],
  [第三方采集], [站点结构与反爬变化], [任务化、进度可见、失败保留、种子数据保底],
)]

== 工程质量与验证

#grid(
  columns: (1fr, 1fr, 1fr, 1fr),
  gutter: 10pt,
  stat([10], [已有后端测试用例], color: blue),
  stat([70+], [Flask API 路由], color: cyan),
  stat([14], [领域数据表], color: mint),
  stat([4], [AI 核心工具], color: amber),
)

#v(14pt)
#progress([前端生产构建], 100%, color: mint)
#v(8pt)
#progress([认证 / JWT / CORS 自动化], 100%, color: blue)
#v(8pt)
#progress([核心 API 自动化], 80%, color: cyan)
#v(8pt)
#progress([PostgreSQL 集成场景], 55%, color: amber)

== 部署与演示路径

#grid(
  columns: (1fr, 1fr, 1fr),
  gutter: 14pt,
  card([1 · 一键启动], [`docker compose up --build -d`], color: mint),
  card([2 · 打开系统], [`http://localhost:8080`], color: blue),
  card([3 · 健康检查], [`http://localhost:8000/health`], color: cyan),
)

#v(18pt)
#block(width: 100%, inset: 15pt, radius: 8pt, fill: pale, stroke: blue.lighten(55%))[
  #text(size: 18pt, weight: "bold", fill: navy)[答辩演示建议路径]
  #v(6pt)
  #text(size: 15pt)[用户提问与下单 → 商家查看订单并发货 → 评论分析与知识库 → 营收看板 → 架构与测试说明]
]

== 团队分工

#text(size: 12.5pt)[#table(
  columns: (18%, 23%, 42%, 17%),
  inset: 8pt,
  stroke: rgb("#CBD5E1"),
  fill: (x, y) => if y == 0 { navy } else if calc.even(y) { pale } else { white },
  table.header(
    text(weight: "bold", fill: white)[成员],
    text(weight: "bold", fill: white)[角色],
    text(weight: "bold", fill: white)[负责模块],
    text(weight: "bold", fill: white)[答辩部分],
  ),
  [待填写], [项目负责人], [范围、计划、集成、风险与交付], [背景 / 总结],
  [待填写], [前端开发], [用户端、购物车、订单与个人中心], [功能演示],
  [待填写], [前端开发], [商家端、AI 工具与运营看板], [功能演示],
  [待填写], [后端开发], [API、认证、交易、客服与上传], [技术架构],
  [待填写], [数据 / AI], [数据库、RAG、AI Provider 与采集], [难点突破],
  [待填写], [测试 / 文档], [验证、部署、文档与答辩材料], [测试结果],
)]

#v(12pt)
#text(size: 14pt, fill: muted)[成员姓名、学号和最终模块比例请在提交前与《项目组成员分工表》同步补齐。]

== 项目收获与下一步

#grid(
  columns: (1fr, 1fr), gutter: 18pt,
  block(inset: 16pt, radius: 9pt, fill: light-blue, stroke: blue.lighten(45%))[
    #text(size: 22pt, weight: "bold", fill: blue)[我们完成了]
    #v(8pt)
    #text(size: 16pt)[
      • 双角色电商业务闭环  
      • 四类 AI 工具与 RAG 问答  
      • 数据、缓存、采集与客服协同  
      • 容器部署与可复现文档
    ]
  ],
  block(inset: 16pt, radius: 9pt, fill: light-mint, stroke: mint.lighten(45%))[
    #text(size: 22pt, weight: "bold", fill: mint)[下一步]
    #v(8pt)
    #text(size: 16pt)[
      • 清理教学兼容的明文密码字段  
      • 扩大 PostgreSQL 集成测试  
      • 引入真实向量检索与评测  
      • 加强监控、审计与内容合规
    ]
  ],
)

#v(18pt)
#align(center)[#pill([从“能生成”走向“可运营、可交易、可维护”], fill: navy, color: white)]

== 谢谢

#align(center + horizon)[
  #text(size: 34pt, weight: "bold", fill: navy)[感谢聆听]
  #v(10pt)
  #text(size: 19pt, fill: muted)[电商 AI 商品文案生成与智能导购助手]
  #v(18pt)
  #pill([Q & A], fill: light-blue, color: blue)
]
