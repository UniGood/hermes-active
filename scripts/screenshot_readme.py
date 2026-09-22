"""hermes-active README 界面截图脚本

签发临时 JWT（只读，不动账号数据）注入浏览器，绕过登录页，
逐页截图 6 个核心页面存入 docs/screenshots/，用于 README 截图。

用法：~/.hermes/hermes-agent/venv/bin/python3 scripts/screenshot_readme.py

注意：
- 截图前自动打码 sk- 开头的密钥字符串，防止泄漏
- free-consciousness 截 Contemplation Logs tab（Status & Config 页含 API Key 明文）
- passive-consciousness 截主内容区 Test tab（展示信号测试按钮 + 全文预览）
"""
import asyncio
import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

from playwright.async_api import async_playwright

BASE_URL = "http://localhost:18720"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "screenshots"

# 与 backend/config.py 保持一致（环境变量未设时的默认值）
JWT_SECRET = "hermes-active-secret-key-change-in-production"

VIEWPORT = {"width": 1440, "height": 900}

# 截图前全局打码密钥
MASK_JS = """
() => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const texts = [];
  while (walker.nextNode()) texts.push(walker.currentNode);
  for (const t of texts) {
    if (/sk-[A-Za-z0-9]{8,}/.test(t.textContent)) {
      t.textContent = t.textContent.replace(/sk-[A-Za-z0-9]+/g, 'sk-****MASKED****');
    }
  }
  for (const inp of document.querySelectorAll('input')) {
    if (/sk-[A-Za-z0-9]{8,}/.test(inp.value)) {
      inp.value = 'sk-****MASKED****';
    }
  }
}
"""


def make_token() -> str:
    """签发与后端相同格式的 JWT：sub=admin, exp=24h"""
    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = b64url(json.dumps({"alg": "HS256"}).encode())
    payload = b64url(json.dumps({
        "sub": "admin",
        "exp": int(time.time()) + 86400,
    }).encode())
    msg = f"{header}.{payload}".encode()
    sig = b64url(hmac.new(JWT_SECRET.encode(), msg, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


async def shot(page, name: str, full_page=False):
    await page.evaluate(MASK_JS)
    await page.wait_for_timeout(500)
    out = OUT_DIR / f"{name}.png"
    await page.screenshot(path=str(out), full_page=full_page)
    print(f"✓ {name}.png")


async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    token = make_token()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        # 注入 token，所有页面自动带登录态
        await ctx.add_init_script(f"localStorage.setItem('token', '{token}')")
        page = await ctx.new_page()

        # 验证 token 有效（/api/auth/me 需要合法 JWT，手动带头）
        resp = await page.request.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status != 200:
            raise RuntimeError(f"token 无效: {resp.status} {await resp.text()}")
        print("token 验证通过")

        # ── 1. 仪表盘 ──
        await page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2500)
        await shot(page, "dashboard")

        # ── 2. 主动意识 ──
        await page.goto(f"{BASE_URL}/active-consciousness", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2500)
        await shot(page, "active-consciousness")

        # ── 3. 被动意识 → Test tab（每个信号的测试按钮 + 全文预览） ──
        await page.goto(f"{BASE_URL}/passive-consciousness", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1500)
        await page.locator(".n-tabs-tab", has_text="Test").first.click()
        await page.wait_for_timeout(2500)
        await shot(page, "passive-consciousness", full_page=True)

        # ── 4. 自由意识 → Contemplation Logs tab（思考链时间线；Status 页含密钥不截） ──
        await page.goto(f"{BASE_URL}/free-consciousness", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1500)
        await page.locator("text=Contemplation Logs").first.click()
        await page.wait_for_timeout(2500)
        await shot(page, "free-consciousness")

        # ── 5. 定时任务 ──
        await page.goto(f"{BASE_URL}/cron-jobs", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2500)
        await shot(page, "cron-jobs")

        # ── 6. 注入分析（注意：前端解析 bug 未修前图表为空白，见 README 提交说明） ──
        await page.goto(f"{BASE_URL}/analysis", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2500)
        await shot(page, "analysis")

        await browser.close()
    print("全部完成")


asyncio.run(main())
