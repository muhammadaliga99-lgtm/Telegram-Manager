"""
Telegram Bot moduli (Kengaytirilgan v2.0 - aiogram v3):
- Smart Reply (Kontekst va guruhdagi aniq odamning oxirgi xabariga javob berish)
- PFP Profil rasmini o'zgartirish (Foydalanuvchi rasm yuborganda)
- Bio, Ism, Familiya va @username sozlamalarini boshqarish
- Chatlardagi suhbatlarni umumlashtirish (summarize)
- Matnli va Edge-TTS ovozli xabarlarni avtomatik yetkazish
- 100% Xavfsizlik: Faqat ADMIN_USER_ID uchun ochiq.
"""
import logging
import os
import tempfile
import time
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
# XAVFSIZLIK MIDDLEWARE: Faqat Bot Egasi (ADMIN_USER_ID)
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
        "🤖 **Telegram Manager AI Agent (v2.0)** to'liq xizmatingizda!\n\n"
        "Endi siz nafaqat xabar yozish, balki Telegram'dagi **HAMMA narsani** boshqara olasiz:\n\n"
        "💬 **Kontekstli Aqlli Javoblar (Smart Reply):**\n"
        "• _Sinfdoshlar guruhiga Aziz yozgan oxirgi xabariga javob ber_\n"
        "• _Ustozimga oxirgi gaplariga mos javob yoz_\n\n"
        "🖼 **PFP / Profil Sozlamalari:**\n"
        "• Botga rasm tashlang ➔ Profil rasmingiz (PFP) o'zgaradi!\n"
        "• _Bio ni 'Full-Stack & AI Engineer' deb o'zgartir_\n"
        "• _Profilim ma'lumotlarini ko'rsat_\n\n"
        "📊 **Guruhlarni O'qish (Summary):**\n"
        "• _Sinfdoshlar guruhida nima gaplar bo'lyapti?_\n\n"
        "🎙 **Ovozli Goloslar va Matnlar:**\n"
        "• _Adajonga yo'ldaman deb golos yubor_\n"
        "• _Ustozimga salom deb yoz_\n\n"
        "⚙️ /status | /profile | /contacts | /help"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    """Joriy profil ma'lumotlarini ko'rsatish."""
    try:
        p = await userbot_manager.get_my_profile()
        text = (
            "👤 **Sizning Telegram Profilingiz:**\n\n"
            f"• **Ism:** {p['first_name']} {p['last_name']}\n"
            f"• **Username:** @{p['username']}\n"
            f"• **Telefon:** `{p['phone']}`\n"
            f"• **Bio (About):** _{p['about']}_\n"
            f"• **ID:** `{p['id']}`"
        )
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.answer(f"Profil ma'lumotlarini olishda xatolik: {e}")


@dp.message(Command("status"))
async def cmd_status(message: Message):
    userbot_status = "🟢 Ulandi (Faol)" if userbot_manager.is_connected() else "🔴 Ulanmagan"
    text = (
        "📊 **Tizim Holati:**\n\n"
        f"• **Telegram Userbot:** {userbot_status}\n"
        f"• **AI Model:** `{settings.GEMINI_MODEL}` (Google Gemini)\n"
        f"• **Standart Ovoz (TTS):** `{settings.DEFAULT_VOICE}`\n"
        f"• **Imkoniyatlar:** Smart Reply, PFP Changer, Bio Editor, Summary, Voice Note\n"
        f"• **Xavfsizlik:** 🔒 Faqat siz (ID: `{settings.ADMIN_USER_ID}`)\n"
        f"• **Cloud:** 🌐 Render 24/7 (Port: `{settings.PORT}`)"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("contacts"))
