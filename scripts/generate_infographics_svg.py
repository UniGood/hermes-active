#!/usr/bin/env python3
"""hermes-active README 信息图生成器（SVG 版）

直接生成矢量 SVG 供 README 引用。
布局原则：元素填满画布、间距统一、viewBox 紧贴内容（告别松散）。
字体/箭头：加深加大的实心圆角箭头、统一字重层次、Helvetica Neue + 思源黑体栈。
用法：~/.hermes/hermes-agent/venv/bin/python3 scripts/generate_infographics_svg.py [name ...]
     name: hero problem architecture four-systems deployment footer
"""
import asyncio
import sys
from pathlib import Path

IMG = Path("/home/ubuntu/.hermes/hermes-active/docs/images")
PREVIEW_DIR = Path("/tmp/infographic-preview")

INK = "#3A3A3A"
SUB = "#838383"
FAINT = "#B4B4B4"
LINE = "#E4E4E4"
WIRE = "#8F8F8F"
CORAL = "#FF7F50"
CORAL2 = "#FFA07A"
CORAL_SOFT = "#FFF1EC"
GRAY_SOFT = "#F7F7F7"
FONT = "'Helvetica Neue','PingFang SC','Noto Sans CJK SC','Microsoft YaHei',Arial,sans-serif"

FILE_SUFFIX = {
    "hero": "hero-banner", "problem": "problem-statement",
    "architecture": "architecture", "four-systems": "four-systems",
    "deployment": "deployment", "footer": "footer-banner",
}


def svg_open(w: int, h: int, vb: str = "", extra_defs: str = "") -> str:
    box = vb or f"0 0 {w} {h}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{box}">
<defs>
  <filter id="sh" x="-20%" y="-20%" width="140%" height="150%">
    <feDropShadow dx="0" dy="3.5" stdDeviation="6" flood-color="#000" flood-opacity="0.08"/>
  </filter>
  <marker id="ar" viewBox="0 0 10 10" refX="7.2" refY="5" markerWidth="10.5" markerHeight="10.5" orient="auto">
    <path d="M0.8 1.2 L8.6 5 L0.8 8.8 z" fill="{WIRE}" stroke="#fff" stroke-width="1.3" stroke-linejoin="round"/>
  </marker>
  <linearGradient id="bub" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{CORAL}"/><stop offset="1" stop-color="{CORAL2}"/>
  </linearGradient>
  <linearGradient id="rib" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#FFD9CC"/><stop offset=".5" stop-color="{CORAL}"/>
    <stop offset="1" stop-color="#FFD9CC"/>
  </linearGradient>
  {extra_defs}
