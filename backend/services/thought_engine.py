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
import re
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from services.context_collector import ContextCollector, ContextBundle

logger = logging.getLogger("hermes.thought_engine")


def _bigram_jaccard(a: str, b: str) -> float:
    """字符 bigram 相似度（零依赖防复读粗筛）

    注：分母用 min(|A|,|B|)（重叠系数）而非 |A∪B|。
    短中文句 bigram 总量小，Jaccard 会系统性偏低（如 3/8=0.375），
    难以命中 0.6 阈值；重叠系数对“换了几个字的车轱辘话”更敏感。
    """
    def grams(s: str) -> set:
        s = re.sub(r'\s+', '', s or '')
        return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / min(len(ga), len(gb))


def _is_repetitive(text: str, recent: list, threshold: float = 0.6) -> bool:
    """与最近话题/句式相似则判复读（threshold 启发式起步值，可配）"""
    return any(_bigram_jaccard(text, r) >= threshold for r in recent if r)


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

        # 防复读：与最近已发送念头粗筛相似则重生成一次（只重试一次，防死循环）
        repetitive = False
        if want_to_contact and thought:
            recent_full = self._recent_sent_topics(limit=3, max_chars=None)
            if _is_repetitive(thought, recent_full):
                logger.info("念头疑似复读，重生成一次: %s", thought[:50])
                response, llm_details = await self._call_llm(messages)
                thought, want_to_contact = self._parse_response(response)
                if want_to_contact and thought and _is_repetitive(thought, recent_full):
                    # 二次仍相似：接受并标记，不再重试
                    repetitive = True

        # 5. 构建返回结果
        duration_ms = int((time.time() - start_time) * 1000)
        
        result = {
            "thought": thought,
            "want_to_contact": want_to_contact,
            "repetitive": repetitive,
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
        from services.config_service import ConfigService
        from services.message_service import MessageService
        from models.database import ActiveSession

        # 加载人设
        persona = load_hermes_persona()

        # 获取配置的名称（复用同一个 session，用完关闭）
        _name_db = ActiveSession()
        try:
            user_name = ConfigService.get_config(_name_db, "personalization.user_name") or "曹凡"
            assistant_name = ConfigService.get_config(_name_db, "personalization.assistant_name") or "凯莉"
        finally:
            _name_db.close()
        role_map = {"user": user_name, "assistant": assistant_name}

        # 格式化对话（纯文本格式：[时间] 角色名: 内容，每条截断）
        max_chars = self.engine_config.get("prompt_max_chars", 300)
        truncated_msgs = [
            {**m, "content": (m.get("content", "") or "")[:max_chars]}
            for m in (context.conversations or [])
        ]
        session_context = MessageService.format_session_messages(
            truncated_msgs,
            role_map=role_map,
            time_format="%Y-%m-%d %H:%M:%S"
        ) if truncated_msgs else "暂无"

        # 格式化记忆
        memories = "\n".join(context.memories) if context.memories else "暂无"

        # 格式化时间（使用配置的时间格式，支持 {weekday} 自定义标记）
        from datetime import datetime, timezone, timedelta
        WEEKDAY_NAMES = ['一', '二', '三', '四', '五', '六', '日']
        time_format = self.config.get("prompts", {}).get("time_format", "%Y-%m-%d %H:%M:%S")
        now = datetime.now(timezone(timedelta(hours=8)))
        weekday = WEEKDAY_NAMES[now.weekday()]
        time_display = time_format.replace('{weekday}', weekday)
        for fmt, val in [('%Y', now.year), ('%m', f'{now.month:02d}'), ('%d', f'{now.day:02d}'),
                         ('%H', f'{now.hour:02d}'), ('%M', f'{now.minute:02d}'), ('%S', f'{now.second:02d}')]:
            time_display = time_display.replace(str(fmt), str(val))

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
            session_context=session_context,
            hindsight_context=memories,
            time=time_display,
            emotion_display=emotion_display,
            weather_display=weather_display,
        )

        # 从配置读取 user message 模板（任务指令 + output priming）
        user_template = self.config.get("prompts", {}).get("thought_generation_instruction") \
            or _DEFAULTS.get("active_consciousness.prompts.thought_generation_instruction") \
            or "基于以上对话和你的记忆，想一个要对曹凡说的话。直接说，不想说就回 SKIP。"

        # user message 也支持 {time} 替换
        user_content = user_template.format(
            time=time_display,
            user_name=user_name,
        )

        # 深夜气质提示（可配置时段，支持跨午夜；起点为开区间，与 _deep_night_factor 一致）
        now_h = now.hour + now.minute / 60.0
        time_cfg = self.config.get("time", {})
        dn_start = float(time_cfg.get("deep_night_start", 23.5))
        dn_end = float(time_cfg.get("deep_night_end", 7.0))
        if (dn_start <= dn_end and dn_start < now_h < dn_end) or \
           (dn_start > dn_end and (now_h > dn_start or now_h < dn_end)):
            user_content += "\n（现在是深夜，想得更轻、更安静，一句就好。）"

        # 防复读：最近说过的注入负面样本
        recent_said = self._recent_sent_topics(limit=5)
        if recent_said:
            user_content += "\n\n最近你主动说过这些，换新的，别重复：" + "；".join(recent_said)

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def _recent_sent_topics(self, limit: int = 5, max_chars: Optional[int] = 30) -> list:
        """查最近 decision='send' 的已发送念头（防复读用）

        Args:
            limit: 取多少条
            max_chars: 每条截断字数（默认 30，用于 prompt 注入）；None 表示全文（用于相似度比对）
        """
        from sqlalchemy import text
        from models.database import active_engine
        try:
            with active_engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT content FROM active_thought_logs "
                    "WHERE decision = 'send' "
                    "ORDER BY created_at DESC LIMIT :limit"
                ), {"limit": limit}).fetchall()
                topics = []
                for r in rows:
                    c = (r[0] or "").strip()
                    if not c:
                        continue
                    topics.append(c[:max_chars] if max_chars else c)
                return topics
        except Exception as e:
            logger.warning("查询最近已发送念头失败: %s", e)
            return []
    
    async def _call_llm(self, messages: list) -> Tuple[str, Dict[str, Any]]:
        """
        调用 LLM

        Args:
            messages: 消息列表 [{"role": "system", "content": ...}, {"role": "user", "content": ...}]

        Returns:
            (response, llm_details)
        """
        start_time = time.time()
        
        # LLM 配置（max_tokens=0 或不配置 → 不限制）
        temperature = self.engine_config.get("temperature", 0.9)
        max_tokens_raw = self.engine_config.get("max_tokens", 0)
        max_tokens = int(max_tokens_raw) if max_tokens_raw and int(max_tokens_raw) > 0 else None

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
                from agent.auxiliary_client import call_llm, extract_content_or_reasoning

                call_kwargs = dict(
                    messages=messages,
                    temperature=temperature,
                )
                if max_tokens is not None:
                    call_kwargs["max_tokens"] = max_tokens
                response = await asyncio.to_thread(call_llm, **call_kwargs)
                raw = extract_content_or_reasoning(response)

                # 提取 reasoning_content
                msg = response.choices[0].message
                reasoning_content = getattr(msg, 'reasoning_content', None) or getattr(msg, 'reasoning', None)
                if not reasoning_content:
                    details = getattr(msg, 'reasoning_details', None)
                    if details and isinstance(details, list):
                        reasoning_content = "\n\n".join(
                            d.get("summary") or d.get("content") or d.get("text", "")
                            for d in details
                            if isinstance(d, dict)
                        )
                llm_details["reasoning_content"] = reasoning_content

                # 记录 token 使用
                if hasattr(response, 'usage'):
                    llm_details["prompt_tokens"] = response.usage.prompt_tokens
                    llm_details["completion_tokens"] = response.usage.completion_tokens
                    llm_details["total_tokens"] = response.usage.total_tokens

            else:
                from services.llm_service import LLMService
                # 自定义模式拼接 messages 为单 prompt
                prompt_text = "\n\n".join(m["content"] for m in messages)
                gen_kwargs = dict(
                    llm_config=self.llm_config,
                    prompt=prompt_text,
                    temperature=temperature,
                )
                if max_tokens is not None:
                    gen_kwargs["max_tokens"] = max_tokens
                result = await LLMService.generate_message(**gen_kwargs)
                
                if result.get("success"):
                    raw = result.get("content", "").strip()
                    llm_details["prompt_tokens"] = result.get("prompt_tokens")
                    llm_details["completion_tokens"] = result.get("completion_tokens")
                    llm_details["total_tokens"] = result.get("total_tokens")
                    llm_details["reasoning_content"] = result.get("reasoning_content")
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
