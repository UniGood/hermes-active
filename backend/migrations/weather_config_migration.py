"""
天气配置迁移脚本

将旧的天气配置从 passivite_consciousness.weather.* 和 active_consciousness.weather.*
迁移到统一的 weather.* 命名空间。

用法：
    cd backend && python -m migrations.weather_config_migration
"""

import sys
import logging
from pathlib import Path

# 添加 backend 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import ActiveSession
from services.config_service import ConfigService

logger = logging.getLogger("hermes.migration.weather_config")

# 旧键 → 新键 映射
# passive_consciousness.weather.* → weather.*
PASSIVE_MAPPINGS = {
    "passive_consciousness.weather.enabled": "weather.enabled",
    "passive_consciousness.weather.provider": "weather.provider",
    "passive_consciousness.weather.city": "weather.city",
    "passive_consciousness.weather.cache_hours": "weather.cache_hours",
    "passive_consciousness.weather.amap_key": "weather.amap_key",
    "passive_consciousness.weather.qweather_key": "weather.qweather_key",
    "passive_consciousness.weather.qweather_geo_url": "weather.qweather_geo_url",
    "passive_consciousness.weather.qweather_weather_url": "weather.qweather_weather_url",
}

# active_consciousness.weather.* → weather.*
ACTIVE_MAPPINGS = {
    "active_consciousness.weather.enabled": "weather.enabled",
    "active_consciousness.weather.amap_key": "weather.amap_key",
    "active_consciousness.weather.adcode": "weather.adcode",
    # cache_ttl (秒) → cache_hours (小时)，需要转换
    "active_consciousness.weather.cache_ttl": "weather.cache_hours",
}


def migrate():
    """执行天气配置迁移"""
    db = ActiveSession()
    migrated = 0
    skipped = 0
    deleted = 0

    try:
        # 第一步：迁移 passive_consciousness.weather.* → weather.*
        # 优先使用 passive 的值（因为它是天气配置的主要来源）
        for old_key, new_key in PASSIVE_MAPPINGS.items():
            old_value = ConfigService.get_config(db, old_key)
            if old_value is None:
                continue

            new_value = ConfigService.get_config(db, new_key)
            if new_value is not None:
                # 新键已存在，跳过（不覆盖）
                logger.info("跳过 %s → %s（新键已存在）", old_key, new_key)
                skipped += 1
            else:
                # 迁移值
                ConfigService.set_config(db, new_key, old_value)
                logger.info("迁移 %s → %s = %s", old_key, new_key, old_value)
                migrated += 1

            # 删除旧键
            ConfigService.delete_config(db, old_key)
            deleted += 1

        # 第二步：迁移 active_consciousness.weather.* → weather.*
        # 只迁移 passive 没有的键（如 adcode），或做特殊转换
        for old_key, new_key in ACTIVE_MAPPINGS.items():
            old_value = ConfigService.get_config(db, old_key)
            if old_value is None:
                continue

            new_value = ConfigService.get_config(db, new_key)

            if old_key == "active_consciousness.weather.cache_ttl":
                # 特殊处理：cache_ttl (秒) → cache_hours (小时)
                if new_value is None:
                    try:
                        cache_hours = str(int(int(old_value) / 3600))
                        ConfigService.set_config(db, new_key, cache_hours)
                        logger.info("迁移 %s → %s = %s（%s秒 → %s小时）",
                                    old_key, new_key, cache_hours, old_value, cache_hours)
                        migrated += 1
                    except (ValueError, TypeError):
                        logger.warning("无法转换 %s = %s，跳过", old_key, old_value)
                        skipped += 1
            elif new_value is not None:
                # 新键已存在，跳过
                logger.info("跳过 %s → %s（新键已存在）", old_key, new_key)
                skipped += 1
            else:
                # 迁移值
                ConfigService.set_config(db, new_key, old_value)
                logger.info("迁移 %s → %s = %s", old_key, new_key, old_value)
                migrated += 1

            # 删除旧键
            ConfigService.delete_config(db, old_key)
            deleted += 1

        # 第三步：清理 context.weather_enabled（如果有残留）
        context_weather_key = "active_consciousness.context.weather_enabled"
        # 不删除这个键，因为它仍在 _DEFAULTS 中使用

        logger.info("迁移完成: 迁移=%d, 跳过=%d, 删除旧键=%d", migrated, skipped, deleted)
        return {"migrated": migrated, "skipped": skipped, "deleted": deleted}

    except Exception as e:
        logger.error("迁移失败: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("开始天气配置迁移...")
    result = migrate()
    print(f"迁移完成: {result}")
