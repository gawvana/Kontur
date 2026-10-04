import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from config import settings
from middlewares.error_handler import ErrorHandlerMiddleware
from handlers import general, catalog, cases, notifications, inline

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=settings.bot_token)
    
    redis = Redis.from_url(settings.redis_url)
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)
    
    dp.update.outer_middleware(ErrorHandlerMiddleware())
    
    dp.include_routers(
        general.router,
        catalog.router,
        cases.router,
        notifications.router,
        inline.router
    )
    
    try:
        await dp.start_polling(bot)
    finally:
        await storage.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
