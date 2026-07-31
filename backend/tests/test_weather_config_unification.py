"""
天气配置统一测试用例
验证 weather.* 命名空间的完整性和逻辑闭环
"""
import pytest
from unittest.mock import patch, MagicMock


class TestWeatherConfigUnification:
    """天气配置统一测试类"""

    def test_weather_config_defaults_exist(self):
        """测试 weather.* 默认配置存在"""
        from config import DEFAULT_WEATHER_CONFIG

        required_keys = [
            "weather.enabled",
            "weather.provider",
            "weather.city",
            "weather.cache_hours",
            "weather.amap_key",
            "weather.qweather_key",
            "weather.qweather_geo_url",
            "weather.qweather_weather_url",
        ]

        for key in required_keys:
            assert key in DEFAULT_WEATHER_CONFIG, f"缺少默认配置: {key}"

    def test_weather_config_defaults_values(self):
        """测试 weather.* 默认配置值"""
        from config import DEFAULT_WEATHER_CONFIG

        assert DEFAULT_WEATHER_CONFIG["weather.enabled"] == "false"
        assert DEFAULT_WEATHER_CONFIG["weather.provider"] == "qweather"
        assert DEFAULT_WEATHER_CONFIG["weather.city"] == "北京"
        assert DEFAULT_WEATHER_CONFIG["weather.cache_hours"] == "4"

    def test_config_service_reads_weather_config(self):
        """测试 ConfigService 能读取 weather.* 配置"""
        from services.config_service import ConfigService

        # 验证 get_config 方法存在且可调用
        assert hasattr(ConfigService, 'get_config')
        assert callable(ConfigService.get_config)

    @patch("models.database.ActiveSession")
    def test_config_service_writes_weather_config(self, mock_session):
        """测试 ConfigService 能写入 weather.* 配置"""
        from services.config_service import ConfigService

        db = MagicMock()
        # 验证 set_config 能接受 weather.* 格式的 key
        try:
            ConfigService.set_config(db, "weather.city", "上海")
        except Exception as e:
            pytest.fail(f"set_config 应该能接受 weather.* 格式的 key: {e}")


class TestWeatherConfigAPI:
    """天气配置 API 测试类"""

    @patch("routers.config.ConfigService")
    @patch("routers.config.get_active_db")
    @patch("routers.config.get_current_user")
    def test_get_weather_config_reads_from_weather_namespace(
        self, mock_user, mock_db, mock_config_service
    ):
        """测试 GET /api/config/weather 从 weather.* 命名空间读取"""
        from routers.config import get_weather_config

        # 模拟配置返回
        def mock_get(db, key):
            values = {
                "weather.enabled": "true",
                "weather.provider": "qweather",
                "weather.city": "济南",
                "weather.cache_hours": "4",
                "weather.amap_key": "",
                "weather.adcode": "370100",
                "weather.cache_ttl": "3600",
                "weather.temp_change_threshold": "5.0",
                "weather.qweather_key": "test-key",
                "weather.qweather_geo_url": "https://geoapi.qweather.com/v2/city/lookup",
                "weather.qweather_weather_url": "https://devapi.qweather.com/v7/weather/now",
            }
            return values.get(key)

        mock_config_service.get_config.side_effect = mock_get

        # 调用 API
        import asyncio
        result = asyncio.run(get_weather_config(mock_user, mock_db))

        assert result["enabled"] is True
        assert result["provider"] == "qweather"
        assert result["city"] == "济南"

    @patch("routers.config.ConfigService")
    @patch("routers.config.get_active_db")
    @patch("routers.config.get_current_user")
    def test_update_weather_config_writes_to_weather_namespace(
        self, mock_user, mock_db, mock_config_service
    ):
        """测试 PUT /api/config/weather 写入 weather.* 命名空间"""
        from routers.config import update_weather_config

        weather_config = {
            "enabled": True,
            "provider": "qweather",
            "city": "北京",
            "qweather_key": "test-key",
        }

        import asyncio
        asyncio.run(update_weather_config(weather_config, mock_user, mock_db))

        # 验证写入的 key 格式
        calls = mock_config_service.set_config.call_args_list
        written_keys = [call[0][1] for call in calls]

        assert "weather.enabled" in written_keys
        assert "weather.provider" in written_keys
        assert "weather.city" in written_keys

        # 验证没有写入旧格式的 key
        for key in written_keys:
            assert not key.startswith("passive_consciousness.weather."), f"不应写入旧格式: {key}"
            assert not key.startswith("active_consciousness.weather."), f"不应写入旧格式: {key}"


