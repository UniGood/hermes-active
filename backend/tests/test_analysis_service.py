"""
分析服务测试用例
测试 AnalysisService 的所有功能
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestAnalysisService:
    """AnalysisService 测试类"""

    @patch("services.analysis_service.active_engine")
    def test_get_injection_stats_empty(self, mock_engine):
        """测试空数据的注入统计"""
        from services.analysis_service import AnalysisService

        # 模拟空查询结果
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟所有查询返回 0
        mock_conn.execute.return_value.fetchone.return_value = (0, 0, 0, 0, 0, 0, 0, 0)
        mock_conn.execute.return_value.fetchall.return_value = []

        stats = AnalysisService.get_injection_stats(hours=24)

        assert stats["total"] == 0
        assert stats["success"] == 0
        assert stats["success_rate"] == 0.0

    @patch("services.analysis_service.active_engine")
    def test_get_injection_stats_with_data(self, mock_engine):
        """测试有数据的注入统计"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟查询结果
        def mock_execute(query, params=None):
            result = MagicMock()
            query_str = str(query)
            if "COUNT(*) AS total" in query_str:
                # 总体统计查询
                result.fetchone.return_value = (100, 80, 15, 5, 450.5, 0.35, 1.8, 0.55)
            elif "GROUP BY platform" in query_str:
                # 按平台分组
                result.fetchall.return_value = [("weixin", 60), ("feishu", 40)]
            elif "GROUP BY tid" in query_str:
                # 按模板分组
                result.fetchall.return_value = [("default", 70), ("custom", 30)]
            elif "GROUP BY hour" in query_str:
                # 按小时分组
                result.fetchall.return_value = [
                    ("2026-07-31 10:00", 20),
                    ("2026-07-31 11:00", 30),
                    ("2026-07-31 12:00", 50)
                ]
            else:
                result.fetchone.return_value = (0, 0, 0, 0, 0, 0, 0, 0)
                result.fetchall.return_value = []
            return result

        mock_conn.execute.side_effect = mock_execute

        stats = AnalysisService.get_injection_stats(hours=24)

        assert stats["total"] == 100
        assert stats["success"] == 80
        assert stats["success_rate"] == 0.8
        assert stats["avg_context_length"] == 450.5
        assert len(stats["by_platform"]) == 2
        assert stats["by_platform"][0]["platform"] == "weixin"
        assert stats["by_platform"][0]["count"] == 60
        assert len(stats["by_template"]) == 2
        assert len(stats["by_hour"]) == 3

    @patch("services.analysis_service.active_engine")
    def test_get_injection_stats_with_platform_filter(self, mock_engine):
        """测试按平台过滤的注入统计"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.return_value.fetchone.return_value = (50, 45, 3, 2, 400.0, 0.3, 1.5, 0.5)
        mock_conn.execute.return_value.fetchall.return_value = [("weixin", 50)]

        stats = AnalysisService.get_injection_stats(hours=24, platform="weixin")

        # 验证查询中包含平台过滤条件
        calls = mock_conn.execute.call_args_list
        for call in calls:
            query = str(call[0][0])
            if "WHERE" in query:
                assert "platform" in query

    @patch("services.analysis_service.active_engine")
    def test_get_trend_data_hourly(self, mock_engine):
        """测试小时级趋势数据"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟趋势数据
        trend_data = [
            (f"2026-07-31 {i:02d}:00", 10 + i, 8 + i, 0.3 + i * 0.05, 1.5 + i * 0.1, 0.5 + i * 0.02, 400 + i * 10)
            for i in range(24)
        ]

        mock_conn.execute.return_value.fetchall.return_value = trend_data

        trends = AnalysisService.get_trend_data(hours=24, interval="hour")

        assert "interval" in trends
        assert trends["interval"] == "hour"
        assert "data" in trends
        assert len(trends["data"]) == 24
        assert "period" in trends["data"][0]
        assert "count" in trends["data"][0]

    @patch("services.analysis_service.active_engine")
    def test_get_trend_data_daily(self, mock_engine):
        """测试天级趋势数据"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟 7 天的趋势数据
        trend_data = [
            (f"2026-07-{25 + i}", 50 + i * 5, 40 + i * 4, 0.3 + i * 0.05, 1.5, 0.5, 400)
            for i in range(7)
        ]

        mock_conn.execute.return_value.fetchall.return_value = trend_data

        trends = AnalysisService.get_trend_data(hours=168, interval="day")

        assert len(trends["data"]) == 7

    @patch("services.analysis_service.active_engine")
    def test_get_trend_data_empty(self, mock_engine):
        """测试空趋势数据"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.return_value.fetchall.return_value = []

        trends = AnalysisService.get_trend_data(hours=24, interval="hour")

        assert len(trends["data"]) == 0

    @patch("services.analysis_service.active_engine")
    def test_get_sentiment_analysis_with_data(self, mock_engine):
        """测试有数据的情感分析"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟情感分布数据
        def mock_execute(query, params=None):
            result = MagicMock()
            query_str = str(query)
            if "emotional_label" in query_str and "COUNT" in query_str:
                result.fetchall.return_value = [
                    ("工作", 30),
                    ("日常", 40),
                    ("八卦", 20),
                    ("情感", 10)
                ]
            elif "longing_label" in query_str and "COUNT" in query_str:
                result.fetchall.return_value = [
                    ("calm", 50),
                    ("missing", 30),
                    ("yearning", 20)
                ]
            elif "chat_heat_label" in query_str and "COUNT" in query_str:
                result.fetchall.return_value = [
                    ("cold", 40),
                    ("warm", 35),
                    ("hot", 25)
                ]
            elif "AVG" in query_str and "longing_score" in query_str:
                result.fetchone.return_value = (0.35, 1.8, 0.55)
            elif "SUM" in query_str and "emotional_intensity" in query_str:
                result.fetchone.return_value = (15, 20)
            else:
                result.fetchone.return_value = (0, 0, 0)
                result.fetchall.return_value = []
            return result

        mock_conn.execute.side_effect = mock_execute

        sentiment = AnalysisService.get_sentiment_analysis(hours=72)

        assert "emotional_distribution" in sentiment
        assert "longing_distribution" in sentiment
        assert "heat_distribution" in sentiment
        assert "avg_scores" in sentiment
        assert "correlation" in sentiment

        assert len(sentiment["emotional_distribution"]) == 4
        # 验证分布数据包含所有标签
        labels = [d["label"] for d in sentiment["emotional_distribution"]]
        assert "工作" in labels
        assert "日常" in labels
        assert "八卦" in labels
        assert "情感" in labels

        assert sentiment["avg_scores"]["longing"] == 0.35
        assert sentiment["avg_scores"]["heat"] == 1.8
        assert sentiment["avg_scores"]["emotion"] == 0.55

    @patch("services.analysis_service.active_engine")
    def test_get_sentiment_analysis_empty(self, mock_engine):
        """测试空情感分析"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.return_value.fetchone.return_value = (0, 0, 0)
        mock_conn.execute.return_value.fetchall.return_value = []

        sentiment = AnalysisService.get_sentiment_analysis(hours=72)

        assert sentiment["emotional_distribution"] == []
        assert sentiment["avg_scores"]["longing"] == 0

    @patch("services.analysis_service.active_engine")
    def test_get_injection_stats_error_handling(self, mock_engine):
        """测试注入统计错误处理"""
        from services.analysis_service import AnalysisService

        mock_engine.connect.side_effect = Exception("Database connection failed")

        stats = AnalysisService.get_injection_stats(hours=24)

        # 错误时返回默认值，不抛出异常
        assert stats["total"] == 0
        assert "error_message" in stats

    @patch("services.analysis_service.active_engine")
    def test_get_trend_data_error_handling(self, mock_engine):
        """测试趋势数据错误处理"""
        from services.analysis_service import AnalysisService

        mock_engine.connect.side_effect = Exception("Database connection failed")

        trends = AnalysisService.get_trend_data(hours=24)

        # 错误时返回默认值，不抛出异常
        assert trends["data"] == []
        assert "error_message" in trends

    @patch("services.analysis_service.active_engine")
    def test_get_sentiment_analysis_error_handling(self, mock_engine):
        """测试情感分析错误处理"""
        from services.analysis_service import AnalysisService

        mock_engine.connect.side_effect = Exception("Database connection failed")

        sentiment = AnalysisService.get_sentiment_analysis(hours=72)

        # 错误时返回默认值，不抛出异常
        assert sentiment["emotional_distribution"] == []
        assert "error_message" in sentiment

    @patch("services.analysis_service.active_engine")
    def test_get_injection_stats_success_rate_calculation(self, mock_engine):
        """测试成功率计算"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟 100 次注入，80 次成功
        mock_conn.execute.return_value.fetchone.return_value = (100, 80, 15, 5, 450.0, 0.35, 1.8, 0.55)
        mock_conn.execute.return_value.fetchall.return_value = []

        stats = AnalysisService.get_injection_stats(hours=24)

        assert stats["success_rate"] == 0.8

    @patch("services.analysis_service.active_engine")
    def test_get_injection_stats_zero_total(self, mock_engine):
        """测试总数为 0 时的成功率计算"""
        from services.analysis_service import AnalysisService

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟 0 次注入
        mock_conn.execute.return_value.fetchone.return_value = (0, 0, 0, 0, 0, 0, 0, 0)
        mock_conn.execute.return_value.fetchall.return_value = []

        stats = AnalysisService.get_injection_stats(hours=24)

        assert stats["success_rate"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
