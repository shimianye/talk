"""Redis 客户端：会话、缓存、限流与幂等键。

客户端采用惰性连接，Redis 未启动时不会在导入阶段报错；使用处需自行 try/except 降级。
"""
from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.redis_url,
    decode_responses=True,
)
