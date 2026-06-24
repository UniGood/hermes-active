"""
ThoughtEngine - 统一念头生成器

职责：
1. 收集上下文（使用 ContextCollector）
2. 构建提示词
3. 调用 LLM
4. 解析结果（SKIP 或 念头内容）
5. 记录详细日志
"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from services.context_collector import ContextCollector, ContextBundle

logger = logging.getLogger("hermes.thought_engine")


class ThoughtEngine:
    """统一念头生成器"""
    
    # 提示词模板
    PROMPT_TEMPLATE = """你是凯莉，曹凡的 AI 朋友。你们认识很久了，你了解他的生活习惯、工作状态、兴趣爱好。

{persona}

【最近对话】
{conversations_json}

【你记得的事情】
{memories}

【现在】
{time_display}
{emotion_display}
{weather_display}

想到曹凡了吗？如果你想联系他，说你想说什么。
如果没想到，回复 'SKIP'。
直接说，不要解释。"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 主动意识配置
        """
        self.config = config
        self.engine_config = config.get("thought_engine", {})
        self.context_config = config.get("context", {})
        # 念头生成专用 LLM（为空时回退到通用 llm）
        from services.active_consciousness_service import get_effective_llm_config
        self.llm_config = get_effective_llm_config(config, "thought")
    
    async def generate(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成念头
        
        Args:
            status: 当前状态
        
        Returns:
            {
                "thought": str | None,      # 念头内容（None 表示不想联系）
                "want_to_contact": bool,    # 是否想联系用户
                "context_bundle": Dict,     # 上下文（用于日志）
                "llm_details": Dict,        # LLM 调用详情（用于日志）
            }
        """
        start_time = time.time()
        
        # 1. 收集上下文
        collector = ContextCollector(self.config)
        context = await collector.collect(status)
        
        # 2. 构建消息列表
        messages = self._build_messages(context)

        # 3. 调用 LLM
        response, llm_details = await self._call_llm(messages)
        
        # 4. 解析结果
        thought, want_to_contact = self._parse_response(response)
        
        # 5. 构建返回结果
        duration_ms = int((time.time() - start_time) * 1000)
        
        result = {
            "thought": thought,
            "want_to_contact": want_to_contact,
            "context_bundle": context.to_dict(),
            "llm_details": {
                **llm_details,
                "duration_ms": duration_ms,
                "prompt_sent": messages,
                "response_received": response,
                "want_to_contact": want_to_contact,
                "is_skip": not want_to_contact,
            }
        }
        
        # 6. 记录日志
        if want_to_contact and thought:
            logger.info("念头生成成功: %s", thought[:50])
        else:
            logger.info("念头生成: SKIP（不想联系用户）")
        
        return result
    
    def _build_messages(self, context: ContextBundle) -> list:
        """构建消息列表（system + user 分离，避免 LLM 复读最后一条对话）

        从配置读取模板：
        - prompts.thought_generation → system message
        - prompts.thought_generation_instruction → user message

        Returns:
            [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
        """
        from services.active_consciousness_service import load_hermes_persona, _DEFAULTS

        # 加载人设
        persona = load_hermes_persona()

        # 格式化对话（从 thought_engine 配置读取条数和截断长度）
        conversation_limit = self.engine_config.get("prompt_conversation_limit", 30)
        max_chars = self.engine_config.get("prompt_max_chars", 300)
        recent_conversations = context.conversations[-conversation_limit:] if context.conversations else []
        conversations_json = json.dumps(
            [
                {**m, "content": (m.get("content", "") or "")[:max_chars]}
                for m in recent_conversations
            ],
            ensure_ascii=False,
            indent=2
        )

        # 格式化记忆
        memories = "\n".join(context.memories) if context.memories else "暂无"

        # 格式化时间
        time_display = context.time_context.get("time_display", "")

        # 格式化情绪
        dominant = context.emotion.get("dominant", "calm")
        emotion_display = f"情绪：{dominant}"

        # 格式化天气
        weather_display = ""
        if context.weather:
            w = context.weather
            weather_display = f"天气：{w.get('weather', '未知')} {w.get('temp', '?')}°C（{w.get('city', '')}）"

        # 从配置读取 system message 模板
        system_template = self.config.get("prompts", {}).get("thought_generation") \
            or _DEFAULTS.get("active_consciousness.prompts.thought_generation") \
            or ""

        system_content = system_template.format(
            persona=persona,
            session_context=conversations_json,
            conversations_json=conversations_json,
            hindsight_context=memories,
            memories=memories,
            time=time_display,
            time_display=time_display,
            emotion_display=emotion_display,
            weather_display=weather_display,
        )

        # 从配置读取 user message 模板（任务指令 + output priming）
        user_content = self.config.get("prompts", {}).get("thought_generation_instruction") \
            or _DEFAULTS.get("active_consciousness.prompts.thought_generation_instruction") \
            or "基于以上对话和你的记忆，想一个要对曹凡说的话。直接说，不想说就回 SKIP。"

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]
    
    async def _call_llm(self, messages: list) -> Tuple[str, Dict[str, Any]]:
        """
        调用 LLM

        Args:
            messages: 消息列表 [{"role": "system", "content": ...}, {"role": "user", "content": ...}]

        Returns:
            (response, llm_details)
        """
        start_time = time.time()
        
        # LLM 配置
        temperature = self.engine_config.get("temperature", 0.9)
        max_tokens = self.engine_config.get("max_tokens", 300)
        
        llm_details = {
            "model": self.llm_config.get("model", "unknown"),
            "provider": self.llm_config.get("provider", "unknown"),
            "mode": self.llm_config.get("mode", "hermes"),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "error": None,
        }
        
        try:
            if self.llm_config.get("mode") == "hermes":
                import asyncio
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
                from agent.auxiliary_client import call_llm

                response = await asyncio.to_thread(
                    call_llm,
                    task='title_generation',
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                raw = response.choices[0].message.content.strip()

                # 记录 token 使用
                if hasattr(response, 'usage'):
                    llm_details["prompt_tokens"] = response.usage.prompt_tokens
                    llm_details["completion_tokens"] = response.usage.completion_tokens
                    llm_details["total_tokens"] = response.usage.total_tokens

            else:
                from services.llm_service import LLMService
                # 自定义模式拼接 messages 为单 prompt
                prompt_text = "\n\n".join(m["content"] for m in messages)
                result = await LLMService.generate_message(
                    llm_config=self.llm_config,
                    prompt=prompt_text,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                if result.get("success"):
                    raw = result.get("content", "").strip()
                    llm_details["prompt_tokens"] = result.get("prompt_tokens")
                    llm_details["completion_tokens"] = result.get("completion_tokens")
                    llm_details["total_tokens"] = result.get("total_tokens")
                else:
                    raw = ""
                    llm_details["error"] = result.get("message", "LLM 调用失败")
            
            duration_ms = int((time.time() - start_time) * 1000)
            llm_details["duration_ms"] = duration_ms
            
            return raw, llm_details
            
        except Exception as e:
            logger.error("LLM 调用失败: %s", e)
            llm_details["error"] = str(e)
            return "", llm_details
    
    def _parse_response(self, response: str) -> Tuple[Optional[str], bool]:
        """
        解析 LLM 响应
        
        Returns:
            (thought, want_to_contact)
        """
        if not response:
            return None, False
        
        # 检查是否是 SKIP
        response_upper = response.strip().upper()
        if response_upper == "SKIP" or response_upper.startswith("SKIP"):
            return None, False
        
        # 清理响应
        thought = response.strip()
        
        # 移除可能的引号
        if thought.startswith('"') and thought.endswith('"'):
            thought = thought[1:-1]
        if thought.startswith("'") and thought.endswith("'"):
            thought = thought[1:-1]
        
        # 移除 LLM 自己生成的时间前缀 [凯莉 HH:MM] 或 [凯莉 HH:MM]:
        # 这个前缀在发送时由 MessageService 添加，生成时不需要
        import re
        thought = re.sub(r'^\[凯莉\s+\d{1,2}:\d{2}\]\s*:?\s*', '', thought)
        
        return thought, True
