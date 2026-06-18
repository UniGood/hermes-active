# backend/services/thought_generator.py

import re
import logging
from typing import Dict, List

logger = logging.getLogger("hermes.thought_generator")


class ThoughtGenerator:
    """念头生成器 - 增强版"""

    async def generate(
        self,
        config: Dict,
        emotion_state: Dict,
        weather_info: Dict,
        chat_history: List[Dict],
        old_thoughts: List[Dict],
        llm_call_func=None
    ) -> List[Dict]:
        """
        生成念头（公开 API）

        Args:
            config: 增强念头生成配置
            emotion_state: 当前情绪状态
            weather_info: 天气信息
            chat_history: 聊天记录
            old_thoughts: 旧念头（用于去重）
            llm_call_func: LLM 调用函数（可选）

        Returns:
            [{"content": "...", "type": "...", "score": 0.7}, ...]
        """
        # 1. 根据 arousal 选择时间范围
        arousal = emotion_state.get("arousal", 0.5)
        time_range = self._select_time_range(arousal, config)

        # 2. 确定生成数量
        count = self._get_thought_count(time_range, config)

        # 3. 构建 prompt
        prompt = self._build_prompt(
            time_range=time_range,
            count=count,
            emotion_state=emotion_state,
            weather_info=weather_info,
            chat_history=chat_history,
            old_thoughts=old_thoughts,
            config=config
        )

        # 4. 调用 LLM
        if llm_call_func:
            response = await llm_call_func(prompt)
        else:
            response = ""

        # 5. 解析念头
        thoughts = self._parse_thoughts(response)

        return thoughts

    def _select_time_range(self, arousal: float, config: Dict) -> int:
        """根据 arousal 选择时间范围"""
        # 约束 arousal 到 [0, 1] 范围
        arousal = max(0.0, min(1.0, arousal))

        low_threshold = config.get("arousal_low_threshold", 0.3)
        high_threshold = config.get("arousal_high_threshold", 0.7)

        if arousal < low_threshold:
            return 15  # 15 天
        elif arousal < high_threshold:
            return 7   # 7 天
        else:
            return 1   # 1 天

    def _get_thought_count(self, time_range: int, config: Dict) -> int:
        """根据时间范围确定生成数量"""
        count_map = {
            15: config.get("count_15d", 3),
            7: config.get("count_7d", 2),
            1: config.get("count_1d", 1)
        }
        return count_map.get(time_range, 1)

    def _build_prompt(
        self,
        time_range: int,
        count: int,
        emotion_state: Dict,
        weather_info: Dict,
        chat_history: List[Dict],
        old_thoughts: List[Dict],
        config: Dict
    ) -> str:
        """构建 prompt"""
        logger.debug("构建 prompt: time_range=%d, count=%d", time_range, count)

        # 聊天记录格式化
        chat_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in chat_history[:50]
        ])

        # 旧念头格式化
        old_thoughts_text = "\n".join([
            f"{i+1}. {t.get('content', '')}"
            for i, t in enumerate(old_thoughts)
        ])

        # 天气信息
        weather_text = ""
        if config.get("weather_enabled") and weather_info.get("weather_changed"):
            change_type = weather_info.get("change_type", "")
            current = weather_info.get("current", {})
            future = weather_info.get("future", {})

            weather_text = f"""
【天气变化提醒】
天气刚刚发生了变化（{change_type}）：
- 当前：{current.get('weather', '未知')}，{current.get('temp', '?')}°C
- 未来：{future.get('weather', '未知')}，{future.get('temp', '?')}°C
可以考虑生成天气相关的念头。
"""

        # 获取主导情绪的中文展示
        from services.active_consciousness_service import get_label_display
        dominant = emotion_state.get('dominant', 'calm')
        dominant_display = get_label_display(dominant)

        # 从配置获取提示词模板
        from services.active_consciousness_service import _DEFAULTS
        from models.database import ActiveSession
        from services.config_service import ConfigService

        prompt_template = ConfigService.get_config(
            ActiveSession(), "active_consciousness.prompts.enhanced_thought"
        ) or _DEFAULTS["active_consciousness.prompts.enhanced_thought"]

        prompt = prompt_template.format(
            count=count,
            time_range=time_range,
            chat_text=chat_text,
            old_thoughts_text=old_thoughts_text,
            valence=emotion_state.get('valence', 0.5),
            arousal=emotion_state.get('arousal', 0.5),
            dominant=dominant,
            dominant_display=dominant_display,
            weather_text=weather_text,
        )

        logger.debug("prompt 长度: %d", len(prompt))
        return prompt

    def _parse_thoughts(self, response: str) -> List[Dict]:
        """解析 LLM 返回的念头"""
        thoughts = []
        pattern = r'<thought>(.*?)</thought>'
        matches = re.findall(pattern, response, re.DOTALL)

        for match in matches:
            thoughts.append({
                "content": match.strip(),
                "type": "association",
                "score": 0.5
            })

        return thoughts