</defs>
<rect width="{w}" height="{h}" fill="#fff"/>
'''


def card(x, y, w, h, rx=18, stroke=LINE, sw=2, fill="#fff", shadow=True):
    f = ' filter="url(#sh)"' if shadow else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{f}/>')


def text(x, y, s, size=16.0, fill=INK, bold=False, anchor="middle", ls=0.0, weight="", raw=False):
    wt = weight or ('700' if bold else '400')
    lsp = f' letter-spacing="{ls}"' if ls else ""
    body = s if raw else s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{wt}"{lsp} '
            f'fill="{fill}" text-anchor="{anchor}" dominant-baseline="central">{body}</text>')


def wire(x1, y1, x2, y2):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{WIRE}" '
            f'stroke-width="2.6" stroke-linecap="round" marker-end="url(#ar)"/>')


def icon(inner: str, x, y, size, color=CORAL, sw=2.0) -> str:
    k = size / 24
    return (f'<g transform="translate({x},{y}) scale({k:.4f})" fill="none" stroke="{color}" '
            f'stroke-width="{sw / k:.2f}" stroke-linecap="round" stroke-linejoin="round">{inner}</g>')


# ── 图标 path（24 viewBox，圆头描边） ──
P_HEART = ('<path d="M12 20.5C12 20.5 4 14.5 4 8.8C4 5.8 6.4 3.5 9.3 3.5C10.9 3.5 12 4.6 12 4.6'
           'C12 4.6 13.1 3.5 14.7 3.5C17.6 3.5 20 5.8 20 8.8C20 14.5 12 20.5 12 20.5Z"/>'
           '<path d="M5.5 11.5H9L10.5 8.5L12.5 14L14 11.5H18.5"/>')
P_MAIL = ('<rect x="3.5" y="7.5" width="17" height="12" rx="3.5"/><path d="M5 9.5L12 14.5L19 9.5"/>'
          '<path d="M12 2V5.5M9.5 3.5L12 6L14.5 3.5"/>')
P_BRAIN = ('<path d="M8.5 20.5H7A3.5 3.5 0 0 1 5 14A3.5 3.5 0 0 1 6.5 7.5A3.6 3.6 0 0 1 10 4.5'
           'A3.5 3.5 0 0 1 15.5 5.5A3.5 3.5 0 0 1 19 9A3.5 3.5 0 0 1 18 15.5A3.5 3.5 0 0 1 15.5 20.5H14"/>'
           '<path d="M12 5V20.5"/>')
P_CAL = ('<rect x="3.5" y="5.5" width="13" height="14" rx="3"/><path d="M7 2.5V6M13 2.5V6M3.5 10H16.5"/>'
         '<circle cx="18" cy="17" r="4.2"/><path d="M18 15.2V17L19.4 18"/>')
P_ROBOT = ('<rect x="5" y="8" width="14" height="10.5" rx="4"/><path d="M12 5V8M9 2.8A2 2 0 1 1 12 4"/>'
           '<circle cx="9.5" cy="13" r="1" fill="COLOR" stroke="none"/>'
           '<circle cx="14.5" cy="13" r="1" fill="COLOR" stroke="none"/><path d="M9.5 16H14.5"/>')
P_CHAIN = ('<path d="M9.5 14.5L7 17A3.2 3.2 0 1 1 2.8 13L5.3 10.5"/>'
           '<path d="M14.5 9.5L17 7A3.2 3.2 0 1 1 21.2 11L18.7 13.5"/>'
           '<path d="M9 4L7.5 2M15 4L16.5 2M4.5 8L2.5 7M19.5 8L21.5 7"/>')
P_PHONE = '<rect x="7" y="2.5" width="10" height="19" rx="3"/><path d="M10.5 18.5H13.5"/>'
P_BROWSER = ('<rect x="2.5" y="4.5" width="19" height="15" rx="3"/><path d="M2.5 9H21.5"/>'
             '<circle cx="6" cy="6.8" r=".7" fill="COLOR" stroke="none"/>'
             '<circle cx="8.6" cy="6.8" r=".7" fill="COLOR" stroke="none"/>')


def robot(x, y, size, color="#B5B5B5"):
    return icon(P_ROBOT.replace("COLOR", color), x, y, size, color)


# ── 版式 1：hero 主视觉横幅 840x264（紧凑高级版） ──
def build_hero(lang: str) -> str:
    sub = "让 AI 助手拥有主动意识" if lang == "zh" else "Proactive Consciousness for AI Assistants"
    p = [svg_open(840, 264)]
    # eyebrow：小橙点 + 全大写宽字距标签（补回 Hermes Agent 归属）
    p += [text(423, 45, f'<tspan fill="{CORAL}" font-size="8">●</tspan>  BUILT FOR HERMES AGENT',
               10.5, "#B0B0B0", weight="500", ls=4, raw=True)]
    # 主标题：粗细双字重，珊瑚橙细体点睛
    p += [text(420, 99, f'Hermes<tspan font-weight="300" fill="{CORAL}"> Active</tspan>',
               46, INK, bold=True, ls=2, raw=True)]
    # 副标题
    p += [text(420, 143, sub, 16, SUB, weight="500", ls=0.8)]
    # 心跳线 -> 演变为对话气泡并渐隐（克制版，整体左移配平视觉重心）
    p += ['<g transform="translate(-26,0)">']
    p += [f'<path d="M185 199 H345 L357 199 L367 181 L379 219 L389 199 L399 189 L407 199 H525'
          f' C539 199 545 190 549 184" stroke="{CORAL}" stroke-width="2" fill="none"'
          f' stroke-linecap="round" stroke-linejoin="round"/>']
    p += [f'<rect x="553" y="173" width="44" height="22" rx="11" fill="url(#bub)"'
          f' filter="url(#sh)"/>']
    p += [f'<rect x="607" y="177" width="30" height="16" rx="8" fill="url(#bub)" opacity=".62"/>']
    p += [f'<circle cx="650" cy="183" r="3.5" fill="{CORAL2}" opacity=".5"/>']
    p += ["</g>"]
    p += ["</svg>"]
    return "\n".join(p)


# ── 版式 2：problem 问题对比 768x432 ──
def build_problem(lang: str) -> str:
    if lang == "zh":
        lcap, rcap = "每次定时任务都是一场失忆", "带着完整记忆，主动开口"
    else:
        lcap, rcap = "Every run starts from zero", "Full memory, speaks first"
    p = [svg_open(768, 432)]
    p += [text(384, 52, f'Stateless Cron <tspan fill="{FAINT}" font-weight="400">vs</tspan> '
              f'Persistent Consciousness', 24, INK, bold=True, raw=True)]
    p += [card(32, 100, 344, 296, rx=24, stroke="none", fill=GRAY_SOFT, shadow=False)]
    p += [card(392, 100, 344, 296, rx=24, stroke="none", fill=CORAL_SOFT, shadow=False)]
    # 左：失忆
    p += [robot(161, 138, 40), icon(P_CHAIN, 215, 142, 32, "#C0C0C0")]
    p += [card(79, 202, 250, 76, rx=28, fill="#fff", shadow=True)]
    p += [text(204, 240, "Who are you again?", 16.5, "#9E9E9E")]
    p += [text(204, 312, lcap, 13, FAINT, weight="500")]
    # 右：记得你
    p += [f'<path d="M515 158 C 527 132, 539 172, 551 144 C 561 122, 573 160, 585 140"'
          f' stroke="{CORAL}" stroke-width="2.4" fill="none" stroke-linecap="round" opacity=".6"/>'
          f'<circle cx="551" cy="144" r="3.4" fill="{CORAL}"/><circle cx="585" cy="140" r="3" fill="{CORAL2}"/>']
    p += [robot(599, 138, 40, CORAL)]
    p += [card(429, 202, 270, 76, rx=28, fill="#fff", shadow=True)]
    p += [text(564, 240, "I was just thinking about you", 16, INK, weight="500")]
    p += [text(564, 312, rcap, 13, "#C98B72", weight="500")]
    p += ["</svg>"]
    return "\n".join(p)


# ── 版式 3：architecture 架构总览 768x420 ──
def build_architecture(lang: str) -> str:
    p = [svg_open(768, 420, vb="64 8 768 420")]
    p += [card(180, 24, 320, 64), text(340, 56, "Vue 3 Web Console", 22, INK, bold=True)]
    p += [wire(340, 88, 340, 122), text(354, 104, "JWT REST API", 13.5, SUB, anchor="start", weight="500")]
    p += [card(80, 128, 520, 156, rx=24, stroke=CORAL, sw=3)]
    p += [text(112, 158, "FastAPI Backend", 25, INK, bold=True, anchor="start")]
    for cx, cw, name in [(112, 136, "Heartbeat"), (260, 160, "Contemplation"), (432, 136, "Scheduler")]:
        p += [f'<rect x="{cx}" y="196" width="{cw}" height="50" rx="25" fill="{CORAL_SOFT}"/>']
        p += [text(cx + cw // 2, 221, name, 15.5, CORAL, bold=True)]
    p += [wire(600, 206, 636, 206), text(634, 184, "Public APIs", 13.5, SUB, anchor="end", weight="500")]
    p += [card(640, 170, 176, 72), text(728, 206, "Hermes Agent", 21, INK, bold=True)]
    p += [wire(230, 284, 230, 324), wire(450, 284, 450, 324)]
    p += [card(140, 330, 180, 82), text(230, 360, "state.db", 21, INK, bold=True),
          text(230, 388, "read-only", 13.5, SUB, weight="500")]
    p += [card(360, 330, 180, 82), text(450, 360, "active.db", 21, INK, bold=True),
          text(450, 388, "read-write", 13.5, CORAL, bold=True)]
    p += ["</svg>"]
    return "\n".join(p)


# ── 版式 4：four-systems 四大系统 768x432 ──
def build_four_systems(lang: str) -> str:
    title = "四大系统" if lang == "zh" else "Four Systems"
    if lang == "zh":
        items = [(P_HEART, "Active Consciousness", "主动意识", "心跳驱动的念头生成与情绪演化"),
                 (P_MAIL, "Passive Consciousness", "被动意识", "消息到达时注入上下文与记忆"),
                 (P_BRAIN, "Free Consciousness", "自由意识", "无人时自主沉思，积淀认知"),
                 (P_CAL, "Scheduled Tasks", "定时任务", "可视化 Cron 与占位符提示词")]
    else:
        items = [(P_HEART, "Active Consciousness", "", "Heartbeat-driven thoughts & emotion"),
                 (P_MAIL, "Passive Consciousness", "", "Context injection on every message"),
                 (P_BRAIN, "Free Consciousness", "", "Autonomous contemplation & sediment"),
                 (P_CAL, "Scheduled Tasks", "", "Visual cron with prompt templates")]
    p = [svg_open(768, 432)]
    p += [text(32, 36, title, 25, INK, bold=True, anchor="start")]
    p += [f'<rect x="32" y="58" width="64" height="5" rx="2.5" fill="url(#rib)"/>']
    for i, (ic, en, zh, desc) in enumerate(items):
        x = 32 + (i % 2) * 360
        y = 92 + (i // 2) * 172
        cy = y + 78
        p += [card(x, y, 344, 156, rx=22)]
        p += [f'<rect x="{x + 24}" y="{cy - 28}" width="56" height="56" rx="18" fill="{CORAL_SOFT}"/>']
        p += [icon(ic, x + 38, cy - 14, 28)]
        tx = x + 100
        p += [text(tx, cy - 22, en, 16.5, INK, bold=True, anchor="start")]
        if zh:
            p += [text(tx, cy + 2, zh, 12.5, CORAL, bold=True, anchor="start", ls=1)]
            p += [text(tx, cy + 26, desc, 12, SUB, anchor="start")]
        else:
            p += [text(tx, cy + 6, desc, 12.5, SUB, anchor="start")]
    p += ["</svg>"]
    return "\n".join(p)


# ── 版式 5：deployment 部署拓扑 768x432 ──
def build_deployment(lang: str) -> str:
    ltag, rtag = ("消息入口", "Web 控制台") if lang == "zh" else ("Messages", "Web Console")
    svc = [("hermes-active", ":18720", True), ("Hermes Gateway", "", False),
           ("Hindsight", ":8888", False), ("plugins/", "", False)]
    p = [svg_open(768, 432)]
    p += [f'<rect x="180" y="64" width="408" height="320" rx="28" fill="#FAFAFA"'
          f' stroke="{LINE}" stroke-width="2" stroke-dasharray="7 7"/>']
    p += [f'<rect x="204" y="52" width="86" height="24" rx="12" fill="#fff" stroke="{LINE}" stroke-width="1.5"/>']
    p += [text(247, 64, "SERVER", 10.5, SUB, bold=True, ls=2)]
    for i, (name, port, hot) in enumerate(svc):
        x = 204 + (i % 2) * 188
        y = 104 + (i // 2) * 128
        p += [card(x, y, 172, 112, rx=16, stroke=CORAL if hot else LINE, sw=2.4 if hot else 2)]
        p += [text(x + 86, y + (46 if port else 56), name, 14, INK if hot else "#5F5F5F", bold=True)]
        if port:
            p += [text(x + 86, y + 74, port, 11.5, CORAL if hot else SUB, weight="500")]
    p += [icon(P_PHONE, 60, 194, 56, "#9AA0A6")]
    p += [wire(126, 222, 172, 222)]
    p += [text(90, 286, ltag, 12, SUB, weight="500")]
    p += [icon(P_BROWSER.replace("COLOR", "#9AA0A6"), 652, 196, 56, "#9AA0A6")]
    p += [wire(596, 222, 644, 222)]
    p += [text(680, 286, rtag, 12, SUB, weight="500")]
    p += ["</svg>"]
    return "\n".join(p)


# ── 版式 6：footer 页脚横幅 720x120 ──
def build_footer(lang: str) -> str:
    p = [svg_open(720, 120)]
    p += [text(360, 42, f'Hermes Active — Built with <tspan fill="#FF6B6B" font-size="17">♥</tspan> '
              f'for the Hermes Agent Community', 15, "#6E6E6E", weight="500", ls=0.6, raw=True)]
    p += [f'<path d="M60 88 H330 L342 88 L350 78 L360 100 L368 88 L380 88 H660"'
          f' stroke="url(#rib)" stroke-width="2.2" fill="none" stroke-linecap="round"'
          f' stroke-linejoin="round"/>']
    p += ["</svg>"]
    return "\n".join(p)


BUILDERS = {
    "hero": (build_hero, 840, 264),
    "problem": (build_problem, 768, 432),
    "architecture": (build_architecture, 768, 420),
    "four-systems": (build_four_systems, 768, 432),
    "deployment": (build_deployment, 768, 432),
    "footer": (build_footer, 720, 120),
}


async def preview_one(path: Path, out: Path, w: int, h: int) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto(f"file://{path}")
        await page.wait_for_timeout(200)
        await page.screenshot(path=str(out))
        await browser.close()


async def preview_all(jobs: list) -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for path, w, h in jobs:
        out = PREVIEW_DIR / f"{path.stem}-preview.png"
        await preview_one(path, out, w, h)
        print(f"  preview: {out}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    names = args or list(BUILDERS)
    jobs = []
    for name in names:
        fn, w, h = BUILDERS[name]
        for lang in ("zh", "en"):
            out = IMG / f"{lang}-{FILE_SUFFIX[name]}.svg"
            out.write_text(fn(lang), encoding="utf-8")
            print(f"✓ {out.name}")
            if lang == "zh":
                jobs.append((out, w, h))
    if "--no-preview" not in sys.argv:
        asyncio.run(preview_all(jobs))


if __name__ == "__main__":
    main()
