"""
被动意识 API 端点测试用例
测试所有被动意识相关的 API 端点
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端"""
    from main import app
    return TestClient(app)


class TestPlatformAPI:
    """平台配置 API 测试类"""

    @patch("routers.passive_consciousness.PassiveConsciousnessService")
    def test_get_platforms(self, mock_service, client):
        """测试获取平台配置"""
        mock_service.get_config.return_value = {
            "platforms": {
                "enabled": True,
                "whitelist": ["weixin", "feishu"]
            }
        }

        response = client.get("/api/passive-consciousness/platforms")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert "weixin" in data["whitelist"]
        assert "feishu" in data["whitelist"]

    @patch("routers.passive_consciousness.PassiveConsciousnessService")
    def test_update_platforms(self, mock_service, client):
        """测试更新平台配置"""
        mock_service.get_config.return_value = {}
        mock_service.update_config.return_value = None

        new_config = {
            "enabled": True,
            "whitelist": ["weixin", "telegram"]
        }

        response = client.put(
            "/api/passive-consciousness/platforms",
            json=new_config
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_get_available_platforms(self, client):
        """测试获取可用平台列表"""
        response = client.get("/api/passive-consciousness/platforms/available")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

        platforms = data["data"]
        platform_ids = [p["id"] for p in platforms]
        assert "weixin" in platform_ids
        assert "feishu" in platform_ids
        assert "telegram" in platform_ids
        assert "discord" in platform_ids
        assert "slack" in platform_ids


class TestWeatherAPI:
    """天气 API 测试类"""

    @patch("routers.passive_consciousness.PassiveConsciousnessService")
    def test_get_weather_disabled(self, mock_service, client):
        """测试天气未启用时获取天气"""
        mock_service.get_config.return_value = {
            "weather": {"enabled": False}
        }

        response = client.get("/api/passive-consciousness/weather")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "未启用" in data["error"]

    @patch("routers.passive_consciousness.PassiveConsciousnessService")
    @patch("routers.passive_consciousness.WeatherService")
    def test_get_weather_enabled(self, mock_weather_service, mock_service, client):
        """测试天气启用时获取天气"""
        mock_service.get_config.return_value = {
            "weather": {
                "enabled": True,
                "provider": "qweather",
                "city": "北京",
                "cache_hours": 4
            }
        }

        mock_weather_instance = MagicMock()
        mock_weather_instance.get_weather.return_value = {
            "success": True,
            "data": {
                "city": "北京",
                "weather": "晴",
                "temperature": 28,
                "humidity": 45
            }
        }
        mock_weather_service.return_value = mock_weather_instance

        response = client.get("/api/passive-consciousness/weather")

        assert response.status_code == 200

    @patch("routers.passive_consciousness.PassiveConsciousnessService")
    def test_get_weather_status(self, mock_service, client):
        """测试获取天气服务状态"""
        mock_service.get_config.return_value = {
            "weather": {
                "enabled": True,
                "provider": "qweather",
                "city": "北京"
            }
        }

        response = client.get("/api/passive-consciousness/weather/status")

        assert response.status_code == 200


class TestTemplateAPI:
    """模板 API 测试类"""

    @patch("routers.passive_consciousness.TemplateService")
    def test_get_templates(self, mock_template_service, client):
        """测试获取模板列表"""
        mock_template_service.get_templates.return_value = [
            {
                "id": "default",
                "name": "日常模板",
                "description": "默认的上下文注入模板",
                "content": "测试内容",
                "is_default": True
            }
        ]

        response = client.get("/api/passive-consciousness/templates")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "default"

    @patch("routers.passive_consciousness.TemplateService")
    def test_get_template_by_id(self, mock_template_service, client):
        """测试获取单个模板"""
        mock_template_service.get_template.return_value = {
            "id": "default",
            "name": "日常模板",
            "content": "测试内容"
        }

        response = client.get("/api/passive-consciousness/templates/default")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == "default"

    @patch("routers.passive_consciousness.TemplateService")
    def test_get_template_not_found(self, mock_template_service, client):
        """测试获取不存在的模板"""
        mock_template_service.get_template.return_value = None

        response = client.get("/api/passive-consciousness/templates/nonexistent")

        assert response.status_code == 404

    @patch("routers.passive_consciousness.PassiveConsciousnessService")
    @patch("routers.passive_consciousness.TemplateService")
    def test_create_template(self, mock_template_service, mock_service, client):
        """测试创建模板"""
        mock_template_service.get_template.return_value = None
        mock_template_service.get_templates.return_value = []
        mock_service.get_config.return_value = {"templates": {}}
        mock_service.update_config.return_value = None

        new_template = {
            "id": "custom",
            "name": "自定义模板",
            "description": "自定义描述",
            "content": "自定义内容"
        }

        response = client.post(
            "/api/passive-consciousness/templates",
            json=new_template
        )

        assert response.status_code == 200

    @patch("routers.passive_consciousness.TemplateService")
    def test_create_template_duplicate_id(self, mock_template_service, client):
        """测试创建重复 ID 的模板"""
        mock_template_service.get_template.return_value = {
            "id": "default",
            "name": "已存在"
        }

        new_template = {
            "id": "default",
            "name": "重复模板",
            "content": "内容"
        }

        response = client.post(
            "/api/passive-consciousness/templates",
            json=new_template
        )

        assert response.status_code == 400

    @patch("routers.passive_consciousness.TemplateService")
    def test_get_template_variables(self, mock_template_service, client):
        """测试获取模板变量列表"""
        mock_template_service.get_variables.return_value = [
            {"name": "emotional_intensity", "type": "float", "description": "情绪强度"},
            {"name": "emotional_label", "type": "string", "description": "情绪标签"}
        ]

        response = client.get("/api/passive-consciousness/templates/variables")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    @patch("routers.passive_consciousness.TemplateService")
    def test_preview_template(self, mock_template_service, client):
        """测试预览模板"""
        mock_template_service.get_template.return_value = {
            "id": "default",
            "content": "{{ emotional_label }}"
        }
        mock_template_service.preview_template.return_value = "八卦"

        response = client.post(
            "/api/passive-consciousness/templates/default/preview",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert "preview" in data["data"]

    @patch("routers.passive_consciousness.TemplateService")
    def test_render_template(self, mock_template_service, client):
        """测试渲染模板"""
        mock_template_service.render_active_template.return_value = "渲染结果"

        render_data = {
            "emotional_label": "八卦",
            "inject_emotion": True
        }

        response = client.post(
            "/api/passive-consciousness/templates/render",
            json=render_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "context" in data["data"]


class TestAnalysisAPI:
    """分析 API 测试类"""

    @patch("routers.passive_consciousness.AnalysisService")
    def test_get_analysis_stats(self, mock_analysis_service, client):
        """测试获取注入统计"""
        mock_analysis_service.get_injection_stats.return_value = {
            "total_injections": 100,
            "success_count": 80,
            "success_rate": 0.8,
            "avg_context_length": 450
        }

        response = client.get("/api/passive-consciousness/analysis/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_injections"] == 100
        assert data["data"]["success_rate"] == 0.8

    @patch("routers.passive_consciousness.AnalysisService")
    def test_get_analysis_stats_with_params(self, mock_analysis_service, client):
        """测试带参数获取注入统计"""
        mock_analysis_service.get_injection_stats.return_value = {
            "total_injections": 50,
            "success_count": 45,
            "success_rate": 0.9
        }

        response = client.get(
            "/api/passive-consciousness/analysis/stats",
            params={"hours": 48, "platform": "weixin"}
        )

        assert response.status_code == 200
        mock_analysis_service.get_injection_stats.assert_called_once_with(48, "weixin")

    @patch("routers.passive_consciousness.AnalysisService")
    def test_get_analysis_trends(self, mock_analysis_service, client):
        """测试获取趋势数据"""
        mock_analysis_service.get_trend_data.return_value = {
            "data_points": [
                {"timestamp": "2026-07-31T10:00:00", "value": 0.5},
                {"timestamp": "2026-07-31T11:00:00", "value": 0.6}
            ],
            "statistics": {
                "avg": 0.55,
                "max": 0.6,
                "min": 0.5
            }
        }

        response = client.get("/api/passive-consciousness/analysis/trends")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["data_points"]) == 2

    @patch("routers.passive_consciousness.AnalysisService")
    def test_get_analysis_sentiment(self, mock_analysis_service, client):
        """测试获取情感分析"""
        mock_analysis_service.get_sentiment_analysis.return_value = {
            "emotional_distribution": {
                "工作": 30,
                "日常": 40,
                "八卦": 20
            },
            "avg_emotional_intensity": 0.55,
            "avg_longing_score": 0.35
        }

        response = client.get("/api/passive-consciousness/analysis/sentiment")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "emotional_distribution" in data["data"]

    @patch("routers.passive_consciousness.AnalysisService")
    def test_get_analysis_stats_error(self, mock_analysis_service, client):
        """测试获取注入统计错误处理"""
        mock_analysis_service.get_injection_stats.side_effect = Exception("Database error")

        response = client.get("/api/passive-consciousness/analysis/stats")

        assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
