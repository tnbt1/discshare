import redis.asyncio as redis
import json
import logging
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class RedisDB:
    def __init__(self):
        self.redis_url = Config.REDIS_URL
        self.redis = None
    
    async def _get_client(self):
        if not self.redis:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
        return self.redis
    
    async def set_session(self, token: str, session_data: Dict[str, Any], ttl: int = None):
        try:
            client = await self._get_client()
            key = f"session:{token}"
            value = json.dumps(session_data)
            
            if ttl is None:
                ttl = Config.URL_EXPIRY_DAYS * 24 * 3600
            
            await client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis set_session error: {e}")
            return False
    
    async def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            client = await self._get_client()
            key = f"session:{token}"
            value = await client.get(key)
            
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get_session error: {e}")
            return None
    
    async def set_file(self, session_id: str, file_id: str, file_info: Dict[str, Any]):
        try:
            client = await self._get_client()
            key = f"file:{session_id}:{file_id}"
            value = json.dumps(file_info)
            ttl = Config.URL_EXPIRY_DAYS * 24 * 3600
            
            await client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis set_file error: {e}")
            return False
    
    async def get_file(self, session_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        try:
            client = await self._get_client()
            key = f"file:{session_id}:{file_id}"
            value = await client.get(key)
            
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get_file error: {e}")
            return None
    
    async def set_rate_limit(self, user_id: str, count: int = 1):
        try:
            client = await self._get_client()
            key = f"rate:{user_id}"
            await client.setex(key, 3600, str(count))  # 1時間
            return True
        except Exception as e:
            logger.error(f"Redis rate_limit error: {e}")
            return False
    
    async def get_rate_limit(self, user_id: str) -> int:
        try:
            client = await self._get_client()
            key = f"rate:{user_id}"
            value = await client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Redis get_rate_limit error: {e}")
            return 0
    
    async def set(self, key: str, value: Any, expire: int = None):
        try:
            client = await self._get_client()

            if isinstance(value, dict):
                value = json.dumps(value)
            
            if expire:
                await client.setex(key, expire, value)
            else:
                await client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:

        try:
            client = await self._get_client()
            value = await client.get(key)
            
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def ping(self) -> bool:
        try:
            client = await self._get_client()
            result = await client.ping()
            return result
        except Exception as e:
            logger.error(f"Redis ping error: {e}")
            return False
    
    async def close(self):
        if self.redis:
            await self.redis.close()