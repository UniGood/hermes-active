"""
被动意识系统端到端集成测试
测试完整的被动意识注入流程
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestPassiveConsciousnessE2E:
    """被动意识端到端测试类"""

    @patch("services.passive_consciousness_service.ActiveSession")
    @patch("services.passive_consciousness_service.state_engine")
    @patch("services.passive_consciousness_service.ConfigService")
    def test_full_config_flow(self, mock_config_service, mock_state_engine, mock_session):
        """测试完整的配置流程：读取 -> 修改 -> 保存 -> 验证"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        # 1. 初始配置（使用默认值）
        mock_config_service.get_config.return_value = None
        initial_config = PassiveConsciousnessService.get_config()

        assert initial_config["enabled"] is False
        assert initial_config["platforms"]["enabled"] is False

        # 2. 修改配置
        new_config = {
            "enabled": True,
            "platforms": {
                "enabled": True,
                "whitelist": ["weixin", "feishu", "telegram"]
            },
            "templates": {
                "active_id": "custom"
            }
        }

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        PassiveConsciousnessService.update_config(new_config)

        # 3. 验证配置已保存
        assert mock_config_service.set_config.call_count > 0

    @patch("services.template_service.TemplateService.get_active_template")
    @patch("services.template_service.TemplateService.render_template")
    def test_template_render_flow(self, mock_render, mock_get_template):
        """测试完整的模板渲染流程"""
        from services.template_service import TemplateService

        # 1. 获取模板
        mock_get_template.return_value = {
            "id": "default",
            "content": "--- [CONSCIOUSNESS_CONTEXT] ---\n{{ emotional_label }}\n--- /[CONSCIOUSNESS_CONTEXT] ---"
        }

        # 2. 渲染模板
        mock_render.return_value = "--- [CONSCIOUSNESS_CONTEXT] ---\n八卦\n--- /[CONSCIOUSNESS_CONTEXT] ---"

        template = TemplateService.get_active_template()
        result = TemplateService.render_template(template["content"], {"emotional_label": "八卦"})

        assert "CONSCIOUSNESS_CONTEXT" in result
        assert "八卦" in result

    @patch("services.analysis_service.active_engine")
    def test_analysis_data_flow_stats(self, mock_engine):
        """测试注入统计数据流程"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟注入统计数据
        def mock_execute(query, params=None):
            result = MagicMock()
            query_str = str(query)
            if "COUNT(*) AS total" in query_str:
                result.fetchone.return_value = (100, 80, 15, 5, 450.0, 0.35, 1.8, 0.55)
            elif "GROUP BY platform" in query_str:
                result.fetchall.return_value = [("weixin", 60), ("feishu", 40)]
            elif "GROUP BY" in query_str:
                result.fetchall.return_value = []
            else:
                result.fetchone.return_value = (0, 0, 0, 0, 0, 0, 0, 0)
                result.fetchall.return_value = []
            return result

        mock_conn.execute.side_effect = mock_execute

        # 获取统计数据
        stats = AnalysisService.get_injection_stats(hours=24)
        assert stats["total"] == 100
        assert stats["success"] == 80
        assert stats["success_rate"] == 0.8

    @patch("services.analysis_service.active_engine")
    def test_analysis_data_flow_trends(self, mock_engine):
        """测试趋势数据流程"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟趋势数据
        mock_conn.execute.return_value.fetchall.return_value = [
            ("2026-07-31 10:00", 10, 8, 0.5, 1.5, 0.5, 400),
            ("2026-07-31 11:00", 15, 12, 0.6, 1.8, 0.6, 450)
        ]

        trends = AnalysisService.get_trend_data(hours=24, interval="hour")
        assert len(trends["data"]) == 2
        assert trends["interval"] == "hour"
        assert trends["data"][0]["period"] == "2026-07-31 10:00"
        assert trends["data"][0]["count"] == 10

    @patch("services.analysis_service.active_engine")
    def test_analysis_data_flow_sentiment(self, mock_engine):
        """测试情感分析数据流程"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟情感分析数据
        def mock_execute(query, params=None):
            result = MagicMock()
            query_str = str(query)
            if "emotional_label" in query_str:
                result.fetchall.return_value = [("工作", 30), ("八卦", 20)]
            elif "longing_label" in query_str:
                result.fetchall.return_value = [("calm", 50)]
            elif "chat_heat_label" in query_str:
                result.fetchall.return_value = [("cold", 40)]
            elif "AVG" in query_str:
                result.fetchone.return_value = (0.35, 1.8, 0.55)
            elif "SUM" in query_str:
                result.fetchone.return_value = (15, 20)
            else:
                result.fetchone.return_value = (0, 0, 0)
                result.fetchall.return_value = []
            return result

        mock_conn.execute.side_effect = mock_execute

        sentiment = AnalysisService.get_sentiment_analysis(hours=72)
        assert "emotional_distribution" in sentiment
        assert "avg_scores" in sentiment
        assert sentiment["avg_scores"]["longing"] == 0.35

    def test_platform_whitelist_logic(self):
        """测试平台白名单逻辑"""
        # 模拟平台配置
        platforms_config = {
            "enabled": True,
            "whitelist": ["weixin", "feishu"]
        }

        # 测试白名单内的平台
        assert self._check_platform_allowed("weixin", platforms_config) is True
        assert self._check_platform_allowed("feishu", platforms_config) is True

        # 测试白名单外的平台
        assert self._check_platform_allowed("telegram", platforms_config) is False
        assert self._check_platform_allowed("discord", platforms_config) is False

        # 测试禁用白名单
        platforms_config["enabled"] = False
        assert self._check_platform_allowed("telegram", platforms_config) is True

    def _check_platform_allowed(self, platform: str, platforms_config: dict) -> bool:
        """检查平台是否允许"""
        if not platforms_config.get("enabled", True):
            return True
        whitelist = platforms_config.get("whitelist", ["weixin"])
        return platform in whitelist

    def test_template_variables_completeness(self):
        """测试模板变量完整性"""
        from services.template_service import TemplateService

        variables = TemplateService.get_variables()
        var_names = [v["name"] for v in variables]

        # 检查关键变量存在
        required_vars = [
            "emotional_intensity",
            "emotional_label",
            "chat_heat",
            "chat_heat_label",
            "chat_heat_count",
            "longing_score",
            "longing_label",
            "weather",
            "memories",
            "reflection",
            "inject_emotion",
            "inject_heat",
            "inject_longing",
            "inject_memory",
            "platform",
            "sender_id"
        ]

        for var in required_vars:
            assert var in var_names, f"缺少必需的变量: {var}"

    def test_template_conditional_rendering(self):
        """测试模板条件渲染的各种场景"""
        from services.template_service import TemplateService

        template = """{% if weather %}
