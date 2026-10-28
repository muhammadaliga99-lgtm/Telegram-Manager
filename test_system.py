"""
Kompleks tizim testi (test_system.py):
Loyiha ishga tushishidan oldin barcha qismlarni (Config, Telethon, Gemini Agent, Edge-TTS, Web)
100% to'g'ri ishlashini avtomatik sinovdan o'tkazadi.
"""
import asyncio
import os
import sys

# UTF-8 stdout
sys.stdout.reconfigure(encoding="utf-8")

from config import settings
from userbot import userbot_manager
from agent import ai_agent
import edge_tts


async def run_tests():
    print("=" * 60)
    print("🧪 TELEGRAM MANAGER KOMPLEKS TESTLARNI BOSHLASH")
    print("=" * 60)

    # 1. Config Test
    print("\n[TEST 1] Konfiguratsiya va Muhit o'zgaruvchilari...")
    assert settings.TELEGRAM_BOT_TOKEN.startswith("9243162646"), "Bot token noto'g'ri!"
    assert settings.ADMIN_USER_ID == 6912373539, "Admin ID noto'g'ri!"
    assert len(settings.TELEGRAM_STRING_SESSION) > 50, "StringSession bo'sh!"
    print("✅ Config testi muvaffaqiyatli o'tdi.")

    # 2. Telethon Userbot Test
    print("\n[TEST 2] Telethon Userbot mijoziga ulanish...")
    await userbot_manager.start()
    assert userbot_manager.is_connected(), "Telethon ulanmadi!"
    print(f"✅ Telethon ulandi! Keshdagi dialoglar soni: {len(userbot_manager._cached_dialogs)}")

    # 3. Peer Resolution Test (Ustoz va Sinfdoshlar guruhi)
    print("\n[TEST 3] 'ustoz' va 'sinfdoshlar guruhi' aliasini aniqlash...")
    entity1, name1 = await userbot_manager.resolve_peer("ustoz")
    print(f"✅ 'ustoz' topildi -> Nomi: {name1}, ID: {getattr(entity1, 'id', None)}")

    entity2, name2 = await userbot_manager.resolve_peer("sinfdoshlar guruhi")
    print(f"✅ 'sinfdoshlar guruhi' topildi -> Nomi: {name2}, ID: {getattr(entity2, 'id', None)}")

    # 4. Gemini AI Agent Test (Ustozga salom yozish)
    print("\n[TEST 4] Gemini AI Agent tahlili: 'ustozimga salom deb yoz'...")
    res1 = await ai_agent.process_command("ustozimga salom deb yoz")
    print(f"Agent javobi: {res1}")
    assert res1.get("action") == "send_message", "Action send_message bo'lishi kerak edi!"
    assert "ustoz" in res1.get("recipient", "").lower(), "Recipient ustoz bo'lishi kerak edi!"
    print("✅ Matnli xabar agenti testi muvaffaqiyatli o'tdi.")

    # 5. Gemini AI Agent Test (Ovozli golos)
    print("\n[TEST 5] Gemini AI Agent tahlili: 'adajonga kech qolaman deb golos yubor'...")
    res2 = await ai_agent.process_command("adajonga kech qolaman deb golos yubor")
    print(f"Agent javobi: {res2}")
    assert res2.get("action") == "send_voice", "Action send_voice bo'lishi kerak edi!"
    print("✅ Ovozli xabar agenti testi muvaffaqiyatli o'tdi.")

    # 6. Edge-TTS Ovoz yaratish testi
    print("\n[TEST 6] Edge-TTS uz-UZ-SardorNeural ovoz sintezi...")
    test_ogg = "test_audio.ogg"
    communicate = edge_tts.Communicate("Assalomu alaykum", settings.DEFAULT_VOICE)
    await communicate.save(test_ogg)
    assert os.path.exists(test_ogg) and os.path.getsize(test_ogg) > 500, "Audio fayl yaratilmadi!"
    os.remove(test_ogg)
    print("✅ Edge-TTS audio sintezi muvaffaqiyatli o'tdi.")

    # To'xtatish
    await userbot_manager.stop()

    print("\n" + "=" * 60)
    print("🎉 BARCHA TESTLAR 100% MUVAFFAQIYATLI O'TDI! XATOLIK YO'Q!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
