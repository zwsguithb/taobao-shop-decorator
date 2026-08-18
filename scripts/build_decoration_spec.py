#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_decoration_spec.py — 淘宝店铺装修：需求 JSON → 装修规格 JSON

用法:
    python build_decoration_spec.py --input requirements.json --output decoration_spec.json

输入 requirements.json（所有字段可选，缺失自动用默认值）:
{
  "shop_name": "XX旗舰店",
  "style": "简约 | 潮酷 | 母婴 | 美妆 | 食品 | 家居 | 数码 | 节日营销",
  "color_scheme": {"primary": "#1F2937", "secondary": ["#4B5563", "#E5E7EB"]},
  "target_audience": "年轻白领",
  "banner_text": {"main": "主标题", "sub": "副标题", "cta": "立即抢购"},
  "products": [{"name": "商品名", "price": "¥499", "link": ""}],
  "product_groups": ["新品", "热卖", "清仓"],
  "promotions": [{"type": "优惠券|满减|限时", "title": "活动名", "detail": "规则说明"}],
  "detail_scope": "全部|关联推荐|图文排版"
}

输出 decoration_spec.json:
  meta / design / homepage.modules / detail.modules / assets
  assets 中每项含 id、type、size、purpose、prompt(生图用)
"""

import argparse
import json
import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# 风格默认值（与 references/design-system.md 保持一致）
# ---------------------------------------------------------------------------
STYLE_DEFAULTS = {
    "简约": {
        "primary": "#1F2937",
        "secondary": ["#4B5563", "#E5E7EB"],
        "keywords": "极简现代风，大留白，细线条，干净利落",
        "scene": "干净整洁的电商氛围",
    },
    "潮酷": {
        "primary": "#111111",
        "secondary": ["#39FF14", "#FFFFFF"],
        "keywords": "高对比撞色，粗体字，几何拼接，街头潮流感",
        "scene": "潮流时尚的街头氛围",
    },
    "母婴": {
        "primary": "#FFB6C1",
        "secondary": ["#87CEEB", "#FFF5F7"],
        "keywords": "柔和渐变，圆角插画，温馨可爱，童趣",
        "scene": "温馨明亮的母婴场景",
    },
    "美妆": {
        "primary": "#E8A0BF",
        "secondary": ["#F7D3E0", "#FFFFFF"],
        "keywords": "渐变光感，轻奢质感，柔光滤镜，高级感",
        "scene": "精致柔美的美妆氛围",
    },
    "食品": {
        "primary": "#FF7A45",
        "secondary": ["#FFC53D", "#FFF7E6"],
        "keywords": "暖色调，食欲感，实拍质感，新鲜诱人",
        "scene": "温馨暖调的食欲氛围",
    },
    "家居": {
        "primary": "#8B9D83",
        "secondary": ["#D9C7B2", "#F5F1EB"],
        "keywords": "低饱和自然色，生活化场景，质感软装",
        "scene": "温馨自然的生活方式场景",
    },
    "数码": {
        "primary": "#0F172A",
        "secondary": ["#38BDF8", "#E2E8F0"],
        "keywords": "深色背景，科技感光效，简洁线条，未来感",
        "scene": "科技感十足的数码氛围",
    },
    "节日营销": {
        "primary": "#E60012",
        "secondary": ["#FFD700", "#FFF5F0"],
        "keywords": "节日元素，氛围光效，喜庆热烈",
        "scene": "节日促销的喜庆氛围",
    },
}

# 素材类型 -> (尺寸, 用途说明)
ASSET_SPECS = {
    "banner": ("750x420", "店铺头图 Banner（首页顶部主视觉）"),
    "carousel": ("750x420", "轮播图（每张一图，建议 3-5 张成套）"),
    "nav": ("150x150", "导航图标（含文字，一行 4-5 个）"),
    "promo": ("750x400", "营销活动海报"),
    "coupon": ("750x300", "优惠券展示图"),
    "product": ("750x750", "商品主图（方图）"),
    "detail_long": ("750x1500", "详情页长图（单段建议 ≤1500px 高）"),
    "service": ("120x120", "客服入口图标"),
}

NEGATIVE_PROMPT = "无其他品牌Logo，无明星肖像，无水印，无乱码文字，无多余元素"


# ---------------------------------------------------------------------------
# 默认需求
# ---------------------------------------------------------------------------
def default_requirements():
    return {
        "shop_name": "我的店铺",
        "style": "简约",
        "target_audience": "全人群",
        "banner_text": {"main": "品牌主视觉", "sub": "", "cta": ""},
        "products": [],
        "product_groups": ["新品", "热卖", "清仓"],
        "promotions": [],
        "detail_scope": "全部",
    }


def merge_requirements(raw):
    """合并用户输入与默认值，缺失字段用默认。"""
    base = default_requirements()
    if not raw:
        return base
    for k, v in raw.items():
        if v is not None:
            base[k] = v
    # banner_text 子字段合并
    bt = dict(base["banner_text"])
    raw_bt = raw.get("banner_text") or {}
    for k, v in raw_bt.items():
        if v is not None:
            bt[k] = v
    base["banner_text"] = bt
    # color_scheme 显式提供则优先
    if raw.get("color_scheme") and isinstance(raw["color_scheme"], dict):
        base["color_scheme"] = raw["color_scheme"]
    return base


# ---------------------------------------------------------------------------
# 规格构建
# ---------------------------------------------------------------------------
def build_spec(req, templates_dir):
    style = req.get("style", "简约")
    if style not in STYLE_DEFAULTS:
        print(f"[warn] 未知风格 '{style}'，回退为 '简约'", file=sys.stderr)
        style = "简约"
    sd = STYLE_DEFAULTS[style]
    cs = req.get("color_scheme") or {"primary": sd["primary"], "secondary": sd["secondary"]}

    # 加载默认模板
    def load_tpl(name):
        path = os.path.join(templates_dir, name)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    home_tpl = load_tpl("homepage_default.json")["homepage"]
    detail_tpl = load_tpl("detail_default.json")["detail"]

    # ---- 填充首页模块 ----
    groups = req.get("product_groups") or ["新品", "热卖", "清仓"]
    home_modules = []
    pg_idx = 0  # 商品分组计数器（模板中可能有多个分组模块）
    for m in home_tpl["modules"]:
        m = dict(m)
        if m["type"] == "banner":
            m["title"] = f"{req['shop_name']} 主视觉"
        elif m["type"] == "nav":
            labels = ["新品", "热卖", "优惠券", "客服"]
            if len(groups) >= 2:
                labels = groups[:2] + ["优惠券", "客服"]
            m["items"] = [{"label": lb, "icon": f"nav_{i+1:02d}.png", "link": ""}
                          for i, lb in enumerate(labels[:5])]
        elif m["type"] == "carousel":
            n = max(3, min(5, len(req.get("promotions", [])) + 2))
            m["images"] = [f"carousel_{i+1:02d}.png" for i in range(n)]
            m["links"] = [""] * n
        elif m["type"] == "coupon":
            promo = next((p for p in req.get("promotions", [])
                          if p.get("type") in ("优惠券", "满减")), None)
            m["title_text"] = promo["title"] if promo else ""
            m["coupon_id"] = ""
        elif m["type"] == "promo":
            promo = next((p for p in req.get("promotions", [])
                          if p.get("type") in ("限时", "活动")), None)
            m["title"] = promo["title"] if promo else "限时活动"
        elif m["type"] == "product_group":
            if pg_idx < len(groups):
                m["group_query"] = groups[pg_idx]
                m["title"] = groups[pg_idx]
            m["products"] = req.get("products", [])
            pg_idx += 1
        home_modules.append(m)
    # 商品分组标题去重处理
    seen = set()
    deduped = []
    for m in home_modules:
        if m["type"] == "product_group":
            key = m.get("group_query", "")
            if key in seen:
                continue
            seen.add(key)
        deduped.append(m)
    home_modules = deduped

    # ---- 填充详情页模块 ----
    detail_scope = req.get("detail_scope", "全部")
    detail_modules = []
    for m in detail_tpl["modules"]:
        m = dict(m)
        if m["type"] == "related" and detail_scope == "图文排版":
            continue
        if m["type"] == "custom" and detail_scope == "关联推荐":
            continue
        if m["type"] == "promo":
            # 详情页海报优先用非券类活动（限时/满减/活动），避免与优惠券标题重复
            promo = next((p for p in req.get("promotions", [])
                          if p.get("type") not in ("优惠券",)), None)
            promo = promo or next(iter(req.get("promotions", [])), None)
            m["title"] = promo["title"] if promo else "营销海报"
        if m["type"] == "related":
            m["products"] = req.get("products", [])[:8]
        detail_modules.append(m)

    # ---- 素材清单 ----
    bt = req["banner_text"]
    assets = []
    assets.append({
        "id": "banner_main.png", "type": "banner",
        "size": ASSET_SPECS["banner"][0], "purpose": ASSET_SPECS["banner"][1],
        "prompt": build_prompt(sd, cs, "手机店铺首页 Banner，主标题文案：" + (bt["main"] or "店铺主视觉") +
                               (("，副标题：" + bt["sub"]) if bt.get("sub") else "")),
    })
    carousel_meta = next((m for m in home_modules if m["type"] == "carousel"), None)
    if carousel_meta:
        for i, img in enumerate(carousel_meta["images"], 1):
            assets.append({
                "id": img, "type": "carousel",
                "size": ASSET_SPECS["carousel"][0], "purpose": f"轮播图 第{i}张",
                "prompt": build_prompt(sd, cs, f"淘宝店铺轮播图 第{i}张，中央留白，无文字"),
            })
    nav_meta = next((m for m in home_modules if m["type"] == "nav"), None)
    if nav_meta:
        for item in nav_meta["items"]:
            assets.append({
                "id": item["icon"], "type": "nav",
                "size": ASSET_SPECS["nav"][0], "purpose": f"导航图标：{item['label']}",
                "prompt": build_prompt(sd, cs, f"圆形图标底，文字区域预留，导航项：{item['label']}，简洁图标风格"),
            })
    promo_meta = next((m for m in home_modules if m["type"] == "promo"), None)
    if promo_meta:
        assets.append({
            "id": "promo_01.png", "type": "promo",
            "size": ASSET_SPECS["promo"][0], "purpose": "首页营销活动海报",
            "prompt": build_prompt(sd, cs, "营销活动海报，大字促销氛围，中央留白放文案：" + promo_meta["title"]),
        })
    for m in detail_modules:
        if m["type"] == "custom":
            assets.append({
                "id": m.get("image", "detail_custom.png"), "type": "detail_long",
                "size": ASSET_SPECS["detail_long"][0], "purpose": f"详情页图文区块：{m['title']}",
                "prompt": build_prompt(sd, cs, f"详情页长图区块：{m['title']}，信息图排版感，无文字"),
            })
        elif m["type"] == "promo":
            assets.append({
                "id": m.get("image", "detail_promo.png"), "type": "promo",
                "size": ASSET_SPECS["promo"][0], "purpose": "详情页营销海报",
                "prompt": build_prompt(sd, cs, "详情页营销海报，促销氛围，中央留白"),
            })

    spec = {
        "meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "shop_name": req["shop_name"],
            "style": style,
            "target_audience": req.get("target_audience", ""),
            "note": "由 build_decoration_spec.py 自动生成，作为后续方案/素材/执行的单一事实来源",
        },
        "design": {
            "style": style,
            "style_keywords": sd["keywords"],
            "colors": {"primary": cs["primary"], "secondary": cs["secondary"]},
            "banner_text": bt,
        },
        "homepage": {"modules": home_modules},
        "detail": {"modules": detail_modules},
        "assets": assets,
    }
    return spec


def build_prompt(sd, cs, subject):
    """按设计规范拼装 AI 生图 prompt。"""
    colors = cs["primary"] + " 为主色，" + "、".join(cs["secondary"][:2]) + " 为辅色"
    return (f"{subject}；{sd['scene']}；{sd['keywords']}；"
            f"配色：{colors}；高清电商主图风格；{NEGATIVE_PROMPT}")


def main():
    ap = argparse.ArgumentParser(description="生成淘宝手机店铺装修规格 JSON")
    ap.add_argument("--input", default="requirements.json", help="需求 JSON 路径")
    ap.add_argument("--output", default="decoration_spec.json", help="输出规格 JSON 路径")
    ap.add_argument("--templates-dir", default=None,
                    help="模板目录（默认取脚本同级 ../assets/templates）")
    args = ap.parse_args()

    templates_dir = args.templates_dir or os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "templates"))

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        print(f"[warn] 未找到 {args.input}，使用全部默认需求", file=sys.stderr)
        raw = {}
    except json.JSONDecodeError as e:
        print(f"[error] 需求 JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    req = merge_requirements(raw)
    spec = build_spec(req, templates_dir)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

    n_assets = len(spec["assets"])
    n_home = len(spec["homepage"]["modules"])
    n_detail = len(spec["detail"]["modules"])
    print(f"✅ 装修规格已生成: {args.output}")
    print(f"   风格: {req['style']} | 主色: {spec['design']['colors']['primary']}")
    print(f"   首页模块: {n_home} 个 | 详情页模块: {n_detail} 个 | 素材: {n_assets} 张")
    print(f"   素材清单已含 AI 生图 prompt（字段 assets[].prompt）")


if __name__ == "__main__":
    main()
