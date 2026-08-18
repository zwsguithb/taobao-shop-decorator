# taobao-shop-decorator（淘宝店铺手机端自动装修 Skill）

面向 WorkBuddy / Claude 类 AI Agent 的领域编排型 Skill：根据自定义需求（风格、色系、文案、商品分组、营销活动），自动化完成**淘宝店铺手机端**的首页与详情页装修。

## 核心能力

- **五阶段工作流**：需求解析 → 方案设计 → AI 素材生成 → 自动执行装修 → 验证发布
- **自定义需求**：8 种视觉风格（简约/潮酷/母婴/美妆/食品/家居/数码/节日营销）+ 色系表 + 文案规范
- **方案先行**：自动生成可视化装修方案（手机预览模拟 + 模块清单 + 素材清单），确认后才执行
- **AI 素材**：按 750px 设计稿规范预生成每张素材的生图 prompt（Banner/轮播/导航图标/活动海报/详情长图）
- **自动执行**：复用用户已登录的 Chrome 会话（CDP），在淘宝卖家中心手机端装修后台逐模块搭建、上传素材、保存草稿
- **安全设计**：不处理任何登录凭据；自动执行止步于保存草稿，发布必须用户确认；装修前自动截图备份现状

## 使用方式

1. 将本目录作为 Skill 安装到 `~/.workbuddy/skills/taobao-shop-decorator/`
2. 对 Agent 说：**"帮我装修淘宝店铺手机端，风格要 XX、主推 XX 商品…"**
3. Agent 依次产出：装修规格 → 可视化方案（确认）→ AI 素材 → 自动装修 → 验证发布

> 自动执行阶段依赖浏览器自动化执行层（推荐 `web-access`，CDP 复用登录态）；未安装时自动降级为「方案 + 素材包 + 手动操作指引」。

## 目录结构

```
taobao-shop-decorator/
├── SKILL.md                          # 主文件：触发条件与五阶段工作流
├── references/
│   ├── taobao-backend-guide.md       # 淘宝卖家中心入口与手机端装修后台导航
│   ├── mobile-modules.md             # 手机端模块库（类型/尺寸/配置项/选型规则）
│   ├── design-system.md              # 设计规范（风格/色系/尺寸/文案/生图 prompt 模板）
│   └── execution-playbook.md         # 浏览器自动化执行手册（定位策略/验证清单/故障处理）
├── scripts/
│   ├── build_decoration_spec.py      # 需求 JSON → 装修规格 JSON（含素材清单与生图 prompt）
│   └── render_plan_html.py           # 装修规格 JSON → 可视化方案 HTML
└── assets/templates/
    ├── homepage_default.json         # 默认首页模块布局
    └── detail_default.json           # 默认详情页模块布局
```

## 快速试用

```bash
# 生成装修规格（需求字段可缺省，自动取默认值）
python scripts/build_decoration_spec.py --input requirements.json --output decoration_spec.json

# 渲染可视化装修方案
python scripts/render_plan_html.py --spec decoration_spec.json --output plan.html
```

## 安全边界

- 不处理密码、验证码、滑块，一律引导用户手动完成
- 不删除用户现有装修模块，执行前截图备份现状
- 发布动作必须经用户明确确认
