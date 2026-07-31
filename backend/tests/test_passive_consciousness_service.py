"""
被动意识服务测试用例
测试 PassiveConsciousnessService 的配置读写、状态查询等功能
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestPassiveConsciousnessConfig:
    """被动意识配置测试类"""

    @patch("services.passive_consciousness_service.ActiveSession")
    @patch("services.passive_consciousness_service.ConfigService")
    def test_get_config_returns_defaults(self, mock_config_service, mock_session):
        """测试获取配置返回默认值"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        # 模拟 ConfigService 返回 None（使用默认值）
        mock_config_service.get_config.return_value = None

        config = PassiveConsciousnessService.get_config()

        assert config["enabled"] is False
        assert config["platforms"]["enabled"] is False
        assert config["platforms"]["whitelist"] == ["weixin"]
        assert config["templates"]["active_id"] == "default"

    @patch("services.passive_consciousness_service.ActiveSession")
    @patch("services.passive_consciousness_service.ConfigService")
    def test_get_config_with_custom_values(self, mock_config_service, mock_session):
        """测试获取配置返回自定义值"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        # 模拟 ConfigService 返回自定义值
        def mock_get_config(db, key):
            values = {
                "passive_consciousness.enabled": "true",
                "passive_consciousness.platforms.enabled": "true",
                "passive_consciousness.platforms.whitelist": '["weixin", "feishu", "telegram"]',
                "passive_consciousness.templates.active_id": "custom",
            }
            return values.get(key)

        mock_config_service.get_config.side_effect = mock_get_config

        config = PassiveConsciousnessService.get_config()

        assert config["enabled"] is True
        assert config["platforms"]["enabled"] is True
        assert "weixin" in config["platforms"]["whitelist"]
        assert "feishu" in config["platforms"]["whitelist"]
        assert "telegram" in config["platforms"]["whitelist"]
        assert config["templates"]["active_id"] == "custom"

    @patch("services.passive_consciousness_service.ActiveSession")
    @patch("services.passive_consciousness_service.ConfigService")
    def test_update_config(self, mock_config_service, mock_session):
        """测试更新配置"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        mock_db = MagicMock()
        mock_session.return_value = mock_db

        new_config = {
            "enabled": True,
            "platforms": {
                "enabled": True,
                "whitelist": ["weixin", "feishu"]
            }
        }

        PassiveConsciousnessService.update_config(new_config)

        # 验证 ConfigService.set_config 被调用
        assert mock_config_service.set_config.call_count > 0

    def test_flat_to_nested_conversion(self):
        """测试扁平 key 到嵌套 dict 的转换"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        flat = {
            "passive_consciousness.enabled": "true",
            "passive_consciousness.platforms.enabled": "true",
            "passive_consciousness.platforms.whitelist": '["weixin"]',
            "passive_consciousness.llm.mode": "hermes",
        }

        nested = PassiveConsciousnessService._flat_to_nested(flat)

        assert nested["enabled"] is True
        assert nested["platforms"]["enabled"] is True
        assert nested["platforms"]["whitelist"] == ["weixin"]
        assert nested["llm"]["mode"] == "hermes"

    def test_nested_to_flat_conversion(self):
        """测试嵌套 dict 到扁平 key 的转换"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        nested = {
            "enabled": True,
            "platforms": {
                "enabled": True,
                "whitelist": ["weixin", "feishu"]
            }
        }

        flat = PassiveConsciousnessService._nested_to_flat(nested)

        assert flat["passive_consciousness.enabled"] == "true"
        assert flat["passive_consciousness.platforms.enabled"] == "true"
        assert '"weixin"' in flat["passive_consciousness.platforms.whitelist"]
        assert '"feishu"' in flat["passive_consciousness.platforms.whitelist"]

    def test_flat_to_nested_boolean_conversion(self):
        """测试布尔值转换"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        flat = {
            "passive_consciousness.enabled": "true",
            "passive_consciousness.passive.inject_emotion": "false",
        }

        nested = PassiveConsciousnessService._flat_to_nested(flat)

        assert nested["enabled"] is True
        assert nested["passive"]["inject_emotion"] is False

    def test_flat_to_nested_json_conversion(self):
        """测试 JSON 值转换"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        flat = {
            "passive_consciousness.platforms.whitelist": '["weixin", "feishu"]',
            "passive_consciousness.session.sources": '["weixin"]',
        }

        nested = PassiveConsciousnessService._flat_to_nested(flat)

        assert isinstance(nested["platforms"]["whitelist"], list)
        assert len(nested["platforms"]["whitelist"]) == 2
        assert isinstance(nested["session"]["sources"], list)

    def test_flat_to_nested_number_conversion(self):
        """测试数字值转换"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        flat = {
            "passive_consciousness.passive.thought_max_chars": "200",
            "passive_consciousness.session.time_range_hours": "24",
        }

        nested = PassiveConsciousnessService._flat_to_nested(flat)

        assert nested["passive"]["thought_max_chars"] == 200
        assert nested["session"]["time_range_hours"] == 24


class TestPassiveConsciousnessStatus:
    """被动意识状态测试类"""

    @patch("services.passive_consciousness_service.ActiveSession")
    @patch("services.passive_consciousness_service.state_engine")
    @patch("services.passive_consciousness_service.PassiveConsciousnessService.get_config")
    def test_get_status_basic(self, mock_get_config, mock_state_engine, mock_session):
        """测试获取基本状态"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        mock_get_config.return_value = {
            "enabled": True,
            "weather": {"enabled": False},
            "platforms": {"enabled": True, "whitelist": ["weixin"]}
        }

        mock_conn = MagicMock()
        mock_state_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_state_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟数据库查询
        mock_conn.execute.return_value.fetchone.return_value = (None,)

        status = PassiveConsciousnessService.get_status()

        assert "enabled" in status
        assert "longing" in status
        assert "chat_heat" in status
        assert "emotional_intensity" in status
        assert "weather" in status

    @patch("services.passive_consciousness_service.ActiveSession")
    @patch("services.passive_consciousness_service.state_engine")
    @patch("services.passive_consciousness_service.PassiveConsciousnessService.get_config")
    def test_get_status_longing_calculation(self, mock_get_config, mock_state_engine, mock_session):
        """测试想念分数计算"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        mock_get_config.return_value = {
            "enabled": True,
            "weather": {"enabled": False}
        }

        mock_conn = MagicMock()
        mock_state_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_state_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟最近用户消息时间为 1 小时前
        one_hour_ago = datetime.now().replace(hour=datetime.now().hour - 1).isoformat()

        def mock_execute(query, params=None):
            result = MagicMock()
            query_str = str(query)
            if "MAX" in query_str and "role='user'" in query_str:
                result.fetchone.return_value = (one_hour_ago,)
            else:
                result.fetchone.return_value = (None,)
            return result

        mock_conn.execute.side_effect = mock_execute

        status = PassiveConsciousnessService.get_status()

        # 1 小时 = 60 分钟，60/300 = 0.2
        assert status["longing"]["score"] > 0
        assert status["longing"]["score"] <= 1.0

    def test_intensity_label_mapping(self):
        """测试情绪强度标签映射"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        assert PassiveConsciousnessService._intensity_label(0.1) == "工作"
        assert PassiveConsciousnessService._intensity_label(0.3) == "日常"
        assert PassiveConsciousnessService._intensity_label(0.5) == "八卦"
        assert PassiveConsciousnessService._intensity_label(0.7) == "情感"
        assert PassiveConsciousnessService._intensity_label(0.9) == "深度情感"


class TestPassiveConsciousnessChats:
    """被动意识聊天记录测试类"""

    @patch("services.passive_consciousness_service.ActiveSession")
    @patch("services.passive_consciousness_service.state_engine")
    def test_get_chats(self, mock_state_engine, mock_session):
        """测试获取聊天记录"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        mock_conn = MagicMock()
        mock_state_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_state_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟聊天记录
        mock_row1 = MagicMock()
        mock_row1._mapping = {
            "id": 1,
            "session_id": "session1",
            "source": "weixin",
            "role": "user",
            "content": "你好",
            "timestamp": "2026-07-31T10:00:00"
        }
        mock_row2 = MagicMock()
        mock_row2._mapping = {
            "id": 2,
            "session_id": "session1",
            "source": "weixin",
            "role": "assistant",
            "content": "你好！",
            "timestamp": "2026-07-31T10:00:01"
        }

        mock_conn.execute.return_value.fetchall.return_value = [mock_row1, mock_row2]

        chats = PassiveConsciousnessService.get_chats(limit=10)

        assert chats["total"] == 2
        assert len(chats["items"]) == 2
        assert chats["items"][0]["role"] == "user"
        assert chats["items"][1]["role"] == "assistant"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
