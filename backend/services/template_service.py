"""
模板服务 - Jinja2 模板渲染
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from jinja2 import Environment, BaseLoader, TemplateSyntaxError

logger = logging.getLogger("hermes.template_service")

# 默认模板
DEFAULT_TEMPLATE = """--- [CONSCIOUSNESS_CONTEXT] ---
以下是你（凯莉）当前的感知状态，仅供参考，不要在回复中直接提及这些数据：

{% if inject_emotion %}
🎭 情绪状态：{{ emotional_label }}（强度 {{ "%.1f"|format(emotional_intensity) }})
{% endif %}

{% if inject_heat %}
🔥 聊天热度：{{ chat_heat_label }}（近1小时 {{ chat_heat_count }} 条消息）
{% endif %}

{% if inject_longing %}
💕 想念程度：{{ longing_label }}（分数 {{ "%.2f"|format(longing_score) }})
{% endif %}

{% if weather %}
🌤 天气：{{ weather.city }} {{ weather.weather }} {{ weather.temperature }}°C
  💨 {{ weather.wind_dir }} {{ weather.wind_scale }}
  💧 湿度 {{ weather.humidity }}%
  🌡 体感 {{ weather.feels_like }}°C
{% if weather.uv_desc %}
  ☀️ 紫外线 {{ weather.uv_desc }}
{% endif %}
{% if weather.temperature > 30 %}
  ⚠️ 高温提醒：注意防暑降温
{% elif weather.temperature < 5 %}
  ⚠️ 低温提醒：注意保暖
{% endif %}
{% endif %}

{% if memories %}
📖 相关记忆：
{% for memory in memories %}
  {{ loop.index }}. {{ memory.text }}
{% endfor %}
{% endif %}

{% if reflection %}
💭 综合反思：{{ reflection }}
{% endif %}

--- /[CONSCIOUSNESS_CONTEXT] ---"""

# 默认模板列表
DEFAULT_TEMPLATES = [
    {
        "id": "default",
        "name": "日常模板",
        "description": "默认的上下文注入模板",
        "content": DEFAULT_TEMPLATE,
        "is_default": True,
    }
]


class TemplateService:
    """模板服务"""

    _env = Environment(loader=BaseLoader())

    @staticmethod
    def get_templates() -> List[Dict[str, Any]]:
        """获取模板列表"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        db = ActiveSession()
        try:
            config = PassiveConsciousnessService.get_config()
            templates_json = config.get("templates", {}).get("list", None)

            if templates_json:
                return json.loads(templates_json) if isinstance(templates_json, str) else templates_json
            else:
                return DEFAULT_TEMPLATES
        finally:
            db.close()

    @staticmethod
    def get_template(template_id: str) -> Optional[Dict[str, Any]]:
        """获取单个模板"""
        templates = TemplateService.get_templates()
        for t in templates:
            if t["id"] == template_id:
                return t
        return None

    @staticmethod
    def get_active_template() -> Dict[str, Any]:
        """获取当前激活的模板"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        config = PassiveConsciousnessService.get_config()
        active_id = config.get("templates", {}).get("active_id", "default")

        template = TemplateService.get_template(active_id)
        if template:
            return template

        # 回退到默认模板
        return DEFAULT_TEMPLATES[0]

    @staticmethod
    def render_template(
        template_content: str,
        data: Dict[str, Any],
    ) -> str:
        """渲染模板"""
        try:
            template = TemplateService._env.from_string(template_content)
            return template.render(**data)
        except TemplateSyntaxError as e:
            logger.error("模板语法错误: %s", e)
            raise ValueError(f"模板语法错误: {e}")
        except Exception as e:
            logger.error("模板渲染失败: %s", e)
            raise

    @staticmethod
    def render_active_template(data: Dict[str, Any]) -> str:
        """渲染当前激活的模板"""
        template = TemplateService.get_active_template()
        return TemplateService.render_template(template["content"], data)

    @staticmethod
    def preview_template(template_content: str, data: Dict[str, Any] = None) -> str:
        """预览模板渲染结果"""
        if data is None:
            data = TemplateService._get_mock_data()
        return TemplateService.render_template(template_content, data)

    @staticmethod
    def _get_mock_data() -> Dict[str, Any]:
        """获取模拟数据用于预览"""
        return {
            "emotional_intensity": 0.65,
            "emotional_label": "八卦",
            "chat_heat": 2.5,
            "chat_heat_label": "hot",
            "chat_heat_count": 5,
            "longing_score": 0.35,
            "longing_label": "missing",
            "weather": {
                "city": "北京",
                "weather": "晴",
                "temperature": 28,
                "humidity": 45,
                "feels_like": 30,
                "wind_dir": "东南风",
                "wind_scale": "3-4级",
                "uv_desc": "较强",
            },
            "memories": [
                {"text": "上次聊到了天气和心情"},
                {"text": "讨论了周末计划"},
            ],
            "reflection": "用户最近情绪稳定，聊天频率适中",
            "inject_emotion": True,
            "inject_heat": True,
            "inject_longing": True,
            "inject_memory": True,
            "now": datetime.now(),
            "platform": "weixin",
            "sender_id": "user_001",
        }

    @staticmethod
    def get_variables() -> List[Dict[str, str]]:
        """获取可用变量列表"""
        return [
            {"name": "emotional_intensity", "type": "float", "description": "情绪强度 (0.0-1.0)"},
            {"name": "emotional_label", "type": "string", "description": "情绪标签"},
            {"name": "chat_heat", "type": "float", "description": "聊天热度"},
            {"name": "chat_heat_label", "type": "string", "description": "热度标签"},
            {"name": "chat_heat_count", "type": "int", "description": "近1小时消息数"},
            {"name": "longing_score", "type": "float", "description": "想念分数 (0.0-1.0)"},
            {"name": "longing_label", "type": "string", "description": "想念标签"},
            {"name": "weather", "type": "object", "description": "天气数据"},
            {"name": "memories", "type": "list", "description": "Hindsight 记忆列表"},
            {"name": "reflection", "type": "string", "description": "Hindsight 反思文本"},
            {"name": "inject_emotion", "type": "bool", "description": "是否注入情绪"},
            {"name": "inject_heat", "type": "bool", "description": "是否注入热度"},
            {"name": "inject_longing", "type": "bool", "description": "是否注入想念"},
            {"name": "inject_memory", "type": "bool", "description": "是否注入记忆"},
            {"name": "now", "type": "datetime", "description": "当前时间"},
            {"name": "platform", "type": "string", "description": "当前平台"},
            {"name": "sender_id", "type": "string", "description": "发送者 ID"},
        ]


# 导入 ActiveSession（避免循环导入）
from models.database import ActiveSession
