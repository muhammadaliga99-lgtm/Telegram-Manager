"""
Asosiy ishga tushiruvchi modul (main.py):
1. Telethon Userbot mijozini ishga tushiradi.
2. aiohttp Web serverini (Render 24/7 port) ishga tushiradi.
3. aiogram Bot polling jarayonini parallel ishga tushiradi.
"""
import asyncio
import logging
import os
import sys

from aiohttp import web
from aiogram import Bot

from bot import bot, dp
from config import settings
from userbot import userbot_manager
from web import create_web_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")


async def main():
    logger.info("==================================================")
    logger.info("🚀 Telegram Manager tizimi ishga tushmoqda...")
    logger.info(f"👤 Bot Egasi (ADMIN_USER_ID): {settings.ADMIN_USER_ID}")
    logger.info(f"🌐 HTTP Port: {settings.PORT}")
    logger.info("==================================================")

    # 1. Telethon Userbot mijozini ishga tushirish
    try:
        await userbot_manager.start()
        logger.info("✅ Telethon Userbot muvaffaqiyatli ishga tushdi.")
    except Exception as e:
        logger.error(f"❌ Telethon ishga tushirishda xatolik: {e}", exc_info=True)
        logger.warning("Bot Userbotsiz davom etmoqda (ba'zi funksiyalar cheklangan bo'lishi mumkin)...")

    # 2. Render 24/7 Web Serverini ishga tushirish
    app = create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.PORT)
    await site.start()
    logger.info(f"✅ Web server 0.0.0.0:{settings.PORT} manzilida ishlamoqda.")

    # 3. aiogram Telegram Botni ishga tushirish
    try:
        # Eski eskirgan webhook yoki update larni tozalab yangidan boshlash
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ aiogram Bot polling boshlanmoqda...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Polling to'xtatish so'rovi qabul qilindi...")
    finally:
        logger.info("Tizim to'xtatilmoqda (Graceful Shutdown)...")
        await runner.cleanup()
        await userbot_manager.stop()
        await bot.session.close()
        logger.info("Tizim to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Tizim foydalanuvchi tomonidan to'xtatildi.")
