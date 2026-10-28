"""
Telegram Bot moduli (aiogram v3):
Muhammad Ali uchun xavfsiz boshqaruv paneli.
Faqat ADMIN_USER_ID uchun ruxsat berilgan.
Boshqa har qanday foydalanuvchi qat'iyan bloklanadi.
"""
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from agent import ai_agent
from config import settings
from userbot import userbot_manager

logger = logging.getLogger(__name__)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


# ========================================================
# XAVFSIZLIK FILTERI: Faqat Bot Egasi (ADMIN_USER_ID)
# ========================================================
@dp.message.outer_middleware()
async def security_middleware(handler, event: types.TelegramObject, data: dict):
    if isinstance(event, Message):
        user_id = event.from_user.id if event.from_user else None
        if user_id != settings.ADMIN_USER_ID:
            logger.warning(
                f"🚨 Begona foydalanuvchi botga kirdi! ID={user_id}, "
                f"Username=@{event.from_user.username if event.from_user else 'None'}"
            )
            await event.answer(
                "⛔ **Kirish taqiqlangan!**\n"
                "Ushbu bot shaxsiy va faqat uning egasi uchun xizmat qiladi.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    return await handler(event, data)


# ========================================================
# BUYRUQLAR (COMMANDS)
# ========================================================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "👋 **Assalomu alaykum, Muhammad Ali!**\n\n"
        "🤖 **Telegram Manager AI Agent** 24/7 ish rejimida faol.\n\n"
        "Siz bu yerga tabiiy tilda buyruq bersangiz, Agent uni darhol tahlil qilib, "
        "shaxsiy yozish uslubingizda (Toshkent shevasi) qabul qiluvchiga **avtomatik** yuboradi:\n\n"
        "📌 **Misollar:**\n"
        "• _Ustozimga salom deb yoz_\n"
        "• _Adajonga hozir yo'ldaman, 15 minutda boraman deb golos yubor_\n"
        "• _Islomga nma gap jigar deb yoz_\n"
        "• _Bilolga loyiha tayyor boldi deb yoz_\n\n"
        "🛠 **Qo'shimcha buyruqlar:**\n"
        "/status — Tizim va userbot holati\n"
        "/contacts — Tezkor kontaktlar ro'yxati\n"
        "/help — Qo'llanma"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("status"))
async def cmd_status(message: Message):
    userbot_status = "🟢 Ulandi (Faol)" if userbot_manager.is_connected() else "🔴 Ulanmagan"
    text = (
        "📊 **Tizim Holati:**\n\n"
        f"• **Telegram Userbot:** {userbot_status}\n"
        f"• **AI Model:** `{settings.GEMINI_MODEL}`\n"
        f"• **Standart Ovoz (TTS):** `{settings.DEFAULT_VOICE}`\n"
        f"• **Rejim:** ⚡ Avtomatik yuborish (Tasdiqsiz)\n"
        f"• **Xavfsizlik:** 🔒 Faqat siz (ID: `{settings.ADMIN_USER_ID}`)\n"
        f"• **Server:** 🌐 Render 24/7 Web Service (Port: `{settings.PORT}`)"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("contacts"))
async def cmd_contacts(message: Message):
    lines = ["📇 **Tezkor Kontaktlar (Aliases):**\n"]
    for alias, peer_id in settings.KNOWN_ALIASES.items():
        lines.append(f"• `{alias}` ➔ ID: `{peer_id}`")
    lines.append("\n💡 *Shuningdek, @username yoki kontaktdagi ismlarni ham to'g'ridan-to'g'ri tushunadi.*")
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 **Telegram Manager Qo'llanmasi:**\n\n"
        "1️⃣ **Matnli xabar yuborish:**\n"
        "«_Ustozimga dars soat nechada bo'ladi deb so'ra_»\n"
        "AI buni sizning nomingizdan samimiy va hurmat bilan («Assalamu Alaykum Ustoz...») yozib yuboradi.\n\n"
        "2️⃣ **Ovozli xabar (Golos) yuborish:**\n"
        "«_Adajonga kech qolaman deb golos yubor_» yoki «_... deb ovozli xabar qil_»\n"
        "AI matnni tabiiy o'zbekcha sun'iy intellekt ovoziga aylantirib, audio note sifatida jo'natadi.\n\n"
        "3️⃣ **24/7 Ishlash:**\n"
        "Loyiha Render platformasida doimiy ishlaydi. Telefoningiz o'chiq bo'lsa ham bot buyruqlarni qabul qiladi."
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# ========================================================
# ASOSIY BUYRUQ VA MATNLARNI QAYTA ISHLASH (AI AGENT)
# ========================================================
@dp.message(F.text)
async def handle_user_command(message: Message):
    user_prompt = message.text.strip()
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    wait_msg = await message.answer("⏳ _Agent buyruqni tahlil qilmoqda..._", parse_mode=ParseMode.MARKDOWN)

    try:
        # Gemini AI tahlili
        decision = await ai_agent.process_command(user_prompt)
        action = decision.get("action", "clarify")
        recipient = decision.get("recipient", "").strip()
        message_text = decision.get("message_text", "").strip()
        voice = decision.get("voice", settings.DEFAULT_VOICE)

        if action == "clarify" or not recipient:
            await wait_msg.edit_text(
                f"🤔 **Tushunarsiz buyruq yoki qabul qiluvchi aniqlanmadi:**\n\n"
                f"{message_text or 'Iltimos, kimga nima deb yozish kerakligini aniqroq yozing.'}\n\n"
                f"Misol: «_Ustozimga salom deb yoz_»",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # 1. MATNLI XABAR YUBORISH
        if action == "send_message":
            res = await userbot_manager.send_text_message(recipient, message_text)
            target_name = res.get("target_name", recipient)
            await wait_msg.edit_text(
                f"✅ **Xabar yuborildi!**\n\n"
                f"👤 **Qabul qiluvchi:** `{target_name}`\n"
                f"💬 **Yuborilgan matn:**\n> {message_text}\n\n"
                f"⚡ *Avtomatik rejimda sizning nomingizdan yetkazildi.*",
                parse_mode=ParseMode.MARKDOWN
            )

        # 2. OVOZLI XABAR (GOLOS) YUBORISH
        elif action == "send_voice":
            await message.bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)
            res = await userbot_manager.send_voice_message(recipient, message_text, voice=voice)
            target_name = res.get("target_name", recipient)
            await wait_msg.edit_text(
                f"🎙 **Ovozli xabar (Golos) yuborildi!**\n\n"
                f"👤 **Qabul qiluvchi:** `{target_name}`\n"
                f"🔊 **Ovoz turi:** `{voice}`\n"
                f"💬 **Aytilgan matn:**\n> {message_text}\n\n"
                f"⚡ *Avtomatik rejimda ovozli xabar qilib yetkazildi.*",
                parse_mode=ParseMode.MARKDOWN
            )

        else:
            await wait_msg.edit_text(f"Noma'lum harakat: {action}")

    except Exception as e:
        logger.error(f"Xabar yuborishda xatolik: {e}", exc_info=True)
        await wait_msg.edit_text(
            f"❌ **Xatolik yuz berdi:**\n`{str(e)}`\n\n"
            f"Iltimos, qabul qiluvchi nomi yoki buyruqni tekshirib qayta urinib ko'ring.",
            parse_mode=ParseMode.MARKDOWN
        )
