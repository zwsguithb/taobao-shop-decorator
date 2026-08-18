---
name: taobao-shop-decorator
description: 淘宝店铺手机端自动装修。This skill should be used when the user asks to 装修/美化/改版淘宝店铺、手机店铺装修、店铺首页装修、店铺详情页装修、生成店铺 Banner/头图/装修方案、自动上架装修素材。支持按自定义需求（风格/色系/文案/商品分组）先产出装修方案与 AI 素材，再通过浏览器自动化（复用用户已登录的 Chrome 会话）在淘宝卖家中心手机端装修后台完成模块搭建、素材上传与发布，最后截图验证。
agent_created: true
---

# 淘宝店铺手机端自动装修（Taobao Mobile Shop Decorator）

## Overview

自动化完成淘宝店铺**手机端**（无线店铺）装修：根据用户自定义需求（风格、色系、文案、商品分组、营销活动），依次产出**装修规格 → 可视化方案 → AI 素材 → 自动执行装修 → 截图验证**，最终在淘宝卖家中心完成手机端首页与商品详情页的模块搭建并发布。

本 Skill 是「领域编排层」：负责需求解析、方案设计、素材生成的编排与判断；实际浏览器操作复用用户本地已登录的淘宝会话，全程不处理密码、验证码或任何登录凭据。

## Workflow Decision Tree

```
用户提出装修需求
├─ 需求信息不完整（缺风格/色系/商品清单/文案任一关键项）
│   └─ 先用 AskUserQuestion 收集，最多追问 2 轮，仍缺失则用合理默认值并在规格中标注
├─ 生成装修规格 JSON ── scripts/build_decoration_spec.py
├─ 渲染可视化方案 HTML ── scripts/render_plan_html.py
│   └─ 展示给用户确认；用户要求修改 → 回到规格重新生成
├─ 用户确认方案后，生成素材（ImageGen / 用户提供）
├─ 浏览器自动化执行装修（见 references/execution-playbook.md）
│   ├─ 执行层可用（web-access 或 playwright-browser-automation 已安装）
│   │   └─ 复用登录态进入卖家中心 → 手机端装修 → 按规格搭模块 → 上传素材 → 保存
│   └─ 执行层不可用 → 提示用户安装浏览器自动化 Skill 或仅交付方案+素材包
└─ 验证：截图检查模块完整性、尺寸、文案 → 用户确认后发布
```

## Phase 1 — 需求解析（收集需求 → 装修规格）

1. 收集用户需求，关键字段如下（缺失时追问或取默认值）：

   | 字段 | 说明 | 默认值 |
   |---|---|---|
   | shop_name | 店铺名称 | 必填 |
   | style | 视觉风格：简约 / 潮酷 / 母婴 / 美妆 / 食品 / 家居 / 数码 / 节日营销 | 简约 |
   | color_scheme | 主色 + 辅色（十六进制） | 按风格从 design-system.md 查表 |
   | target_audience | 目标人群 | 不限 |
   | banner_text | 头图文案（主标题/副标题/行动号召） | 店铺名 + 主推卖点 |
   | products | 主推商品列表：[{name, image, price, link}] | 空 |
   | product_groups | 商品分组名列表，如 新品/热卖/清仓 | 默认三组 |
   | promotions | 优惠活动：[{type: 优惠券/满减/限时, title, detail}] | 空 |
   | detail_scope | 详情页装修范围：关联推荐 / 图文排版 / 全部 | 全部 |

2. 运行 `scripts/build_decoration_spec.py` 生成装修规格 JSON（`decoration_spec.json`）：
   ```
   python scripts/build_decoration_spec.py --input requirements.json --output decoration_spec.json
   ```
   规格包含 `design`（风格/色系/字体）、`homepage.modules`（首页模块布局）、`detail.modules`（详情页模块）、`assets`（素材清单，含尺寸与生图 prompt）。
3. 将规格回读进上下文，作为后续所有步骤的单一事实来源（single source of truth）。

## Phase 2 — 方案设计（可视化方案供用户确认）

1. 运行 `scripts/render_plan_html.py` 生成可视化方案页：
   ```
   python scripts/render_plan_html.py --spec decoration_spec.json --output plan.html
   ```
   方案页包含：手机 750px 预览框中的模块排列效果、每个模块的类型/位置/尺寸、素材清单（尺寸+用途）、文案清单。
2. 用 present_files 打开 `plan.html` 展示给用户。
3. 用户提出修改意见 → 修改 `requirements.json` 后重新运行两个脚本（或直接用 Edit 调整规格 JSON 再渲染）。
4. 用户确认方案后才进入素材与执行阶段，**禁止跳过确认直接装修**。

