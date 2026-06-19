"""
ContextCollector - 收集 LLM 生成念头需要的全部上下文

职责：
1. 从 state.db 读取最近对话（结构化，支持动态时间范围）
2. 从 Hindsight 召回相关记忆
3. 获取情绪状态
4. 获取时间感知
5. 获取天气信息（如果启用）
6. 加载用户习惯（从 USER.md）
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger("hermes.context_collector")


@dataclass
class ContextBundle:
    """给 LLM 的完整上下文"""
    
    # 最近对话（结构化）
    conversations: List[Dict]   # [{role, content, time, platform}]
    
    # Hindsight 记忆
    memories: List[str]         # Recall 结果
    
    # 情绪状态
    emotion: Dict               # {valence, arousal, social_need, dominant}
    
    # 时间感知
    time_context: Dict          # {hour, is_workday, is_meal_time, is_sleep_time, time_display}
    
    # 天气（如果启用）
    weather: Optional[Dict]     # {weather, temp, city} 或 None
    
    # 用户习惯（从 USER.md 提取）
    user_habits: str            # 通勤时间、午餐偏好、作息等
    
    # 动态时间范围（新增）
    time_range_days: int        # 本次收集使用的时间范围（天）
    
    def to_dict(self) -> Dict:
        """转换为字典（用于日志记录）"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为 JSON 字符串（用于日志记录）"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ContextCollector:
    """收集 LLM 生成念头需要的全部上下文"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 主动意识配置
        """
        self.config = config
        self.context_config = config.get("context", {})
        self.llm_config = config.get("llm", {})
        self.session_config = config.get("session", {})
        self.hindsight_config = config.get("hindsight", {})
        self.weather_config = config.get("weather", {})
    
    async def collect(self, status: Dict[str, Any]) -> ContextBundle:
        """
        收集完整的上下文信息
        
        Args:
            status: 当前状态（longing, chat_heat, emotional_intensity 等）
        
        Returns:
            ContextBundle 对象
        """
        # 0. 获取情绪状态（用于动态时间范围）
        emotion = self._get_emotion_state()
        
        # 1. 根据情绪动态选择时间范围
        time_range_days = self._get_dynamic_time_range_days(emotion, status)
        
        # 2. Session 对话（结构化，按时间范围查询）
        conversations = await self._get_structured_conversations(time_range_days)
        
        # 3. Hindsight 记忆
        memories = await self._recall_memories(conversations)
        
        # 4. 时间感知
        time_context = self._get_time_context()
        
        # 5. 天气（如果启用）
        weather = await self._get_weather()
        
        # 6. 用户习惯
        user_habits = self._load_user_habits()
        
        logger.info("上下文收集完成: 天数=%d, 对话=%d条, 记忆=%d条", 
                    time_range_days, len(conversations), len(memories))
        
        return ContextBundle(
            conversations=conversations,
            memories=memories,
            emotion=emotion,
            time_context=time_context,
            weather=weather,
            user_habits=user_habits,
            time_range_days=time_range_days
        )
    
    def _get_dynamic_time_range_days(self, emotion: Dict, status: Dict) -> int:
        """
        根据情绪状态动态选择时间范围
        
        规则：
        - 情绪强度低 (arousal < 0.3) → 读取 15 天消息（更广泛的上下文）
        - 情绪强度中 (0.3-0.7) → 读取 7 天消息
        - 情绪强度高 (arousal > 0.7) → 读取 3 天消息（关注近期）
        - 沉默时间长 (> 6小时) → 读取 1 天消息（关注近期互动）
        - 可通过配置覆盖默认值
        """
        # 检查配置是否有自定义时间范围
        custom_days = self.context_config.get("time_range_days", None)
        if custom_days is not None and int(custom_days) > 0:
            return int(custom_days)
        
        arousal = emotion.get("arousal", 0.3)
        silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
        
        # 沉默时间长 → 关注近期
        if silence_minutes > 360:  # 6小时
            return 1
        
        # 根据 arousal 选择时间范围
        if arousal < 0.3:
            return 15  # 低唤醒：广泛上下文
        elif arousal < 0.7:
            return 7   # 中唤醒：一周
        else:
            return 3   # 高唤醒：近期
    
    async def _get_structured_conversations(self, time_range_days: int = 7) -> List[Dict]:
        """
        获取结构化的对话（按时间范围查询）
        
        Args:
            time_range_days: 查询最近 N 天的消息
        """
        try:
            from services.message_service import MessageService
            from services.session_service import SessionService
            from services.fallback_session_service import FallbackSessionService
            from sqlalchemy import text
            from models.database import state_engine
            
            sources = self.session_config.get("sources", ["weixin"])
            max_chars = self.context_config.get("conversation_max_chars", 2000)
            filter_tool = self.session_config.get("filter_tool_messages", True)
            
            conversations = []
            
            # 计算时间范围
            cutoff_time = datetime.now() - timedelta(days=time_range_days)
            cutoff_timestamp = cutoff_time.timestamp()
            
            for platform in sources:
                user_id = SessionService.get_weixin_user_id() if platform == "weixin" else None
                if not user_id:
                    continue
                
                session = FallbackSessionService.get_or_create_active_session(platform, user_id)
                if not session:
                    continue
                
                session_id = session["id"] if isinstance(session, dict) else session.id
                
                # 按时间范围查询消息
                try:
                    with state_engine.connect() as conn:
                        query = text("""
                            SELECT role, content, timestamp 
                            FROM messages 
                            WHERE session_id = :session_id 
                            AND CAST(timestamp AS REAL) > :cutoff
                            AND role IN ('user', 'assistant')
                            ORDER BY timestamp ASC
                        """)
                        result = conn.execute(query, {
                            "session_id": session_id,
                            "cutoff": cutoff_timestamp
                        })
                        messages = [dict(row._mapping) for row in result]
                except Exception as e:
                    logger.warning("查询消息失败: %s", e)
                    # 回退到原来的方式
                    messages = MessageService.get_session_context_raw(
                        session_id, limit=200, include_tool=not filter_tool
                    ) or []
                
                if messages:
                    for msg in messages:
                        content = msg.get("content") or ""
                        if not content.strip():
                            continue
                        if max_chars and len(content) > max_chars:
                            content = content[:max_chars] + "..."
                        
                        conversations.append({
                            "role": msg.get("role", "unknown"),
                            "content": content,
                            "time": str(msg.get("timestamp", "")),
                            "platform": platform
                        })
            
            return conversations
            
        except Exception as e:
            logger.warning("获取结构化对话失败: %s", e)
            return []
    
    async def _recall_memories(self, conversations: List[Dict]) -> List[str]:
        """从 Hindsight 召回相关记忆"""
        if not self.hindsight_config.get("enabled", False):
            return []
        
        if not self.context_config.get("memory_enabled", True):
            return []
        
        try:
            from services.active_consciousness_service import call_hindsight_recall
            
            # 用最近对话内容作为 query
            query = " ".join([
                msg.get("content", "") 
                for msg in conversations[-5:]  # 最近 5 条
                if msg.get("role") == "user"
            ])
            
            if not query.strip():
                query = "最近的想法"
            
            limit = self.context_config.get("memory_limit", 5)
            bank_id = self.hindsight_config.get("bank_id", "hermes")
            base_url = self.hindsight_config.get("base_url", "http://localhost:8888")
            timeout = float(self.hindsight_config.get("timeout", 30))
            
            results = await call_hindsight_recall(
                query=query,
                limit=limit,
                bank_id=bank_id,
                base_url=base_url,
                timeout=timeout
            )
            
            return [r.get("text", "") for r in results if r.get("text")]
            
        except Exception as e:
            logger.warning("Hindsight 召回失败: %s", e)
            return []
    
    def _get_emotion_state(self) -> Dict:
        """获取情绪状态"""
        try:
            from services.active_consciousness_service import get_emotion_state
            state = get_emotion_state()
            return state.to_dict()
        except Exception as e:
            logger.warning("获取情绪状态失败: %s", e)
            return {
                "valence": 0.5,
                "arousal": 0.3,
                "social_need": 0.3,
                "dominant": "calm"
            }
    
    def _get_time_context(self) -> Dict:
        """获取时间感知"""
        now = datetime.now()
        hour = now.hour
        
        return {
            "hour": hour,
            "is_workday": now.weekday() < 5,
            "is_meal_time": hour in [7, 8, 12, 13, 18, 19],
            "is_sleep_time": hour >= 23 or hour < 7,
            "time_display": now.strftime("%Y-%m-%d %H:%M %A")
        }
    
    async def _get_weather(self) -> Optional[Dict]:
        """获取天气信息"""
        if not self.weather_config.get("enabled", False):
            return None
        
        if not self.context_config.get("weather_enabled", False):
            return None
        
        try:
            from services.weather_service import WeatherService
            
            weather_service = WeatherService()
            weather_info = await weather_service.get_weather(
                amap_key=self.weather_config.get("amap_key", ""),
                adcode=self.weather_config.get("adcode", "370100"),
                cache_ttl=int(self.weather_config.get("cache_ttl", 3600)),
                temp_threshold=float(self.weather_config.get("temp_change_threshold", 5.0))
            )
            
            if weather_info.get("success"):
                current = weather_info.get("current", {})
                return {
                    "weather": current.get("weather", "未知"),
                    "temp": current.get("temp", "?"),
                    "city": current.get("city", "济南")
                }
            
            return None
            
        except Exception as e:
            logger.warning("获取天气失败: %s", e)
            return None
    
    def _load_user_habits(self) -> str:
        """加载用户习惯（从 USER.md）"""
        try:
            from pathlib import Path
            
            hermes_dir = Path.home() / ".hermes"
            user_path = hermes_dir / "memories" / "USER.md"
            
            if user_path.exists():
                content = user_path.read_text(encoding="utf-8").strip()
                if content:
                    # 截取关键部分
                    if len(content) > 1500:
                        content = content[:1500] + "\n...(已截断)"
                    return content
            
            return ""
            
        except Exception as e:
            logger.warning("加载用户习惯失败: %s", e)
            return ""
