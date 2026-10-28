"""
Telethon Userbot moduli:
Muhammad Alining shaxsiy Telegram hisobi nomidan xabarlarni o'qish,
kontaktlarni qidirish, matnli xabarlar va Edge-TTS ovozli xabarlarni (golos)
yuborish vazifalarini bajaradi.
"""
import asyncio
import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

import edge_tts
from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, User

from config import settings

logger = logging.getLogger(__name__)


class UserbotManager:
    def __init__(self):
        self.session_str = settings.TELEGRAM_STRING_SESSION
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        self.client: Optional[TelegramClient] = None
        self._cached_dialogs: List[Dict[str, Any]] = []
        self._last_dialogs_fetch: float = 0.0

    async def start(self):
        """Telethon mijozini ishga tushirish va ulanishni tekshirish."""
        logger.info("Telethon Userbot mijoziga ulanmoqda...")
        self.client = TelegramClient(
            StringSession(self.session_str),
            self.api_id,
            self.api_hash
        )
        await self.client.connect()
        if not await self.client.is_user_authorized():
            raise RuntimeError(
                "Xatolik: Telethon sessiyasi tasdiqlanmagan (unauthorized)! "
                "Iltimos, sessiya kalitini qayta tekshiring."
            )
        me = await self.client.get_me()
        logger.info(f"Telethon muvaffaqiyatli ulandi! Egasi: {me.first_name} (@{me.username}) ID={me.id}")
        await self.refresh_dialogs()

    async def stop(self):
        """Telethon mijozini to'xtatish."""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            logger.info("Telethon Userbot to'xtatildi.")

    def is_connected(self) -> bool:
        return bool(self.client and self.client.is_connected())

    async def refresh_dialogs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Oxirgi suhbatlar ro'yxatini yangilash va keshda saqlash."""
        if not self.client:
            return []
        dialogs = []
        try:
            async for d in self.client.iter_dialogs(limit=limit):
                username = getattr(d.entity, "username", None)
                first_name = getattr(d.entity, "first_name", "")
                last_name = getattr(d.entity, "last_name", "")
                title = getattr(d.entity, "title", "")
                kind = "group" if d.is_group else "channel" if d.is_channel else "user"
                
                dialogs.append({
                    "id": d.id,
                    "name": d.name or "",
                    "first_name": first_name or "",
                    "last_name": last_name or "",
                    "title": title or "",
                    "username": username or "",
                    "type": kind,
                    "entity": d.entity
                })
            self._cached_dialogs = dialogs
            self._last_dialogs_fetch = time.time()
        except Exception as e:
            logger.error(f"Dialoglarni olishda xatolik: {e}")
        return self._cached_dialogs

    def _format_entity_name(self, entity: Any) -> str:
        """Entity nomini chiroyli formatda chiqarish."""
        if not entity:
            return "Noma'lum"
        first = getattr(entity, "first_name", None) or getattr(entity, "title", None) or ""
        last = getattr(entity, "last_name", None)
        username = getattr(entity, "username", None)
        full = f"{first} {last}".strip() if last else first
        return f"{full} (@{username})" if username else full

    async def resolve_peer(self, target: str) -> Tuple[Any, str]:
        """
        Qabul qiluvchi identifikatorini entity ob'ektiga aylantirish:
        1. Known aliases (ustoz, adajon, va h.k.)
        2. Raqamli Telegram ID
        3. @username
        4. Keshdagi suhbatlar nomidan qidiruv
        5. cl.get_entity() to'g'ridan-to'g'ri chaqiruv
        """
        if not self.client:
            raise RuntimeError("Telethon mijozi ulanmagan!")

        cleaned = str(target).strip()
        lowered = cleaned.lower()

        # 1. Alias orqali tekshirish
        for alias_key, alias_id in settings.KNOWN_ALIASES.items():
            if alias_key in lowered:
                cleaned = alias_id
                break

        # Keshni yangilab olish agar eskirgan bo'lsa (10 daqiqa)
        if time.time() - self._last_dialogs_fetch > 600:
            await self.refresh_dialogs()

        # 2. Agar raqam bo'lsa (ID)
        is_num = cleaned.lstrip("-").isdigit()
        if is_num:
            peer_id = int(cleaned)
            # Avval keshdan qidiramiz
            for d in self._cached_dialogs:
                if d["id"] == peer_id:
                    return d["entity"], d["name"]
            try:
                entity = await self.client.get_entity(peer_id)
                return entity, self._format_entity_name(entity)
            except Exception as e:
                logger.warning(f"ID orqali entity topilmadi ({peer_id}): {e}")

        # 3. Agar @username bo'lsa
        if cleaned.startswith("@"):
            uname = cleaned.lstrip("@").lower()
            for d in self._cached_dialogs:
                if d["username"].lower() == uname:
                    return d["entity"], d["name"]
            try:
                entity = await self.client.get_entity(cleaned)
                return entity, self._format_entity_name(entity)
            except Exception as e:
                logger.warning(f"Username orqali entity topilmadi ({cleaned}): {e}")

        # 4. Dialoglar ro'yxatidan qidirish (ism/familiya/nom bo'yicha)
        search_term = lowered.lstrip("@")
        for d in self._cached_dialogs:
            d_name = d["name"].lower()
            d_user = d["username"].lower()
            if search_term == d_user or search_term in d_name:
                return d["entity"], d["name"]

        # 5. So'nggi chora: get_entity orqali qidirib ko'rish
        try:
            entity = await self.client.get_entity(cleaned)
            return entity, self._format_entity_name(entity)
        except Exception as e:
            raise ValueError(f"Qabul qiluvchi topilmadi: '{target}'. Xatolik: {e}")

    async def send_text_message(self, recipient: str, text: str) -> Dict[str, Any]:
        """Muhammad Alining nomidan matnli xabar yuborish."""
        entity, target_name = await self.resolve_peer(recipient)
        msg = await self.client.send_message(entity, text)
        return {
            "success": True,
            "target_name": target_name,
            "target_id": getattr(entity, "id", None),
            "message_id": msg.id,
            "text": text,
            "type": "text"
        }

    async def send_voice_message(
        self,
        recipient: str,
        text: str,
        voice: Optional[str] = None
    ) -> Dict[str, Any]:
        """Muhammad Alining nomidan matnni sun'iy intellekt ovoziga aylantirib (golos) yuborish."""
        entity, target_name = await self.resolve_peer(recipient)
        selected_voice = voice or settings.DEFAULT_VOICE

        # Vaqtinchalik audio fayl yaratish
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"voice_{int(time.time() * 1000)}.ogg")

        try:
            communicate = edge_tts.Communicate(text, selected_voice)
            await communicate.save(temp_file)

            # Telegram'ga voice note (dumaloq emas, to'g'ri ogg ovozli xabar) shaklida jo'natish
            msg = await self.client.send_file(
                entity,
                temp_file,
                voice_note=True
            )

            return {
                "success": True,
                "target_name": target_name,
                "target_id": getattr(entity, "id", None),
                "message_id": msg.id,
                "text": text,
                "voice": selected_voice,
                "type": "voice"
            }
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    async def read_recent_messages(self, recipient: str, limit: int = 5) -> List[str]:
        """Chat tarixidan oxirgi xabarlarni o'qish."""
        entity, target_name = await self.resolve_peer(recipient)
        history = []
        async for m in self.client.iter_messages(entity, limit=limit):
            if m.text:
                who = "Men" if m.out else target_name
                history.append(f"[{m.date.strftime('%H:%M')}] {who}: {m.text}")
        return list(reversed(history))


userbot_manager = UserbotManager()