async def cmd_contacts(message: Message):
    lines = ["📇 **Tezkor Kontaktlar va Guruhlar:**\n"]
    for alias, peer_id in settings.KNOWN_ALIASES.items():
        lines.append(f"• `{alias}` ➔ `{peer_id}`")
    lines.append("\n💡 *Barcha guruhlar va kontaktlar nomini aqlli qidiruv (Fuzzy) orqali tushunadi.*")
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ========================================================
# RASM YUBORILGANDA: PFP (PROFIL RASMI) QILISH
# ========================================================
@dp.message(F.photo)
async def handle_photo(message: Message):
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
    wait_msg = await message.answer("⏳ _Rasm qabul qilindi, profil rasmi (PFP) o'rnatilmoqda..._", parse_mode=ParseMode.MARKDOWN)

    temp_path = os.path.join(tempfile.gettempdir(), f"pfp_{int(time.time())}.jpg")
    try:
        # Eng yuqori sifatli rasmni yuklab olamiz
        photo = message.photo[-1]
        await message.bot.download(photo.file_id, destination=temp_path)

        res = await userbot_manager.update_profile_photo(temp_path)
        await wait_msg.edit_text(
            "🖼 **Muvaffaqiyatli!**\n\n"
            "Telegram akkauntingiz profil rasmi (PFP avatar) yangilandi! ✨",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"PFP yangilashda xatolik: {e}", exc_info=True)
        await wait_msg.edit_text(f"❌ Profil rasmini o'zgartirishda xatolik: `{e}`", parse_mode=ParseMode.MARKDOWN)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ========================================================
