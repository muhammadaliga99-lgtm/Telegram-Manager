"""
Web Server moduli (aiohttp.web):
Render platformasida xizmatni 24/7 ishlab turishini ta'minlash uchun
PORT bo'yicha HTTP server ishga tushiradi va Health Check so'rovlariga javob beradi.
"""
import logging
import time
from aiohttp import web

from config import settings
from userbot import userbot_manager

logger = logging.getLogger(__name__)

START_TIME = time.time()


async def handle_index(request: web.Request) -> web.Response:
    """Bosh sahifa: Tizim statusi haqida qisqacha ma'lumot."""
    uptime_sec = int(time.time() - START_TIME)
    data = {
        "status": "healthy",
        "service": "Telegram-Manager",
        "userbot_connected": userbot_manager.is_connected(),
        "admin_id": settings.ADMIN_USER_ID,
        "uptime_seconds": uptime_sec,
        "mode": "automatic"
    }
    return web.json_response(data)


async def handle_healthz(request: web.Request) -> web.Response:
    """Render va tashqi monitoring xizmatlari (UptimeRobot) uchun Health check."""
    return web.Response(text="OK", status=200)


def create_web_app() -> web.Application:
    """aiohttp ilovasini yaratish va marshrutlarni sozlash."""
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/health", handle_healthz)
    app.router.add_get("/healthz", handle_healthz)
    return app
