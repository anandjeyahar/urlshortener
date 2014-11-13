import redis
import os
redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
redisConn = redis.from_url(redis_url)