## Phase 3 — 素材生成（AI 生成 + 用户补充）

1. 依据规格中的 `assets` 清单逐个生成素材：
   - **图片素材**：调用 ImageGen 生成，prompt 已由 build_decoration_spec.py 按风格/色系/文案预生成，生成前按 references/design-system.md 核对尺寸。
   - **用户已有素材**：优先使用用户提供的图片/Logo，缺失部分才 AI 生成。
2. 素材尺寸与用途对照（完整规范见 references/design-system.md）：

   | 素材类型 | 尺寸（750 设计稿） | 用途 |
   |---|---|---|
   | 店铺头图 Banner | 750 × 420 | 手机端首页顶部 |
   | 轮播图 | 750 × 420（可多张） | 首页轮播 |
   | 分类导航图标 | 150 × 150（含文字） | 金刚区导航 |
   | 营销活动图 | 750 × 400 | 活动/优惠券模块 |
   | 商品主图 | 750 × 750 | 商品卡片 |
   | 详情页长图 | 750 × N | 详情页图文排版 |

3. 所有素材统一输出到工作目录 `assets_output/`，文件名与规格中 `assets[].id` 对应（如 `banner_main.png`、`nav_01.png`），便于后续上传时精确对应。

## Phase 4 — 自动执行装修（浏览器自动化）

> 执行前先读 `references/taobao-backend-guide.md`（后台入口与导航）和 `references/execution-playbook.md`（定位策略、操作步骤、故障处理）。

1. **检查执行层**：确认浏览器自动化 Skill 可用：
   - 优先：`web-access`（CDP 直连本地 Chrome，复用登录态，适合淘宝这类强登录场景）；
   - 备选：`playwright-browser-automation`。
   - 均不可用 → 停止自动执行，向用户交付「方案 + 素材包 + 手动操作指引」，并提示可安装对应 Skill。
2. **登录状态确认**：引导用户先在本地 Chrome 手动登录淘宝卖家账号（千牛/卖家中心），随后通过 CDP 复用该会话。**禁止**代填密码、处理验证码或滑块，遇到登录墙立即暂停并提示用户手动处理。
3. **备份现状**：进入手机端装修页后，先对当前装修状态整体截图保存（`backup/` 目录），作为回滚依据。
4. **执行装修**：按 `decoration_spec.json` 逐模块执行：新增模块 → 配置内容 → 上传素材 → 排序，边做边截图。
5. **保存草稿**：全部模块搭建完成后先**保存草稿**，向用户展示截图确认，**发布动作必须由用户明确同意后执行**。

## Phase 5 — 验证与发布

1. 按 `references/execution-playbook.md` 的「验证清单」逐项检查：模块是否齐全、素材尺寸是否正确、文案是否一致、链接是否有效。
2. 用手机预览模式截图首页头部、导航区、商品区、活动区与详情页。
3. 用户确认无误 → 执行发布（手机端装修页的「发布」按钮），再次截图确认发布成功。

## 安全与边界（必须遵守）

- **不处理任何登录凭据**：密码、验证码、滑块、扫码一律引导用户手动完成。
- **不删除用户现有装修**：除非用户明确要求替换某模块；默认在新装修前备份现状（截图 + 草稿）。
- **发布需用户确认**：自动执行止步于「保存草稿」，发布前必须取得用户同意。
- **页面结构变化兜底**：淘宝后台 DOM 可能改版，优先用可见文本/角色定位，固定选择器失败时改用文本匹配或询问用户。
- **素材合规**：AI 生图不得包含品牌侵权元素（其他品牌 Logo、明星肖像等）。

## Resources

### scripts/
- `build_decoration_spec.py` — 需求 JSON → 装修规格 JSON（合并默认模板、生成素材清单与生图 prompt）
- `render_plan_html.py` — 装修规格 JSON → 可视化方案 HTML（手机预览模拟 + 模块/素材/文案清单）

### references/
- `taobao-backend-guide.md` — 淘宝卖家中心入口、手机端装修后台路径与页面结构
- `mobile-modules.md` — 手机端模块库：模块类型、配置项、尺寸、适用场景
- `design-system.md` — 设计规范：风格库、色系表、尺寸规范、文案规范、生图 prompt 模板
- `execution-playbook.md` — 浏览器自动化执行手册：执行层选择、定位策略、逐模块操作步骤、验证清单、故障处理

### assets/templates/
- `homepage_default.json` — 默认首页模块布局模板（金刚区导航/轮播/商品分组/活动/客服）
- `detail_default.json` — 默认详情页模块布局模板（关联推荐/图文详情/营销海报）
