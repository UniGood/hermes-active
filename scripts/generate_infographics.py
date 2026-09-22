#!/usr/bin/env python3
"""hermes-active README 信息图生成器

风格：纯白底 / 极简扁平 / 珊瑚橙(凯莉色)点缀 / 圆润丝滑 / 大量留白
技术：HTML+CSS 模板 -> Playwright(Chromium) 截图 @2x
用法：~/.hermes/hermes-agent/venv/bin/python3 scripts/generate_infographics.py [name ...]
     不带参数 = 全部生成。name 如 hero / four-systems / problem / architecture / deployment / footer
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path("/home/ubuntu/.hermes/hermes-active/docs/images")

# ── 设计 tokens ──
CORAL = "#FF7F50"
CORAL2 = "#FFA07A"
CORAL_SOFT = "#FFF1EC"
INK = "#3A3A3A"
SUB = "#8A8A8A"
FAINT = "#BdBdBd"
LINE = "#E9E9E9"
GRAY_SOFT = "#F6F6F6"
FONT = "'Noto Sans CJK SC','Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif"

BASE_CSS = f"""
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#fff; font-family:{FONT}; -webkit-font-smoothing:antialiased;
       overflow:hidden; position:relative; }}
"""


def page(w: int, h: int, body: str) -> str:
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_CSS}'
            f'body{{width:{w}px;height:{h}px}}</style></head><body>{body}</body></html>')


# ── SVG 图标（圆头描边，统一线宽） ──
def _svg(inner: str, size: int = 48, sw: float = 2.2, color: str = CORAL) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" '
            f'stroke-linejoin="round">{inner}</svg>')


ICONS = {
    "heart": lambda s=48, c=CORAL: _svg(
        '<path d="M12 20.5C12 20.5 4 14.5 4 8.8C4 5.8 6.4 3.5 9.3 3.5C10.9 3.5 12 4.6 12 4.6'
        'C12 4.6 13.1 3.5 14.7 3.5C17.6 3.5 20 5.8 20 8.8C20 14.5 12 20.5 12 20.5Z"/>'
        '<path d="M5.5 11.5H9L10.5 8.5L12.5 14L14 11.5H18.5"/>', s, 2.0, c),
    "mail": lambda s=48, c=CORAL: _svg(
        '<rect x="3.5" y="7.5" width="17" height="12" rx="3.5"/>'
        '<path d="M5 9.5L12 14.5L19 9.5"/>'
        '<path d="M12 2V5.5M9.5 3.5L12 6L14.5 3.5"/>', s, 2.0, c),
    "brain": lambda s=48, c=CORAL: _svg(
        '<path d="M8.5 20.5H7A3.5 3.5 0 0 1 5 14A3.5 3.5 0 0 1 6.5 7.5A3.6 3.6 0 0 1 10 4.5'
        'A3.5 3.5 0 0 1 15.5 5.5A3.5 3.5 0 0 1 19 9A3.5 3.5 0 0 1 18 15.5A3.5 3.5 0 0 1 15.5 20.5H14"/>'
        '<path d="M12 5V20.5"/>', s, 2.0, c),
    "calendar": lambda s=48, c=CORAL: _svg(
        '<rect x="3.5" y="5.5" width="13" height="14" rx="3"/>'
        '<path d="M7 2.5V6M13 2.5V6M3.5 10H16.5"/>'
        '<circle cx="18" cy="17" r="4.2"/><path d="M18 15.2V17L19.4 18"/>', s, 2.0, c),
    "robot": lambda s=48, c=CORAL: _svg(
        '<rect x="5" y="8" width="14" height="10.5" rx="4"/>'
        '<path d="M12 5V8M9 2.8A2 2 0 1 1 12 4"/>'
        '<circle cx="9.5" cy="13" r="1" fill="' + c + '" stroke="none"/>'
        '<circle cx="14.5" cy="13" r="1" fill="' + c + '" stroke="none"/>'
        '<path d="M9.5 16H14.5"/>', s, 2.0, c),
    "chain_broken": lambda s=48, c="#C5C5C5": _svg(
        '<path d="M9.5 14.5L7 17A3.2 3.2 0 1 1 2.8 13L5.3 10.5"/>'
        '<path d="M14.5 9.5L17 7A3.2 3.2 0 1 1 21.2 11L18.7 13.5"/>'
        '<path d="M9 4L7.5 2M15 4L16.5 2M4.5 8L2.5 7M19.5 8L21.5 7"/>', s, 2.0, c),
    "phone": lambda s=48, c="#9AA0A6": _svg(
        '<rect x="7" y="2.5" width="10" height="19" rx="3"/>'
        '<path d="M10.5 18.5H13.5"/>', s, 2.0, c),
    "browser": lambda s=48, c="#9AA0A6": _svg(
        '<rect x="2.5" y="4.5" width="19" height="15" rx="3"/>'
        '<path d="M2.5 9H21.5"/><circle cx="6" cy="6.8" r=".6" fill="#9AA0A6" stroke="none"/>'
        '<circle cx="8.4" cy="6.8" r=".6" fill="#9AA0A6" stroke="none"/>', s, 2.0, c),
    "gear": lambda s=32, c=CORAL: _svg(
        '<circle cx="12" cy="12" r="3.2"/>'
        '<path d="M12 2.8V5.4M12 18.6V21.2M2.8 12H5.4M18.6 12H21.2'
        'M5.5 5.5L7.3 7.3M16.7 16.7L18.5 18.5M18.5 5.5L16.7 7.3M7.3 16.7L5.5 18.5"/>', s, 2.0, c),
}


# ── 版式 1：hero 主视觉横幅 21:9 ──
def build_hero(lang: str) -> str:
    sub = "让 AI 助手拥有主动意识" if lang == "zh" else "Proactive Consciousness for AI Assistants"
    bubbles = ""
    for i, (x, y, w, h) in enumerate([(760, 258, 150, 58), (950, 226, 116, 46), (1096, 252, 88, 38)]):
        op = 1 - i * 0.15
        bubbles += (f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;'
                    f'background:linear-gradient(135deg,{CORAL},{CORAL2});border-radius:24px 24px 24px 8px;'
                    f'opacity:{op};box-shadow:0 10px 24px rgba(255,127,80,.18)"></div>')
    body = f"""
