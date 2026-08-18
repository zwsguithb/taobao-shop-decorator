#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_plan_html.py — 淘宝店铺装修：装修规格 JSON → 可视化方案 HTML

用法:
    python render_plan_html.py --spec decoration_spec.json --output plan.html

输出一个自包含 HTML（无外部依赖），包含：
  1. 方案摘要（店铺/风格/色系/文案）
  2. 手机预览框：首页与详情页模块排列效果模拟
  3. 模块清单表
  4. 素材清单表（含尺寸、用途、AI 生图 prompt）
"""

import argparse
import html
import json
import os


# ---------------------------------------------------------------------------
# HTML 工具
# ---------------------------------------------------------------------------
def esc(s):
    return html.escape(str(s if s is not None else ""))


def color_block(c):
    return f'<span class="swatch" style="background:{esc(c)}" title="{esc(c)}"></span> {esc(c)}'


# ---------------------------------------------------------------------------
# 手机预览渲染（按模块类型生成预览 HTML）
# ---------------------------------------------------------------------------
def render_module(m, primary, secondary):
    t = m.get("type", "")
    title = esc(m.get("title", ""))
    sec = secondary[0] if secondary else "#EEEEEE"
    if t == "banner":
        return (f'<div class="mod banner" style="background:linear-gradient(135deg,{esc(primary)},{esc(sec)})">'
                f'<div class="mod-title">🖼 {title}</div>'
                f'<div class="banner-ph"><span>750×420 头图</span></div></div>')
    if t == "nav":
        items = m.get("items", [])
        cells = "".join(
            f'<div class="nav-item"><div class="nav-ico" style="background:{esc(sec)}"></div>'
            f'<span>{esc(it.get("label",""))}</span></div>' for it in items)
        return f'<div class="mod"><div class="mod-title">🧭 {title}</div><div class="nav-grid">{cells}</div></div>'
    if t == "carousel":
        imgs = m.get("images", [])
        dots = "".join('<span class="dot"></span>' for _ in imgs)
        return (f'<div class="mod carousel" style="background:{esc(sec)}">'
                f'<div class="mod-title">🎠 {title}（{len(imgs)} 张）</div>'
                f'<div class="carousel-ph"><span>750×420 轮播</span>{dots}</div></div>')
    if t == "coupon":
        return (f'<div class="mod coupon" style="border:2px dashed {esc(primary)};color:{esc(primary)}">'
                f'<div class="mod-title">🎟 {title}</div>'
                f'<div class="coupon-body">{esc(m.get("title_text","")) or "优惠券位"}</div></div>')
    if t == "promo":
        return (f'<div class="mod promo" style="background:linear-gradient(135deg,{esc(sec)},{esc(primary)})">'
                f'<div class="mod-title">🎯 {title}</div>'
                f'<div class="promo-ph"><span>750×400 活动图</span></div></div>')
    if t == "product_group":
        products = m.get("products", []) or []
        if products:
            cards = "".join(
                f'<div class="p-card"><div class="p-img" style="background:{esc(sec)}"></div>'
                f'<span>{esc(p.get("name",""))}</span><b>{esc(p.get("price",""))}</b></div>'
                for p in products[:4])
        else:
            cards = "".join(
                f'<div class="p-card"><div class="p-img" style="background:{esc(sec)}"></div>'
                f'<span>商品位</span></div>' for _ in range(4))
        return (f'<div class="mod"><div class="mod-title">📦 {title}'
                f'<i>（分组：{esc(m.get("group_query",""))}）</i></div>'
                f'<div class="p-grid">{cards}</div></div>')
    if t == "related":
        n = m.get("count", 6)
        cards = "".join(
            f'<div class="p-card"><div class="p-img" style="background:{esc(sec)}"></div>'
            f'<span>关联商品</span></div>' for _ in range(n))
        return f'<div class="mod"><div class="mod-title">🔗 {title}</div><div class="p-grid">{cards}</div></div>'
    if t == "service":
        return (f'<div class="mod service" style="border-color:{esc(primary)};color:{esc(primary)}">'
                f'<div class="mod-title">💬 {esc(m.get("label", title))}</div></div>')
    if t == "custom":
        return (f'<div class="mod custom" style="background:repeating-linear-gradient(45deg,'
                f'{esc(sec)}22,{esc(sec)}22 8px,#fff 8px,#fff 16px)">'
                f'<div class="mod-title">🧩 {title}</div>'
                f'<div class="custom-ph"><span>{esc(m.get("image","长图"))}</span></div></div>')
    return f'<div class="mod"><div class="mod-title">❓ {title}（{esc(t)}）</div></div>'


def render_phone(spec, scope):
    primary = spec["design"]["colors"]["primary"]
    secondary = spec["design"]["colors"]["secondary"]
    modules = spec[scope]["modules"]
    body = "".join(render_module(m, primary, secondary) for m in modules)
    return (f'<div class="phone">'
            f'<div class="phone-notch"></div>'
            f'<div class="phone-screen">{body}</div>'
            f'<div class="phone-home"></div></div>')


# ---------------------------------------------------------------------------
# 表格渲染
# ---------------------------------------------------------------------------
def render_module_table(scope_label, modules):
    rows = ""
    for i, m in enumerate(modules, 1):
        detail = m.get("title", m.get("type", ""))
        extra = ""
        if m.get("group_query"):
            extra = f'（分组：{esc(m["group_query"])}）'
        if m.get("items"):
            extra = f'（{len(m["items"])} 项）'
        if m.get("images"):
            extra = f'（{len(m["images"])} 张）'
        rows += (f'<tr><td>{i}</td><td><code>{esc(m.get("type",""))}</code></td>'
                 f'<td>{esc(detail)}{extra}</td></tr>')
    return (f'<h3>{esc(scope_label)}模块（{len(modules)} 个）</h3>'
            f'<table><thead><tr><th>#</th><th>类型</th><th>内容</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def render_asset_table(assets):
    rows = ""
    for a in assets:
        rows += (f'<tr><td><code>{esc(a.get("id",""))}</code></td>'
                 f'<td>{esc(a.get("type",""))}</td>'
                 f'<td>{esc(a.get("size",""))}</td>'
                 f'<td>{esc(a.get("purpose",""))}</td>'
                 f'<td class="prompt-cell">{esc(a.get("prompt",""))}</td></tr>')
    return (f'<h3>素材清单（{len(assets)} 张）</h3>'
            f'<table><thead><tr><th>文件</th><th>类型</th><th>尺寸</th>'
            f'<th>用途</th><th>AI 生图 Prompt</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="渲染淘宝手机店铺装修可视化方案 HTML")
    ap.add_argument("--spec", default="decoration_spec.json", help="装修规格 JSON 路径")
    ap.add_argument("--output", default="plan.html", help="输出方案 HTML 路径")
    args = ap.parse_args()

    with open(args.spec, "r", encoding="utf-8") as f:
        spec = json.load(f)

    meta = spec["meta"]
    design = spec["design"]
    colors = design["colors"]
    bt = design.get("banner_text", {})

    phone_home = render_phone(spec, "homepage")
    phone_detail = render_phone(spec, "detail")
    mod_home = render_module_table("首页", spec["homepage"]["modules"])
    mod_detail = render_module_table("详情页", spec["detail"]["modules"])
    assets_html = render_asset_table(spec["assets"])

    sec_sw = "".join(color_block(c) for c in colors["secondary"])
    banner_text_html = (
        f'<div class="banner-text">'
        f'<div><b>主标题</b>：{esc(bt.get("main",""))}</div>'
        f'<div><b>副标题</b>：{esc(bt.get("sub",""))}</div>'
        f'<div><b>行动号召</b>：{esc(bt.get("cta",""))}</div>'
        f'</div>' if bt else "")

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>装修方案 · {esc(meta.get("shop_name",""))}</title>
<style>
  :root {{ --primary: {esc(colors["primary"])}; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "PingFang SC","Microsoft YaHei",sans-serif; background:#f4f5f7; color:#1f2937; padding: 24px; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .sub {{ color: #6b7280; font-size: 13px; margin-bottom: 20px; }}
  h2 {{ font-size: 18px; margin: 28px 0 12px; border-left: 4px solid var(--primary); padding-left: 10px; }}
  h3 {{ font-size: 15px; margin: 18px 0 8px; }}
  .cards {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(240px,1fr)); gap: 12px; }}
  .card {{ background:#fff; border-radius: 10px; padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .card b {{ color:#374151; }}
  .card .val {{ font-size: 14px; margin-top:4px; }}
  .swatch {{ display:inline-block; width:16px; height:16px; border-radius:4px; vertical-align:middle; margin-right:4px; border:1px solid #e5e7eb; }}
  .banner-text {{ font-size: 14px; line-height: 1.9; }}
  .phones {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(330px,1fr)); gap: 20px; }}
  .phone {{ width: 300px; margin: 0 auto; background:#111; border-radius: 34px; padding: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.25); }}
  .phone-notch {{ width: 90px; height: 18px; background:#111; border-radius: 0 0 12px 12px; margin: -4px auto 6px; }}
  .phone-screen {{ background:#fff; border-radius: 22px; overflow: hidden; }}
  .phone-home {{ width: 44px; height: 4px; background:#333; border-radius: 2px; margin: 8px auto 2px; }}
  .mod {{ padding: 8px; border-bottom: 1px solid #f0f0f0; }}
  .mod-title {{ font-size: 11px; color:#6b7280; margin-bottom: 6px; }}
  .mod-title i {{ color:#9ca3af; font-style: normal; }}
  .banner, .promo {{ border-radius: 8px; color: #fff; min-height: 84px; }}
  .banner-ph, .promo-ph, .carousel-ph {{ display:flex; flex-direction:column; align-items:center; justify-content:center; color: rgba(255,255,255,.85); font-size: 12px; min-height: 60px; border: 1px dashed rgba(255,255,255,.5); border-radius: 6px; }}
  .carousel {{ border-radius: 8px; }}
  .carousel-ph {{ color:#6b7280; border-color:#d1d5db; }}
  .dot {{ display:inline-block; width:6px; height:6px; border-radius:50%; background:#9ca3af; margin: 6px 2px; }}
  .nav-grid {{ display:grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }}
  .nav-item {{ text-align:center; font-size:10px; color:#374151; }}
  .nav-ico {{ width:34px; height:34px; border-radius:10px; margin:0 auto 2px; }}
  .coupon {{ border-radius: 8px; background:#fff; }}
  .coupon-body {{ text-align:center; padding: 8px; font-weight: 600; }}
  .p-grid {{ display:grid; grid-template-columns: repeat(4,1fr); gap: 6px; }}
  .p-card {{ text-align:center; font-size:9px; color:#374151; }}
  .p-img {{ height: 42px; border-radius:6px; margin-bottom:2px; }}
  .p-card b {{ display:block; color: #e60012; }}
  .service {{ border: 1px solid; border-radius: 8px; text-align:center; padding: 10px; }}
  .custom {{ border-radius: 8px; min-height: 56px; }}
  .custom-ph {{ border:1px dashed #9ca3af; border-radius:6px; color:#6b7280; font-size:11px; text-align:center; padding: 14px; }}
  table {{ width:100%; border-collapse: collapse; background:#fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.08); font-size: 13px; }}
  th, td {{ padding: 8px 10px; border-bottom: 1px solid #f0f0f0; text-align: left; vertical-align: top; }}
  th {{ background: #f9fafb; color: #374151; font-weight: 600; }}
  code {{ background:#f3f4f6; padding: 1px 6px; border-radius: 4px; font-size: 12px; }}
  .prompt-cell {{ color: #6b7280; max-width: 320px; }}
  .note {{ background:#fffbeb; border:1px solid #fde68a; border-radius:8px; padding: 10px 14px; font-size:13px; color:#92400e; margin-top: 16px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>🏬 {esc(meta.get("shop_name",""))} · 手机端装修方案</h1>
  <div class="sub">生成时间 {esc(meta.get("generated_at",""))} · {esc(meta.get("note",""))}</div>

  <h2>方案摘要</h2>
  <div class="cards">
    <div class="card"><b>视觉风格</b><div class="val">{esc(design.get("style",""))}</div>
      <div class="val" style="color:#6b7280;font-size:12px">{esc(design.get("style_keywords",""))}</div></div>
    <div class="card"><b>主色</b><div class="val">{color_block(colors["primary"])}</div></div>
    <div class="card"><b>辅色</b><div class="val">{sec_sw}</div></div>
    <div class="card"><b>目标人群</b><div class="val">{esc(meta.get("target_audience",""))}</div></div>
    {f'<div class="card"><b>头图文案</b><div class="val">{banner_text_html}</div></div>' if bt else ''}
  </div>

  <h2>手机端效果预览</h2>
  <div class="phones">
    <div><h3>📱 首页</h3>{phone_home}</div>
    <div><h3>📄 详情页</h3>{phone_detail}</div>
  </div>

  <h2>模块清单</h2>
  {mod_home}
  {mod_detail}

  <h2>素材清单（AI 生图）</h2>
  {assets_html}

  <div class="note">⚠️ 请确认以上方案；确认后进入素材生成与自动装修阶段。所有素材尺寸基于 750px 设计稿，发布操作需另行确认。</div>
</div>
</body>
</html>
"""
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"✅ 装修方案已生成: {args.output}")
    print(f"   首页模块 {len(spec['homepage']['modules'])} 个 | 详情页模块 {len(spec['detail']['modules'])} 个 | 素材 {len(spec['assets'])} 张")


if __name__ == "__main__":
    main()
