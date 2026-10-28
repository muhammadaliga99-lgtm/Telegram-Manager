"""
Kompleks tizim testi (test_system.py - v2.0):
Yangi imkoniyatlar: Smart Reply, Context Awareness, Profile Management, TTS, Intent Router
"""
import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from config import settings
from userbot import userbot_manager
from agent import ai_agent
import edge_tts


async def run_tests():
    print("=" * 60)
    print("🧪 TELEGRAM MANAGER (v2.0) KOMPLEKS TESTLARNI BOSHLASH")
    print("=" * 60)

    # 1. Config Test
    print("\n[TEST 1] Konfiguratsiya va Muhit o'zgaruvchilari...")
    assert settings.TELEGRAM_BOT_TOKEN.startswith("9243162646"), "Bot token noto'g'ri!"
    assert settings.ADMIN_USER_ID == 6912373539, "Admin ID noto'g'ri!"
    print("✅ Config testi muvaffaqiyatli o'tdi.")

    # 2. Telethon Userbot Test
    print("\n[TEST 2] Telethon Userbot mijoziga ulanish...")
    await userbot_manager.start()
    assert userbot_manager.is_connected(), "Telethon ulanmadi!"
    print(f"✅ Telethon ulandi! Keshdagi dialoglar soni: {len(userbot_manager._cached_dialogs)}")

    # 3. Peer Resolution Test (Ustoz va Sinfdoshlar guruhi)
    print("\n[TEST 3] 'ustoz' va 'sinfdoshlar guruhi' aliasini aniqlash...")
    e1, n1 = await userbot_manager.resolve_peer("ustoz")
    print(f"✅ 'ustoz' -> {n1}")
    e2, n2 = await userbot_manager.resolve_peer("sinfdoshlar guruhi")
    print(f"✅ 'sinfdoshlar guruhi' -> {n2}")

    # 4. Intent Classification Test: Smart Reply
    print("\n[TEST 4] Intent Router: 'Sinfdoshlar guruhiga Aziz yozgan oxirgi xabariga javob ber'...")
    i1 = await ai_agent.classify_intent("Sinfdoshlar guruhiga Aziz yozgan oxirgi xabariga javob ber")
    print("Intent 1:", i1)
    assert i1.get("action") == "smart_reply", "Action smart_reply bo'lishi kerak edi!"
    assert i1.get("target_person") == "Aziz", "Target person Aziz bo'lishi kerak edi!"
    print("✅ Smart reply niyati muvaffaqiyatli aniqlandi.")

    # 5. Context-Aware Reply Generation Test
    print("\n[TEST 5] Kontekstli javob generatsiyasi (Sinfdoshlar chatidan Azizga javob)...")
    messages, chat_name, _ = await userbot_manager.get_recent_messages("sinfdoshlar", limit=15)
    reply_decision = await ai_agent.generate_contextual_reply(
        chat_name,
        messages,
        "Aziz",
        "javob ber"
    )
    print("Reply Decision:", reply_decision)
    assert reply_decision.get("target_message_id") is not None, "Target message ID topilmadi!"
    assert len(reply_decision.get("reply_text", "")) > 2, "Javob matni bo'sh!"
    print(f"✅ Azizning xabariga mos javob tuzildi: «{reply_decision.get('reply_text')}»")

    # 6. Intent Classification Test: Profile Update
    print("\n[TEST 6] Intent Router: 'Bio ni AI Specialist deb o'zgartir'...")
    i2 = await ai_agent.classify_intent("Bio ni 'AI Specialist' deb o'zgartir")
    print("Intent 2:", i2)
    assert i2.get("action") == "update_profile", "Action update_profile bo'lishi kerak edi!"
    print("✅ Profile update niyati muvaffaqiyatli aniqlandi.")

    # 7. Edge-TTS Audio Test
    print("\n[TEST 7] Edge-TTS uz-UZ-SardorNeural ovoz sintezi...")
    test_ogg = "test_v2.ogg"
    comm = edge_tts.Communicate("Salom jigar, nma gap", settings.DEFAULT_VOICE)
    await comm.save(test_ogg)
    assert os.path.exists(test_ogg) and os.path.getsize(test_ogg) > 500
    os.remove(test_ogg)
    print("✅ Audio sintezi muvaffaqiyatli o'tdi.")

    await userbot_manager.stop()

    print("\n" + "=" * 60)
    print("🎉 BARCHA v2.0 TESTLARI 100% MUVAFFAQIYATLI O'TDI!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