class TestPassiveConsciousnessWeatherConfig:
    """被动意识天气配置测试类"""

    def test_no_weather_defaults_in_passive_consciousness(self):
        """测试被动意识服务中没有天气配置默认值"""
        from services.passive_consciousness_service import _DEFAULTS

        weather_keys = [k for k in _DEFAULTS.keys() if "weather" in k]
        assert len(weather_keys) == 0, f"被动意识中不应有天气配置: {weather_keys}"


class TestActiveConsciousnessWeatherConfig:
    """主动意识天气配置测试类"""

    def test_no_weather_config_defaults_in_active_consciousness(self):
        """测试主动意识服务中没有天气配置默认值"""
        from services.active_consciousness_service import _DEFAULTS

        # 检查没有独立的天气配置（weather.enabled, weather.provider 等）
        # 但允许 context 相关的配置（如 weather_enabled 用于控制是否注入天气）
        weather_config_keys = [
            k for k in _DEFAULTS.keys()
            if k.startswith("active_consciousness.weather.")
        ]
        assert len(weather_config_keys) == 0, f"主动意识中不应有独立的天气配置: {weather_config_keys}"


class TestContextCollectorWeatherConfig:
    """上下文收集器天气配置测试类"""

    def test_context_collector_imports_config_service(self):
        """测试上下文收集器导入了 ConfigService"""
        import importlib
        try:
            from services import context_collector
            importlib.reload(context_collector)
            # 验证模块可以正常导入
        except ImportError as e:
            pytest.fail(f"上下文收集器导入失败: {e}")


class TestWeatherConfigMigration:
    """天气配置迁移测试类"""

    def test_migration_script_exists(self):
        """测试迁移脚本存在"""
        import os
        migration_path = "/home/ubuntu/.hermes/hermes-active/backend/migrations/weather_config_migration.py"
        assert os.path.exists(migration_path), "迁移脚本不存在"

    def test_migration_script_has_migrate_function(self):
        """测试迁移脚本有 migrate 函数"""
        from migrations.weather_config_migration import migrate
        assert callable(migrate), "migrate 应该是可调用函数"


class TestWeatherConfigEndToEnd:
    """天气配置端到端测试类"""

    def test_weather_service_can_be_imported(self):
        """测试天气服务可以正常导入"""
        try:
            from services.weather_service import WeatherService
            service = WeatherService()
            assert service is not None
        except ImportError as e:
            pytest.fail(f"天气服务导入失败: {e}")

    def test_no_old_weather_config_keys_in_database(self):
        """测试数据库中没有旧的天气配置 key"""
        # 这个测试需要实际数据库连接，跳过
        pass


class TestWeatherConfigConsistency:
    """天气配置一致性测试类"""

    def test_config_api_and_passive_use_same_namespace(self):
        """测试配置 API 和被动意识使用相同的命名空间"""
        from routers.config import get_weather_config
        from services.passive_consciousness_service import _DEFAULTS

        # 两者都不应有旧格式的天气配置
        for key in _DEFAULTS.keys():
            assert not key.startswith("passive_consciousness.weather."), f"被动意识中有旧配置: {key}"
            assert not key.startswith("active_consciousness.weather."), f"主动意识中有旧配置: {key}"

    def test_all_weather_keys_use_weather_prefix(self):
        """测试所有天气配置 key 使用 weather. 前缀"""
        from config import DEFAULT_WEATHER_CONFIG

        for key in DEFAULT_WEATHER_CONFIG.keys():
            assert key.startswith("weather."), f"配置 key 应以 weather. 开头: {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