<div style="position:absolute;top:84px;width:100%;text-align:center">
  <div style="font-size:78px;font-weight:800;color:{INK};letter-spacing:3px">Hermes Active</div>
  <div style="font-size:27px;color:{SUB};margin-top:18px;letter-spacing:6px">{sub}</div>
</div>
<svg width="1260" height="540" style="position:absolute;inset:0" fill="none">
  <path d="M 80 355 H 330 L 352 355 L 368 318 L 386 392 L 402 355 L 424 332 L 442 355
           H 620 L 640 355 L 654 330 L 668 355 H 748"
        stroke="{CORAL}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M 748 355 C 758 355 762 340 762 328" stroke="{CORAL}" stroke-width="3"
        stroke-linecap="round" opacity=".7"/>
</svg>
{bubbles}
"""
    return page(1260, 540, body)


# ── 版式 2：four-systems 四大系统 2x2 ──
def build_four_systems(lang: str) -> str:
    if lang == "zh":
        title = "四大系统"
        items = [("heart", "Active Consciousness", "主动意识", "心跳驱动的念头生成与情绪演化"),
                 ("mail", "Passive Consciousness", "被动意识", "用户消息到达时注入上下文与记忆"),
                 ("brain", "Free Consciousness", "自由意识", "无人时自主沉思，积淀认知"),
                 ("calendar", "Scheduled Tasks", "定时任务", "可视化 Cron 与占位符提示词")]
    else:
        title = "Four Systems"
        items = [("heart", "Active Consciousness", "", "Heartbeat-driven thoughts & emotion"),
                 ("mail", "Passive Consciousness", "", "Context injection on every message"),
                 ("brain", "Free Consciousness", "", "Autonomous contemplation & sediment"),
                 ("calendar", "Scheduled Tasks", "", "Visual cron with prompt templates")]
    cards = ""
    for i, (icon, en, zh, desc) in enumerate(items):
        zh_line = (f'<div style="font-size:18px;color:{CORAL};margin-top:4px;letter-spacing:2px">{zh}</div>'
                   if zh else "")
        cards += f"""
