"""
模板服务测试用例
测试 TemplateService 的所有功能
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestTemplateService:
    """TemplateService 测试类"""

    def test_default_template_exists(self):
        """测试默认模板存在"""
        from services.template_service import DEFAULT_TEMPLATES, DEFAULT_TEMPLATE

        assert len(DEFAULT_TEMPLATES) == 1
        assert DEFAULT_TEMPLATES[0]["id"] == "default"
        assert DEFAULT_TEMPLATES[0]["name"] == "日常模板"
        assert DEFAULT_TEMPLATES[0]["is_default"] is True
        assert len(DEFAULT_TEMPLATE) > 0

    def test_render_template_basic(self):
        """测试基本模板渲染"""
        from services.template_service import TemplateService

        template_content = "情绪状态：{{ emotional_label }}（强度 {{ emotional_intensity }}）"
        data = {
            "emotional_label": "八卦",
            "emotional_intensity": 0.65
        }

        result = TemplateService.render_template(template_content, data)

        assert "八卦" in result
        assert "0.65" in result

    def test_render_template_conditional(self):
        """测试条件渲染"""
        from services.template_service import TemplateService

        template_content = """{% if inject_emotion %}
🎭 情绪状态：{{ emotional_label }}
{% endif %}
{% if inject_heat %}
🔥 聊天热度：{{ chat_heat_label }}
{% endif %}"""

        # 测试两个条件都为真
        data = {
            "inject_emotion": True,
            "inject_heat": True,
            "emotional_label": "八卦",
            "chat_heat_label": "hot"
        }
        result = TemplateService.render_template(template_content, data)
        assert "情绪状态" in result
        assert "聊天热度" in result

        # 测试只注入情绪
        data["inject_heat"] = False
        result = TemplateService.render_template(template_content, data)
        assert "情绪状态" in result
        assert "聊天热度" not in result

    def test_render_template_loop(self):
        """测试循环渲染"""
        from services.template_service import TemplateService

        template_content = """📖 相关记忆：
{% for memory in memories %}
  {{ loop.index }}. {{ memory.text }}
{% endfor %}"""

        data = {
            "memories": [
                {"text": "记忆1"},
                {"text": "记忆2"},
                {"text": "记忆3"}
            ]
        }

        result = TemplateService.render_template(template_content, data)
        assert "1. 记忆1" in result
        assert "2. 记忆2" in result
        assert "3. 记忆3" in result

    def test_render_template_nested_condition(self):
        """测试嵌套条件渲染"""
        from services.template_service import TemplateService

        template_content = """{% if weather %}
🌤 天气：{{ weather.city }} {{ weather.weather }} {{ weather.temperature }}°C
{% if weather.temperature > 30 %}
  ⚠️ 高温提醒：注意防暑降温
{% elif weather.temperature < 5 %}
  ⚠️ 低温提醒：注意保暖
{% endif %}
{% endif %}"""

        # 测试高温
        data = {"weather": {"city": "北京", "weather": "晴", "temperature": 35}}
        result = TemplateService.render_template(template_content, data)
        assert "高温提醒" in result

        # 测试低温
        data = {"weather": {"city": "哈尔滨", "weather": "雪", "temperature": -10}}
        result = TemplateService.render_template(template_content, data)
        assert "低温提醒" in result

        # 测试正常温度
        data = {"weather": {"city": "北京", "weather": "晴", "temperature": 25}}
        result = TemplateService.render_template(template_content, data)
        assert "高温提醒" not in result
        assert "低温提醒" not in result

    def test_render_template_syntax_error(self):
        """测试模板语法错误"""
        from services.template_service import TemplateService

        template_content = "{{ invalid syntax }}"
        data = {}

        with pytest.raises(ValueError, match="模板语法错误"):
            TemplateService.render_template(template_content, data)

    def test_preview_template_with_mock_data(self):
        """测试预览模板（使用模拟数据）"""
        from services.template_service import TemplateService

        template_content = "🎭 情绪状态：{{ emotional_label }}"

        result = TemplateService.preview_template(template_content)

        # 应该使用模拟数据
        assert "八卦" in result

    def test_preview_template_with_custom_data(self):
        """测试预览模板（使用自定义数据）"""
        from services.template_service import TemplateService

        template_content = "🎭 情绪状态：{{ emotional_label }}"
        data = {"emotional_label": "深度情感"}

        result = TemplateService.preview_template(template_content, data)

        assert "深度情感" in result

    def test_get_variables(self):
        """测试获取可用变量列表"""
        from services.template_service import TemplateService

        variables = TemplateService.get_variables()

        assert len(variables) > 0

        # 检查关键变量存在
        var_names = [v["name"] for v in variables]
        assert "emotional_intensity" in var_names
        assert "emotional_label" in var_names
        assert "chat_heat" in var_names
        assert "longing_score" in var_names
        assert "weather" in var_names
        assert "memories" in var_names
        assert "inject_emotion" in var_names

    def test_get_variables_types(self):
        """测试变量类型信息"""
        from services.template_service import TemplateService

        variables = TemplateService.get_variables()

        # 检查变量类型
        var_dict = {v["name"]: v["type"] for v in variables}
        assert var_dict["emotional_intensity"] == "float"
        assert var_dict["emotional_label"] == "string"
        assert var_dict["chat_heat"] == "float"
        assert var_dict["inject_emotion"] == "bool"
        assert var_dict["weather"] == "object"
        assert var_dict["memories"] == "list"

    @patch("services.template_service.TemplateService._get_mock_data")
    def test_preview_template_uses_mock_data(self, mock_get_mock_data):
        """测试预览模板时使用模拟数据"""
        from services.template_service import TemplateService

        mock_get_mock_data.return_value = {"emotional_label": "测试情绪"}
        template_content = "{{ emotional_label }}"

        result = TemplateService.preview_template(template_content)

        mock_get_mock_data.assert_called_once()
        assert "测试情绪" in result

    def test_render_default_template(self):
        """测试渲染默认模板"""
        from services.template_service import TemplateService, DEFAULT_TEMPLATE

        data = {
            "inject_emotion": True,
            "inject_heat": True,
            "inject_longing": True,
            "inject_memory": True,
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
                "wind_dir": "东南风",
                "wind_scale": "3-4级"
            },
            "memories": [
                {"text": "记忆1"},
                {"text": "记忆2"}
            ],
            "reflection": "用户情绪稳定"
        }

        result = TemplateService.render_template(DEFAULT_TEMPLATE, data)

        assert "CONSCIOUSNESS_CONTEXT" in result
        assert "八卦" in result
        assert "hot" in result
        assert "missing" in result
        assert "北京" in result
        assert "记忆1" in result
        assert "用户情绪稳定" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