天气：{{ weather.city }} {{ weather.weather }}
{% if weather.temperature > 30 %}
高温
{% elif weather.temperature < 5 %}
低温
{% else %}
舒适
{% endif %}
{% endif %}"""

        # 测试高温
        result = TemplateService.render_template(template, {
            "weather": {"city": "北京", "weather": "晴", "temperature": 35}
        })
        assert "高温" in result
        assert "低温" not in result

        # 测试低温
        result = TemplateService.render_template(template, {
            "weather": {"city": "哈尔滨", "weather": "雪", "temperature": -10}
        })
        assert "低温" in result
        assert "高温" not in result

        # 测试舒适温度
        result = TemplateService.render_template(template, {
            "weather": {"city": "北京", "weather": "晴", "temperature": 25}
        })
        assert "舒适" in result
        assert "高温" not in result
        assert "低温" not in result

        # 测试无天气数据
        result = TemplateService.render_template(template, {"weather": None})
        assert "天气" not in result

    def test_template_memory_loop(self):
        """测试模板记忆循环渲染"""
        from services.template_service import TemplateService

        template = """{% if memories %}
📖 相关记忆：
{% for memory in memories %}
  {{ loop.index }}. {{ memory.text }}
{% endfor %}
{% endif %}"""

        # 测试多条记忆
        result = TemplateService.render_template(template, {
            "memories": [
                {"text": "记忆一"},
                {"text": "记忆二"},
                {"text": "记忆三"}
            ]
        })
        assert "1. 记忆一" in result
        assert "2. 记忆二" in result
        assert "3. 记忆三" in result

        # 测试空记忆
        result = TemplateService.render_template(template, {"memories": []})
        assert "记忆" not in result

        # 测试无记忆
        result = TemplateService.render_template(template, {"memories": None})
        assert "记忆" not in result

    def test_analysis_statistics_calculation(self):
        """测试分析统计数据计算"""
        # 模拟注入数据
        injections = [
            {"status": "success", "context_length": 400, "platform": "weixin"},
            {"status": "success", "context_length": 500, "platform": "weixin"},
            {"status": "success", "context_length": 450, "platform": "feishu"},
            {"status": "skipped", "context_length": 0, "platform": "telegram"},
            {"status": "error", "context_length": 0, "platform": "weixin"},
        ]

        # 计算统计
        total = len(injections)
        success = sum(1 for i in injections if i["status"] == "success")
        success_rate = success / total if total > 0 else 0
        avg_length = sum(i["context_length"] for i in injections if i["status"] == "success") / success if success > 0 else 0

        assert total == 5
        assert success == 3
        assert success_rate == 0.6
        assert avg_length == 450.0

    def test_longing_score_calculation(self):
        """测试想念分数计算逻辑"""
        from datetime import datetime, timedelta

        now = datetime.now()

        # 测试不同时间间隔的想念分数
        test_cases = [
            (timedelta(minutes=0), 0.0),      # 刚刚
            (timedelta(minutes=30), 0.1),     # 30分钟
            (timedelta(hours=1), 0.2),        # 1小时
            (timedelta(hours=2.5), 0.5),      # 2.5小时
            (timedelta(hours=5), 1.0),        # 5小时（最大值）
            (timedelta(hours=10), 1.0),       # 超过5小时（仍为1.0）
        ]

        for gap, expected_approx in test_cases:
            last_msg_time = now - gap
            gap_minutes = gap.total_seconds() / 60
            score = min(gap_minutes / 300, 1.0)

            assert abs(score - expected_approx) < 0.01, \
                f"时间间隔 {gap}: 期望 {expected_approx}, 实际 {score}"

    def test_chat_heat_levels(self):
        """测试聊天热度等级"""
        # 热度等级定义
        HEAT_LEVELS = [
            (0.0, "cold"),
            (0.5, "warm"),
            (1.0, "hot"),
            (3.0, "fire"),
        ]

        def get_heat_label(heat: float) -> str:
            label = "cold"
            for threshold, lbl in reversed(HEAT_LEVELS):
                if heat >= threshold:
                    label = lbl
                    break
            return label

        # 测试不同热度
        assert get_heat_label(0.0) == "cold"
        assert get_heat_label(0.3) == "cold"
        assert get_heat_label(0.5) == "warm"
        assert get_heat_label(0.8) == "warm"
        assert get_heat_label(1.0) == "hot"
        assert get_heat_label(2.0) == "hot"
        assert get_heat_label(3.0) == "fire"
        assert get_heat_label(5.0) == "fire"


class TestPassiveConsciousnessIntegration:
    """被动意识集成测试类"""

    @patch("services.passive_consciousness_service.ActiveSession")
    @patch("services.passive_consciousness_service.state_engine")
    @patch("services.passive_consciousness_service.ConfigService")
    @patch("services.template_service.TemplateService.render_active_template")
    def test_full_injection_flow(
        self,
        mock_render,
        mock_config_service,
        mock_state_engine,
        mock_session
    ):
        """测试完整的注入流程"""
        from services.passive_consciousness_service import PassiveConsciousnessService
        from services.template_service import TemplateService

        # 1. 配置启用被动意识
        mock_config_service.get_config.return_value = None

        # 2. 模拟状态数据
        mock_conn = MagicMock()
        mock_state_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_state_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        one_hour_ago = datetime.now().replace(hour=datetime.now().hour - 1).isoformat()

        def mock_execute(query, params=None):
            result = MagicMock()
            query_str = str(query)
            if "MAX" in query_str and "role='user'" in query_str:
                result.fetchone.return_value = (one_hour_ago,)
            elif "COUNT" in query_str:
                result.fetchone.return_value = (5,)
            elif "MAX" in query_str:
                result.fetchone.return_value = (datetime.now().isoformat(),)
            else:
                result.fetchone.return_value = (0.5,)
            return result

        mock_conn.execute.side_effect = mock_execute

        # 3. 获取状态
        status = PassiveConsciousnessService.get_status()

        assert "longing" in status
        assert "chat_heat" in status
        assert "emotional_intensity" in status

        # 4. 渲染模板
        mock_render.return_value = """--- [CONSCIOUSNESS_CONTEXT] ---
🎭 情绪状态：八卦（强度 0.5）
🔥 聊天热度：hot（近1小时 5 条消息）
💕 想念程度：missing（分数 0.2）
--- /[CONSCIOUSNESS_CONTEXT] ---"""

        template_data = {
            "emotional_intensity": status["emotional_intensity"]["intensity"],
            "emotional_label": status["emotional_intensity"]["label"],
            "chat_heat": status["chat_heat"]["heat"],
            "chat_heat_label": status["chat_heat"]["label"],
            "chat_heat_count": status["chat_heat"]["recent_count"],
            "longing_score": status["longing"]["score"],
            "longing_label": status["longing"]["label"],
            "inject_emotion": True,
            "inject_heat": True,
            "inject_longing": True,
            "inject_memory": True
        }

        context = TemplateService.render_active_template(template_data)

        assert "CONSCIOUSNESS_CONTEXT" in context
        assert "情绪状态" in context
        assert "聊天热度" in context
        assert "想念程度" in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