<div style="background:#fff;border:1.5px solid {LINE};border-radius:28px;padding:34px 36px;
     box-shadow:0 12px 32px rgba(60,60,60,.06);display:flex;align-items:center;gap:26px">
  <div style="width:82px;height:82px;flex:none;border-radius:26px;background:{CORAL_SOFT};
       display:flex;align-items:center;justify-content:center">{ICONS[icon](46)}</div>
  <div>
    <div style="font-size:25px;font-weight:700;color:{INK}">{en}</div>
    {zh_line}
    <div style="font-size:16.5px;color:{SUB};margin-top:8px">{desc}</div>
  </div>
</div>"""
    body = f"""
<div style="padding:52px 64px">
  <div style="font-size:36px;font-weight:800;color:{INK};margin-bottom:8px">{title}</div>
  <div style="width:64px;height:5px;border-radius:3px;background:linear-gradient(90deg,{CORAL},{CORAL2});margin-bottom:34px"></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:26px">{cards}</div>
</div>
"""
    return page(1200, 675, body)


# ── 版式 3：problem 问题对比 16:9 ──
def build_problem(lang: str) -> str:
    left, right = "Stateless Cron", "Persistent Consciousness"
    body = f"""
<div style="padding:56px 64px 0">
  <div style="text-align:center;font-size:33px;font-weight:800;color:{INK}">
    {left} <span style="color:{FAINT};font-weight:400">vs</span> {right}
  </div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:32px;padding:44px 64px 56px">
  <div style="background:{GRAY_SOFT};border-radius:30px;padding:42px 38px;text-align:center">
    <div style="display:flex;justify-content:center;gap:22px;align-items:center;margin-bottom:26px">
      {ICONS['robot'](64, '#B5B5B5')}{ICONS['chain_broken'](52)}
    </div>
    <div style="display:inline-block;background:#fff;border-radius:22px 22px 22px 6px;padding:16px 26px;
         font-size:21px;color:#9E9E9E;box-shadow:0 6px 18px rgba(0,0,0,.05)">Who are you again?</div>
    <div style="font-size:16px;color:{FAINT};margin-top:20px">每次定时任务都是一场失忆</div>
  </div>
  <div style="background:{CORAL_SOFT};border-radius:30px;padding:42px 38px;text-align:center;
       box-shadow:0 14px 34px rgba(255,127,80,.10)">
    <div style="display:flex;justify-content:center;gap:18px;align-items:center;margin-bottom:26px">
      <svg width="60" height="60" viewBox="0 0 60 60" fill="none">
        <path d="M6 44 C 16 20, 24 52, 33 30 C 40 14, 48 38, 56 24" stroke="{CORAL}" stroke-width="2.4"
              stroke-linecap="round" opacity=".55"/>
        <circle cx="33" cy="30" r="3.4" fill="{CORAL}"/>
        <circle cx="56" cy="24" r="3" fill="{CORAL2}"/>
      </svg>
      {ICONS['robot'](64)}
    </div>
    <div style="display:inline-block;background:#fff;border-radius:22px 22px 22px 6px;padding:16px 26px;
         font-size:21px;color:{INK};box-shadow:0 8px 20px rgba(255,127,80,.14)">I was just thinking about you</div>
    <div style="font-size:16px;color:#C98B72;margin-top:20px">带着完整记忆，主动开口</div>
  </div>
