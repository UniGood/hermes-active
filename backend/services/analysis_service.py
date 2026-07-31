"""
分析服务 — 被动意识注入效果分析

提供注入统计、趋势数据、情感分析等功能，
数据来源为 passive_consciousness_logs 表。
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy import text

from models.database import active_engine

logger = logging.getLogger("hermes.analysis")


class AnalysisService:
    """被动意识注入分析服务"""

    @staticmethod
    def get_injection_stats(
        hours: int = 24,
        platform: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取注入统计

        Args:
            hours: 统计时间范围（小时），默认 24
            platform: 按平台筛选（可选）

        Returns:
            {
                "total": int,
                "success": int,
                "skipped": int,
                "error": int,
                "success_rate": float,
                "avg_context_length": float,
                "avg_longing_score": float,
                "avg_chat_heat": float,
                "avg_emotional_intensity": float,
                "by_platform": [{"platform": str, "count": int}],
                "by_template": [{"template_id": str, "count": int}],
                "by_hour": [{"hour": str, "count": int}],
            }
        """
        try:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            params: Dict[str, Any] = {"since": since}

            platform_filter = ""
            if platform:
                platform_filter = "AND platform = :platform"
                params["platform"] = platform

            with active_engine.connect() as conn:
                # 总体统计
                row = conn.execute(text(f"""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success,
                        SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) AS skipped,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error,
                        AVG(CASE WHEN status = 'success' THEN context_length END) AS avg_context_length,
                        AVG(longing_score) AS avg_longing,
                        AVG(chat_heat) AS avg_heat,
                        AVG(emotional_intensity) AS avg_emotion
                    FROM passive_consciousness_logs
                    WHERE timestamp > :since {platform_filter}
                """), params).fetchone()

                total = row[0] or 0
                success = row[1] or 0
                skipped = row[2] or 0
                error = row[3] or 0
                success_rate = round(success / total, 4) if total > 0 else 0.0

                # 按平台分组
                platform_rows = conn.execute(text(f"""
                    SELECT platform, COUNT(*) AS cnt
                    FROM passive_consciousness_logs
                    WHERE timestamp > :since {platform_filter}
                    GROUP BY platform
                    ORDER BY cnt DESC
                """), params).fetchall()
                by_platform = [
                    {"platform": r[0] or "unknown", "count": r[1]}
                    for r in platform_rows
                ]

                # 按模板分组
                template_rows = conn.execute(text(f"""
                    SELECT COALESCE(template_id, 'unknown') AS tid, COUNT(*) AS cnt
                    FROM passive_consciousness_logs
                    WHERE timestamp > :since {platform_filter}
                    GROUP BY tid
                    ORDER BY cnt DESC
                """), params).fetchall()
                by_template = [
                    {"template_id": r[0], "count": r[1]}
                    for r in template_rows
                ]

                # 按小时分组
                hour_rows = conn.execute(text(f"""
                    SELECT strftime('%Y-%m-%d %H:00', timestamp) AS hour, COUNT(*) AS cnt
                    FROM passive_consciousness_logs
                    WHERE timestamp > :since {platform_filter}
                    GROUP BY hour
                    ORDER BY hour
                """), params).fetchall()
                by_hour = [
                    {"hour": r[0], "count": r[1]}
                    for r in hour_rows
                ]

            return {
                "total": total,
                "success": success,
                "skipped": skipped,
                "error": error,
                "success_rate": success_rate,
                "avg_context_length": round(row[4] or 0, 1),
                "avg_longing_score": round(row[5] or 0, 3),
                "avg_chat_heat": round(row[6] or 0, 2),
                "avg_emotional_intensity": round(row[7] or 0, 3),
                "by_platform": by_platform,
                "by_template": by_template,
                "by_hour": by_hour,
            }

        except Exception as e:
            logger.error("获取注入统计失败: %s", e)
            return {
                "total": 0, "success": 0, "skipped": 0, "error": 0,
                "success_rate": 0.0,
                "avg_context_length": 0, "avg_longing_score": 0,
                "avg_chat_heat": 0, "avg_emotional_intensity": 0,
                "by_platform": [], "by_template": [], "by_hour": [],
                "error_message": str(e),
            }

    @staticmethod
    def get_trend_data(
        hours: int = 168,
        interval: str = "day",
    ) -> Dict[str, Any]:
        """
        获取趋势数据

        Args:
            hours: 时间范围（小时），默认 168（7 天）
            interval: 聚合粒度 — "hour" / "day" / "week"

        Returns:
            {
                "interval": str,
                "data": [
                    {
                        "period": str,
                        "count": int,
                        "success_count": int,
                        "avg_longing": float,
                        "avg_heat": float,
                        "avg_emotion": float,
                        "avg_context_length": float,
                    }
                ]
            }
        """
        try:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()

            # 根据粒度选择 strftime 格式
            fmt_map = {
                "hour": "%Y-%m-%d %H:00",
                "day": "%Y-%m-%d",
                "week": "%Y-W%W",
            }
            fmt = fmt_map.get(interval, fmt_map["day"])

            with active_engine.connect() as conn:
                rows = conn.execute(text(f"""
                    SELECT
                        strftime(:fmt, timestamp) AS period,
                        COUNT(*) AS cnt,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_cnt,
                        AVG(longing_score) AS avg_longing,
                        AVG(chat_heat) AS avg_heat,
                        AVG(emotional_intensity) AS avg_emotion,
                        AVG(CASE WHEN status = 'success' THEN context_length END) AS avg_ctx_len
                    FROM passive_consciousness_logs
                    WHERE timestamp > :since
                    GROUP BY period
                    ORDER BY period
                """), {"since": since, "fmt": fmt}).fetchall()

                data = [
                    {
                        "period": r[0],
                        "count": r[1],
                        "success_count": r[2] or 0,
                        "avg_longing": round(r[3] or 0, 3),
                        "avg_heat": round(r[4] or 0, 2),
                        "avg_emotion": round(r[5] or 0, 3),
                        "avg_context_length": round(r[6] or 0, 1),
                    }
                    for r in rows
                ]

            return {"interval": interval, "data": data}

        except Exception as e:
            logger.error("获取趋势数据失败: %s", e)
            return {"interval": interval, "data": [], "error_message": str(e)}

    @staticmethod
    def get_sentiment_analysis(hours: int = 72) -> Dict[str, Any]:
        """
        获取情感分析

        Args:
            hours: 分析时间范围（小时），默认 72

        Returns:
            {
                "emotional_distribution": [{"label": str, "count": int, "percentage": float}],
                "longing_distribution": [{"label": str, "count": int, "percentage": float}],
                "heat_distribution": [{"label": str, "count": int, "percentage": float}],
                "avg_scores": {
                    "longing": float,
                    "heat": float,
                    "emotion": float,
                },
                "correlation": {
                    "high_emotion_high_heat_count": int,
                    "high_longing_success_count": int,
                },
            }
        """
        try:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()

            with active_engine.connect() as conn:
                # 情绪分布
                emotion_rows = conn.execute(text("""
                    SELECT emotional_label, COUNT(*) AS cnt
                    FROM passive_consciousness_logs
                    WHERE timestamp > :since AND status = 'success'
                    GROUP BY emotional_label
                    ORDER BY cnt DESC
                """), {"since": since}).fetchall()

                total_emotion = sum(r[1] for r in emotion_rows) or 1
                emotional_distribution = [
                    {
                        "label": r[0] or "未知",
                        "count": r[1],
                        "percentage": round(r[1] / total_emotion, 4),
                    }
                    for r in emotion_rows
                ]

                # 想念等级分布
                longing_rows = conn.execute(text("""
                    SELECT longing_label, COUNT(*) AS cnt
                    FROM passive_consciousness_logs
                    WHERE timestamp > :since AND status = 'success'
                    GROUP BY longing_label
                    ORDER BY cnt DESC
                """), {"since": since}).fetchall()

                total_longing = sum(r[1] for r in longing_rows) or 1
                longing_distribution = [
                    {
                        "label": r[0] or "unknown",
                        "count": r[1],
                        "percentage": round(r[1] / total_longing, 4),
                    }
                    for r in longing_rows
                ]

                # 热度分布
                heat_rows = conn.execute(text("""
                    SELECT chat_heat_label, COUNT(*) AS cnt
                    FROM passive_consciousness_logs
                    WHERE timestamp > :since AND status = 'success'
                    GROUP BY chat_heat_label
                    ORDER BY cnt DESC
                """), {"since": since}).fetchall()

                total_heat = sum(r[1] for r in heat_rows) or 1
                heat_distribution = [
                    {
                        "label": r[0] or "unknown",
                        "count": r[1],
                        "percentage": round(r[1] / total_heat, 4),
                    }
                    for r in heat_rows
                ]

                # 平均分
                avg_row = conn.execute(text("""
                    SELECT
                        AVG(longing_score),
                        AVG(chat_heat),
                        AVG(emotional_intensity)
                    FROM passive_consciousness_logs
                    WHERE timestamp > :since AND status = 'success'
                """), {"since": since}).fetchone()

                # 关联分析
                corr_row = conn.execute(text("""
                    SELECT
                        SUM(CASE WHEN emotional_intensity >= 0.7 AND chat_heat >= 1.0 THEN 1 ELSE 0 END) AS high_emotion_high_heat,
                        SUM(CASE WHEN longing_score >= 0.5 AND status = 'success' THEN 1 ELSE 0 END) AS high_longing_success
                    FROM passive_consciousness_logs
                    WHERE timestamp > :since
                """), {"since": since}).fetchone()

            return {
                "emotional_distribution": emotional_distribution,
                "longing_distribution": longing_distribution,
                "heat_distribution": heat_distribution,
                "avg_scores": {
                    "longing": round(avg_row[0] or 0, 3),
                    "heat": round(avg_row[1] or 0, 2),
                    "emotion": round(avg_row[2] or 0, 3),
                },
                "correlation": {
                    "high_emotion_high_heat_count": corr_row[0] or 0,
                    "high_longing_success_count": corr_row[1] or 0,
                },
            }

        except Exception as e:
            logger.error("获取情感分析失败: %s", e)
            return {
                "emotional_distribution": [],
                "longing_distribution": [],
                "heat_distribution": [],
                "avg_scores": {"longing": 0, "heat": 0, "emotion": 0},
                "correlation": {"high_emotion_high_heat_count": 0, "high_longing_success_count": 0},
                "error_message": str(e),
            }
