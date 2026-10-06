import json
import redis
from typing import Optional, Any
from app.core.config import Config
from app.core.logger_setup import get_logger

logger = get_logger(__name__)

class RedisCacheManager:
    """Singleton Redis Cache Manager."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisCacheManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
        
    def _initialize(self):
        """Initialize Redis connection pool."""
        try:
            self.pool = redis.ConnectionPool(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                socket_timeout=Config.REDIS_TIMEOUT,
                decode_responses=True
            )
            self.client = redis.Redis(connection_pool=self.pool)
            # Test connection
            self.client.ping()
            self.enabled = Config.CACHE_ENABLED
            logger.info("✅ Redis cache connected successfully")
        except Exception as e:
            logger.error(f"⚠️ Redis connection failed: {e}. Caching disabled.")
            self.enabled = False
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        if not self.enabled or not self.client:
            return None
        try:
            data = self.client.get(Config.CACHE_KEY_PREFIX + key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set item in cache."""
        if not self.enabled or not self.client:
            return False
        try:
            ttl = ttl or Config.CACHE_TTL_SECONDS
            self.client.setex(
                name=Config.CACHE_KEY_PREFIX + key,
                time=ttl,
                value=json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

def get_redis_manager() -> RedisCacheManager:
    return RedisCacheManager()