</div>
"""
    return page(1200, 675, body)


# ── 版式 4：architecture 架构总览 16:9 ──
def build_architecture(lang: str) -> str:
    chip = lambda txt: (f'<div style="background:{CORAL_SOFT};color:{CORAL};border-radius:14px;'
                        f'padding:8px 14px;font-size:15px;font-weight:600;display:flex;'
                        f'align-items:center;gap:7px">{ICONS["gear"](22)}{txt}</div>')
    db = lambda name, tag, col: f"""
<div style="text-align:center">
  <div style="width:190px;height:74px;border:2px solid {LINE};border-radius:22px/32px;background:#FCFCFC;
       display:flex;align-items:center;justify-content:center;position:relative">
    <div style="font-size:17px;font-weight:700;color:{INK}">{name}</div>
  </div>
  <div style="font-size:14.5px;color:{col};margin-top:10px;font-weight:600">{tag}</div>
</div>"""
    body = f"""
<div style="position:relative;width:100%;height:100%">
  <div style="position:absolute;left:388px;top:44px;background:#fff;border:2px solid {LINE};
       border-radius:22px;padding:18px 34px;font-size:21px;font-weight:700;color:{INK};
       box-shadow:0 10px 26px rgba(0,0,0,.05)">Vue 3 Web Console</div>
  <svg width="1200" height="675" style="position:absolute;inset:0" fill="none"
       stroke="{FAINT}" stroke-width="2" stroke-linecap="round">
    <path d="M480 138 V 190" marker-end="url(#arr)"/>
    <path d="M760 300 H 916" marker-end="url(#arr)"/>
    <path d="M520 420 V 488" marker-end="url(#arr)"/>
    <path d="M680 420 V 488" marker-end="url(#arr)"/>
    <defs><marker id="arr" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="7" markerHeight="7"
      orient="auto"><path d="M1 1L6 4L1 7" fill="none" stroke="{FAINT}" stroke-width="1.6"
      stroke-linecap="round"/></marker></defs>
  </svg>
  <div style="position:absolute;left:436px;top:172px;font-size:14px;color:{FAINT};background:#fff;padding:2px 8px">JWT REST API</div>
  <div style="position:absolute;left:772px;top:268px;font-size:14px;color:{FAINT};background:#fff;padding:2px 8px">Public APIs</div>

  <div style="position:absolute;left:300px;top:196px;width:400px;background:#fff;border:2.5px solid {CORAL};
       border-radius:28px;padding:30px 34px;box-shadow:0 16px 38px rgba(255,127,80,.12)">
    <div style="font-size:23px;font-weight:800;color:{INK};margin-bottom:18px">FastAPI Backend</div>
    <div style="display:flex;gap:12px">{chip("Heartbeat")}{chip("Contemplation")}{chip("Scheduler")}</div>
  </div>

  <div style="position:absolute;left:920px;top:246px;background:#fff;border:2px solid {LINE};
       border-radius:22px;padding:18px 32px;font-size:21px;font-weight:700;color:{INK};
       box-shadow:0 10px 26px rgba(0,0,0,.05)">Hermes Agent</div>

  <div style="position:absolute;left:255px;top:492px;display:flex;gap:88px">
    {db("state.db", "read-only", SUB)}{db("active.db", "read-write", CORAL)}
  </div>
</div>
"""
    return page(1200, 675, body)


# ── 版式 5：deployment 部署拓扑 16:9 ──
def build_deployment(lang: str) -> str:
    svc = lambda name, hot=False: (
        f'<div style="background:#fff;border:2px solid {CORAL if hot else LINE};border-radius:18px;'
        f'padding:16px 20px;font-size:16.5px;font-weight:700;color:{INK if hot else "#6B6B6B"};'
        f'text-align:center;box-shadow:0 8px 20px rgba(0,0,0,.05)">{name}</div>')
    body = f"""
