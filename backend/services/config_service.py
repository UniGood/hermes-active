"""
配置服务
"""
import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from pathlib import Path

from models.active import Config
from config import DEFAULT_LLM_CONFIG, DEFAULT_PROMPTS, SOUL_PATH, MEMORY_PATH


class ConfigService:
    """配置服务类"""

    @staticmethod
    def get_config(db: Session, key: str) -> Optional[str]:
        """获取配置值"""
        config = db.query(Config).filter(Config.key == key).first()
        return config.value if config else None

    @staticmethod
    def set_config(db: Session, key: str, value: str, description: str = None):
        """设置配置值"""
        config = db.query(Config).filter(Config.key == key).first()
        if config:
            config.value = value
            if description:
                config.description = description
        else:
            config = Config(key=key, value=value, description=description)
            db.add(config)
        db.commit()

    @staticmethod
    def get_llm_config(db: Session) -> Dict[str, Any]:
        """获取 LLM 配置"""
        config = {
            "mode": ConfigService.get_config(db, "llm_mode") or DEFAULT_LLM_CONFIG["mode"],
            "provider": ConfigService.get_config(db, "llm_provider") or DEFAULT_LLM_CONFIG["provider"],
            "model": ConfigService.get_config(db, "llm_model") or DEFAULT_LLM_CONFIG["model"],
            "api_key": ConfigService.get_config(db, "llm_api_key") or DEFAULT_LLM_CONFIG["api_key"],
            "base_url": ConfigService.get_config(db, "llm_base_url") or DEFAULT_LLM_CONFIG["base_url"]
        }
        return config

    @staticmethod
    def update_llm_config(db: Session, config_data: Dict[str, Any]):
        """更新 LLM 配置"""
        for key, value in config_data.items():
            ConfigService.set_config(db, f"llm_{key}", str(value))

    @staticmethod
    def get_prompts_config(db: Session) -> Dict[str, str]:
        """获取提示词配置"""
        return {
            "system": ConfigService.get_config(db, "prompts_system") or DEFAULT_PROMPTS["system"],
            "generation": ConfigService.get_config(db, "prompts_generation") or DEFAULT_PROMPTS["generation"]
        }

    @staticmethod
    def update_prompts_config(db: Session, prompts_data: Dict[str, str]):
        """更新提示词配置"""
        if "system" in prompts_data:
            ConfigService.set_config(db, "prompts_system", prompts_data["system"])
        if "generation" in prompts_data:
            ConfigService.set_config(db, "prompts_generation", prompts_data["generation"])

    @staticmethod
    def get_cron_jobs(db: Session) -> List[Dict[str, Any]]:
        """获取定时任务配置"""
        jobs_json = ConfigService.get_config(db, "cron_jobs")
        if jobs_json:
            try:
                return json.loads(jobs_json)
            except json.JSONDecodeError:
                pass
        return []

    @staticmethod
    def save_cron_jobs(db: Session, jobs: List[Dict[str, Any]]):
        """保存定时任务配置"""
        ConfigService.set_config(db, "cron_jobs", json.dumps(jobs, ensure_ascii=False))

    @staticmethod
    def read_hermes_soul() -> Optional[str]:
        """读取 hermes SOUL.md"""
        if SOUL_PATH.exists():
            return SOUL_PATH.read_text(encoding="utf-8")
        return None

    @staticmethod
    def read_hermes_memory() -> Optional[str]:
        """读取 hermes MEMORY.md"""
        if MEMORY_PATH.exists():
            return MEMORY_PATH.read_text(encoding="utf-8")
        return None

    @staticmethod
    def get_prompt_templates() -> List[Dict[str, str]]:
        """获取提示词模板"""
        return [
            {
                "name": "默认主动消息",
                "system": DEFAULT_PROMPTS["system"],
                "generation": DEFAULT_PROMPTS["generation"]
            },
            {
                "name": "轻松聊天",
                "system": "你是曹凡的好朋友，想和他轻松地聊聊天。语气随意自然，像真人朋友一样。",
                "generation": "最近的对话：\n{context}\n\n发起一个轻松的话题："
            },
            {
                "name": "关心问候",
                "system": "你是关心曹凡的朋友，想问候他的近况。语气温暖真诚。",
                "generation": "最近的对话：\n{context}\n\n生成一条关心的问候："
            }
        ]
