"""
LLM 服务
"""
import time
from typing import Optional, Dict, Any
from openai import AsyncOpenAI

from config import DEFAULT_LLM_CONFIG

# 可用 provider 列表
PROVIDERS = [
    {"id": "openai", "name": "OpenAI", "base_url": "https://api.openai.com/v1"},
    {"id": "anthropic", "name": "Anthropic", "base_url": "https://api.anthropic.com/v1"},
    {"id": "xiaomi", "name": "小米 MiMo", "base_url": "https://api.xiaomi.com/v1"},
    {"id": "deepseek", "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1"},
    {"id": "custom", "name": "自定义", "base_url": ""},
]


class LLMService:
    """LLM 服务类"""

    @staticmethod
    def _get_client(llm_config: Dict[str, Any]) -> AsyncOpenAI:
        """根据配置创建 OpenAI 客户端"""
        provider = llm_config.get("provider", "")
        api_key = llm_config.get("api_key", "")
        base_url = llm_config.get("base_url", "")

        # 从 provider 列表中查找默认 base_url
        if not base_url and provider:
            for p in PROVIDERS:
                if p["id"] == provider:
                    base_url = p["base_url"]
                    break

        if not api_key:
            raise ValueError("未配置 LLM API Key")

        if not base_url:
            raise ValueError("未配置 LLM Base URL")

        return AsyncOpenAI(api_key=api_key, base_url=base_url)

    @staticmethod
    async def _close_client(client: AsyncOpenAI) -> None:
        """安全关闭 AsyncOpenAI 客户端，释放底层 httpx/aiohttp 连接"""
        try:
            await client.close()
        except Exception:
            pass  # 忽略关闭异常

    @staticmethod
    async def test_connection(llm_config: Dict[str, Any]) -> Dict[str, Any]:
        """测试 LLM 连通性"""
        start_time = time.time()
        client = LLMService._get_client(llm_config)
        try:
            model = llm_config.get("model", "gpt-3.5-turbo")

            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )

            duration = round(time.time() - start_time, 2)
            return {
                "success": True,
                "message": f"LLM 连通性测试成功 (耗时 {duration}s)",
                "model": model,
                "duration": duration
            }
        except ValueError as e:
            return {"success": False, "message": str(e)}
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            return {
                "success": False,
                "message": f"LLM 连通性测试失败: {str(e)}",
                "duration": duration
            }
        finally:
            await LLMService._close_client(client)

    @staticmethod
    async def generate_message(
        llm_config: Dict[str, Any],
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 200
    ) -> Dict[str, Any]:
        """调用 LLM 生成消息"""
        start_time = time.time()
        client = LLMService._get_client(llm_config)
        try:
            model = llm_config.get("model", "gpt-3.5-turbo")

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content.strip()
            duration = round(time.time() - start_time, 2)

            return {
                "success": True,
                "content": content,
                "model": model,
                "duration": duration
            }
        except ValueError as e:
            return {"success": False, "content": "", "message": str(e)}
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            return {
                "success": False,
                "content": "",
                "message": f"LLM 调用失败: {str(e)}",
                "duration": duration
            }
        finally:
            await LLMService._close_client(client)

    @staticmethod
    def get_providers() -> list:
        """获取可用 provider 列表"""
        return [p["id"] for p in PROVIDERS]