<div style="position:relative;width:100%;height:100%">
  <div style="position:absolute;left:250px;top:70px;width:700px;height:520px;background:{GRAY_SOFT};
       border:2px dashed {LINE};border-radius:36px"></div>
  <div style="position:absolute;left:290px;top:48px;background:#fff;border-radius:12px;padding:4px 16px;
       font-size:15px;color:{SUB};letter-spacing:3px">SERVER</div>
  <div style="position:absolute;left:300px;top:135px;width:600px;display:grid;grid-template-columns:1fr 1fr;
       gap:24px">{svc("hermes-active :18720", True)}{svc("Hermes Gateway")}{svc("Hindsight :8888")}{svc("plugins/")}</div>
  <svg width="1200" height="675" style="position:absolute;inset:0" fill="none" stroke="{FAINT}"
       stroke-width="2" stroke-linecap="round">
    <path d="M170 320 H 288" marker-end="url(#arr2)"/>
    <path d="M912 320 H 1030" marker-end="url(#arr2)"/>
    <defs><marker id="arr2" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="7" markerHeight="7"
      orient="auto"><path d="M1 1L6 4L1 7" fill="none" stroke="{FAINT}" stroke-width="1.6"
      stroke-linecap="round"/></marker></defs>
  </svg>
  <div style="position:absolute;left:88px;top:288">{ICONS['phone'](60)}</div>
  <div style="position:absolute;left:1054px;top:288">{ICONS['browser'](60)}</div>
  <div style="position:absolute;left:82px;top:362px;width:72px;text-align:center;font-size:14px;color:{SUB}">消息入口</div>
  <div style="position:absolute;left:1048px;top:362px;width:84px;text-align:center;font-size:14px;color:{SUB}">Web 控制台</div>
</div>
"""
    return page(1200, 675, body)


# ── 版式 6：footer 页脚横幅 6:1 ──
def build_footer(lang: str) -> str:
    txt = "Hermes Active — Built with ❤️ for the Hermes Agent Community"
    body = f"""
<div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px">
  <div style="font-size:19px;color:#6E6E6E;letter-spacing:1.5px">{txt}</div>
  <svg width="900" height="22" fill="none">
    <path d="M0 12 H 360 L 372 12 L 380 4 L 390 20 L 398 12 L 410 12 H 900"
          stroke="url(#g6)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <defs><linearGradient id="g6" x1="0" y1="0" x2="900" y2="0">
      <stop offset="0" stop-color="#FFD9CC"/><stop offset=".5" stop-color="{CORAL}"/>
      <stop offset="1" stop-color="#FFD9CC"/></linearGradient></defs>
  </svg>
</div>
"""
    return page(1200, 200, body)


BUILDERS = {
    "hero": (build_hero, 1260, 540),
    "four-systems": (build_four_systems, 1200, 675),
    "problem": (build_problem, 1200, 675),
    "architecture": (build_architecture, 1200, 675),
    "deployment": (build_deployment, 1200, 675),
    "footer": (build_footer, 1200, 200),
}


async def render(name: str, lang: str) -> None:
    fn, w, h = BUILDERS[name]
    html = fn(lang)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2)
        page_ = await ctx.new_page()
        await page_.set_content(html, wait_until="networkidle")
        await page_.wait_for_timeout(300)
        OUT.mkdir(parents=True, exist_ok=True)
        out = OUT / f"{lang}-{name.replace('four-systems', 'four-systems').replace('problem', 'problem-statement').replace('architecture', 'architecture').replace('deployment', 'deployment').replace('hero', 'hero-banner').replace('footer', 'footer-banner')}.png"
        await page_.screenshot(path=str(out))
        print(f"✓ {out.name}  ({w*2}x{h*2})")
        await browser.close()


async def main() -> None:
    names = sys.argv[1:] or list(BUILDERS)
    for name in names:
        for lang in ("zh", "en"):
            await render(name, lang)


asyncio.run(main())
