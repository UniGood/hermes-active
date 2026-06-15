"""
配置路由
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User, Config
from models.schemas import LLMConfig, PromptsConfig, DefaultPromptsConfig, SuccessResponse
from services.config_service import ConfigService
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/config", tags=["配置管理"])


# ============ 通用配置 ============

@router.get("/all")
async def get_all_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取所有配置"""
    configs = db.query(Config).all()
    return [c.to_dict() for c in configs]


@router.get("/get/{key}")
async def get_config_value(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取单个配置值"""
    value = ConfigService.get_config(db, key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"配置 {key} 不存在")
    return {"key": key, "value": value}


@router.put("/set", response_model=SuccessResponse)
async def set_config_value(
    key: str,
    value: str,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """设置配置值"""
    ConfigService.set_config(db, key, value, description)
    return SuccessResponse(message=f"配置 {key} 更新成功")


@router.delete("/delete/{key}", response_model=SuccessResponse)
async def delete_config(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """删除配置"""
    config = db.query(Config).filter(Config.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"配置 {key} 不存在")
    db.delete(config)
    db.commit()
    return SuccessResponse(message=f"配置 {key} 已删除")


# ============ LLM 配置 ============

@router.get("/llm", response_model=LLMConfig)
async def get_llm_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取 LLM 配置"""
    config = ConfigService.get_llm_config(db)
    return LLMConfig(**config)


@router.put("/llm", response_model=SuccessResponse)
async def update_llm_config(
    config: LLMConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """更新 LLM 配置"""
    ConfigService.update_llm_config(db, config.model_dump())
    return SuccessResponse(message="LLM 配置更新成功")


# ============ 提示词配置 ============

@router.get("/prompts", response_model=PromptsConfig)
async def get_prompts_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取提示词配置"""
    config = ConfigService.get_prompts_config(db)
    return PromptsConfig(**config)


@router.put("/prompts", response_model=SuccessResponse)
async def update_prompts_config(
    prompts: PromptsConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """更新提示词配置"""
    ConfigService.update_prompts_config(db, prompts.model_dump())
    return SuccessResponse(message="提示词配置更新成功")


@router.get("/prompts/templates")
async def get_prompt_templates(
    current_user: User = Depends(get_current_user)
):
    """获取提示词模板"""
    return ConfigService.get_prompt_templates()


# ============ 默认提示词配置 ============

@router.get("/default-prompts", response_model=DefaultPromptsConfig)
async def get_default_prompts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取默认提示词配置"""
    system_prompt = ConfigService.get_config(db, "default_system_prompt") or ""
    user_prompt = ConfigService.get_config(db, "default_user_prompt") or ""
    append_soul_md = ConfigService.get_config(db, "default_append_soul_md")
    return DefaultPromptsConfig(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        append_soul_md=append_soul_md != "false"  # 默认 true
    )


@router.put("/default-prompts", response_model=SuccessResponse)
async def update_default_prompts(
    prompts: DefaultPromptsConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """更新默认提示词配置"""
    ConfigService.set_config(db, "default_system_prompt", prompts.system_prompt, "默认系统提示词")
    ConfigService.set_config(db, "default_user_prompt", prompts.user_prompt, "默认用户提示词")
    ConfigService.set_config(db, "default_append_soul_md", str(prompts.append_soul_md).lower(), "默认是否拼接 soul.md")
    return SuccessResponse(message="默认提示词配置已保存")


# ============ Hermes 文件 ============

@router.get("/hermes/soul")
async def get_hermes_soul(
    current_user: User = Depends(get_current_user)
):
    """获取 Hermes SOUL.md 内容"""
    content = ConfigService.read_hermes_soul()
    return {"content": content}


@router.get("/hermes/memory")
async def get_hermes_memory(
    current_user: User = Depends(get_current_user)
):
    """获取 Hermes MEMORY.md 内容"""
    content = ConfigService.read_hermes_memory()
    return {"content": content}


# ============ Hindsight 配置 ============

@router.get("/hindsight")
async def get_hindsight_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取 Hindsight 配置"""
    import json
    config_str = ConfigService.get_config(db, "active_consciousness.hindsight")
    if config_str:
        try:
            return json.loads(config_str) if isinstance(config_str, str) else config_str
        except json.JSONDecodeError:
            pass
    return {
        "enabled": True,
        "base_url": "http://localhost:8888",
        "bank_id": "hermes",
        "recall_limit": 5,
        "reflect_enabled": True,
        "timeout": 120
    }


@router.put("/hindsight", response_model=SuccessResponse)
async def update_hindsight_config(
    config: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """更新 Hindsight 配置"""
    import json
    ConfigService.set_config(db, "active_consciousness.hindsight", json.dumps(config), "Hindsight 记忆配置")
    return SuccessResponse(message="Hindsight 配置更新成功")