# ASOSIY BUYRUQLAR (AI AGENT MATNLI HANDLER)
# ========================================================
@dp.message(F.text)
async def handle_text_command(message: Message):
    user_prompt = message.text.strip()
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    wait_msg = await message.answer("⏳ _Agent tahlil qilmoqda..._", parse_mode=ParseMode.MARKDOWN)

    try:
        # 1. Niyatni (Intent) aniqlash
        intent = await ai_agent.classify_intent(user_prompt)
        action = intent.get("action", "clarify")

        # ----------------------------------------------------
        # HARAKAT 1: SMART REPLY (Guruh/Chatdagi xabarga munosib javob)
        # ----------------------------------------------------
        if action == "smart_reply":
            chat_target = intent.get("chat") or intent.get("recipient")
            target_person = intent.get("target_person")
            instruction = intent.get("instruction")
            is_voice = intent.get("voice", False)

            if not chat_target:
                await wait_msg.edit_text("Qaysi guruh yoki chat ekanligi aniqlanmadi.")
                return

            await wait_msg.edit_text("🔍 _Suhbat tarixi o'qilmoqda va munosib javob tayyorlanmoqda..._", parse_mode=ParseMode.MARKDOWN)

            # Tarixni o'qish
            messages, chat_name, entity = await userbot_manager.get_recent_messages(chat_target, limit=15)
            if not messages:
                await wait_msg.edit_text(f"«{chat_name}» chatidan xabarlar topilmadi.")
                return

            # Gemini orqali kontekstli javob generatsiya qilish
            decision = await ai_agent.generate_contextual_reply(
                chat_name,
                messages,
                target_person,
                instruction
            )

            target_msg_id = decision.get("target_message_id")
            sender_name = decision.get("sender_name", target_person or "Suhbatdosh")
            quoted_text = decision.get("quoted_text", "")
            reply_text = decision.get("reply_text")

            if not reply_text:
                await wait_msg.edit_text("Javob matnini shakllantirib bo'lmadi.")
                return

            # Yuborish (ovozli yoki matnli)
            if is_voice:
                await message.bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)
                await userbot_manager.send_voice_message(
                    chat_target,
                    reply_text,
                    reply_to_msg_id=target_msg_id
                )
                type_label = "🎙 Ovozli golos (iqtibos bilan)"
            else:
                await userbot_manager.send_text_message(
                    chat_target,
                    reply_text,
                    reply_to_msg_id=target_msg_id
                )
                type_label = "💬 Matnli xabar (iqtibos bilan)"

            quote_block = f"\n💬 **{sender_name}ning xabari:** «_{quoted_text}_»" if quoted_text else ""
            await wait_msg.edit_text(
                f"✅ **Munosib javob yuborildi!**\n\n"
                f"👥 **Suhbat:** `{chat_name}`{quote_block}\n"
                f"↩️ **Sizning javobingiz:**\n> {reply_text}\n\n"
                f"⚡ *{type_label} avtomatik yetkazildi.*",
                parse_mode=ParseMode.MARKDOWN
            )

        # ----------------------------------------------------
        # HARAKAT 2: SUHBAT MAZMUNINI O'QISH (SUMMARIZE)
        # ----------------------------------------------------
        elif action == "read_and_summarize":
            chat_target = intent.get("chat") or intent.get("recipient")
            if not chat_target:
                await wait_msg.edit_text("Qaysi guruhni o'qish kerakligi aniqlanmadi.")
                return

            await wait_msg.edit_text(f"📖 _«{chat_target}» guruhidagi suhbatlar o'qilmoqda..._", parse_mode=ParseMode.MARKDOWN)
            messages, chat_name, entity = await userbot_manager.get_recent_messages(chat_target, limit=20)
            summary = await ai_agent.summarize_chat(chat_name, messages)

            await wait_msg.edit_text(
                f"📋 **«{chat_name}» guruhidagi oxirgi gaplar mazmuni:**\n\n"
                f"{summary}",
                parse_mode=ParseMode.MARKDOWN
            )

        # ----------------------------------------------------
        # HARAKAT 3: PROFIL SOZLAMALARINI O'ZGARTIRISH (BIO, ISM, USERNAME)
        # ----------------------------------------------------
        elif action == "update_profile":
            fn = intent.get("first_name")
            ln = intent.get("last_name")
            about = intent.get("about")
            username = intent.get("username")

            results = []
            if fn or ln or about:
                res = await userbot_manager.update_profile(first_name=fn, last_name=ln, about=about)
                if about:
                    results.append(f"• **Bio:** «_{about}_»")
                if fn:
                    results.append(f"• **Ism:** «{fn}»")

            if username:
                await userbot_manager.update_username(username)
                results.append(f"• **Username:** @{username}")

            if results:
                await wait_msg.edit_text(
                    "⚙️ **Profil sozlamalari yangilandi:**\n\n" + "\n".join(results),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await wait_msg.edit_text("O'zgartirish uchun ma'lumot topilmadi.")

        # ----------------------------------------------------
        # HARAKAT 4: PROFIL MA'LUMOTLARINI KO'RSATISH
        # ----------------------------------------------------
        elif action == "get_profile":
            p = await userbot_manager.get_my_profile()
            await wait_msg.edit_text(
                "👤 **Sizning Profilingiz:**\n\n"
                f"• **Ism:** {p['first_name']} {p['last_name']}\n"
                f"• **Username:** @{p['username']}\n"
                f"• **Bio (About):** _{p['about']}_\n"
                f"• **ID:** `{p['id']}`",
                parse_mode=ParseMode.MARKDOWN
            )

        # ----------------------------------------------------
        # HARAKAT 5: HAQIQIY RASM (PHOTO) YUBORISH
        # ----------------------------------------------------
        elif action == "send_photo":
            recipient = intent.get("recipient") or intent.get("chat")
            image_query = intent.get("image_query") or user_prompt
            caption = intent.get("caption") or ""

            if not recipient:
                await wait_msg.edit_text("Qaysi chat yoki guruhga rasm yuborish kerakligi aniqlanmadi.")
                return

            await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
            await wait_msg.edit_text(f"🔍 _«{image_query}» bo'yicha yuqori sifatli foto qidirilmoqda va yuklanmoqda..._", parse_mode=ParseMode.MARKDOWN)

            res = await userbot_manager.send_photo_message(recipient, image_query, caption=caption)
            await wait_msg.edit_text(
                f"🖼 **Haqiqiy rasm (Foto) yuborildi!**\n\n"
                f"👤 **Qabul qiluvchi:** `{res.get('target_name', recipient)}`\n"
                f"📸 **Rasm mavzusi:** _{image_query}_\n"
                f"💬 **Izoh:** {caption or '(izohsiz)'}\n\n"
                f"⚡ *Avtomatik rejimda Muhammad Ali hisobidan yetkazildi.*",
                parse_mode=ParseMode.MARKDOWN
            )

        # ----------------------------------------------------
        # HARAKAT 6: ODDIY MATNLI XABAR YUBORISH
        # ----------------------------------------------------
        elif action == "send_message":
            recipient = intent.get("recipient") or intent.get("chat")
            text = intent.get("message_text")
            if not recipient or not text:
                await wait_msg.edit_text("Qabul qiluvchi yoki xabar matni to'liq emas.")
                return

            res = await userbot_manager.send_text_message(recipient, text)
            await wait_msg.edit_text(
                f"✅ **Xabar yuborildi!**\n\n"
                f"👤 **Qabul qiluvchi:** `{res.get('target_name', recipient)}`\n"
                f"💬 **Yuborilgan matn:**\n> {text}\n\n"
                f"⚡ *Avtomatik rejimda sizning nomingizdan jo'natildi.*",
                parse_mode=ParseMode.MARKDOWN
            )

        # ----------------------------------------------------
        # HARAKAT 6: OVOZLI XABAR (GOLOS) YUBORISH
        # ----------------------------------------------------
        elif action == "send_voice":
            recipient = intent.get("recipient") or intent.get("chat")
            text = intent.get("message_text") or user_prompt
            raw_voice = intent.get("voice")
            voice = raw_voice if (isinstance(raw_voice, str) and raw_voice.startswith("uz-")) else settings.DEFAULT_VOICE

            if not recipient:
                await wait_msg.edit_text("Qabul qiluvchi aniqlanmadi.")
                return

            # Agar foydalanuvchi baqiradigan yoki baland ovozda desa, volume ni oshiramiz
            volume = "+50%" if any(w in user_prompt.lower() for w in ["baqir", "baland", "loud", "qichqir"]) else "+0%"

            await message.bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)
            res = await userbot_manager.send_voice_message(recipient, text, voice=voice, volume=volume)
            await wait_msg.edit_text(
                f"🎙 **Ovozli xabar (Golos) yuborildi!**\n\n"
                f"👤 **Qabul qiluvchi:** `{res.get('target_name', recipient)}`\n"
                f"🔊 **Ovoz turi:** `{voice}`\n"
                f"💬 **Aytilgan matn:**\n> {text}\n\n"
                f"⚡ *Avtomatik rejimda yetkazildi.*",
                parse_mode=ParseMode.MARKDOWN
            )

        else:
            exp = intent.get("explanation", "")
            if exp and not any(w in exp.lower() for w in ["bog'lanib bo'lmadi", "xatolik", "tushunolmadim"]):
                await wait_msg.edit_text(
                    f"🤖 {exp}\n\n"
                    "💡 *Biror harakat bajarish uchun buyruq bering, masalan:*\n"
                    "• _Aza dan hol-ahvol so'ra_\n"
                    "• _Sinfdoshlar guruhiga Aziz yozgan oxirgi xabariga javob ber_\n"
                    "• _Bio ni 'AI Developer' deb o'zgartir_\n"
                    "• _Ustozimga salom deb yoz_",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await wait_msg.edit_text(
                    f"🤔 **Buyruqni tushunolmadim:**\n{exp}\n\n"
                    "Iltimos, aniqroq buyruq bering. Masalan:\n"
                    "• _Aza dan hol-ahvol so'ra_\n"
                    "• _Sinfdoshlar guruhiga Aziz yozgan oxirgi xabariga javob ber_\n"
                    "• _Bio ni 'Developer' deb o'zgartir_\n"
                    "• _Ustozimga salom deb yoz_",
                    parse_mode=ParseMode.MARKDOWN
                )

    except Exception as e:
        logger.error(f"Xatolik yuz berdi: {e}", exc_info=True)
        await wait_msg.edit_text(
            f"❌ **Xatolik yuz berdi:**\n`{str(e)}`",
            parse_mode=ParseMode.MARKDOWN
        )
