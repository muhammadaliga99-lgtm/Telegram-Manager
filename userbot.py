"""
Telethon Userbot moduli (Kengaytirilgan v2.0):
- Xabarlarni o'qish, guruhlar va shaxsiy chatlar tarixini olish
- Kontekstga qarab iqtibos (reply_to) bilan javob qaytarish
- Profil sozlamalari (PFP avatar, Bio, Ism, Username) ni o'zgartirish
- Matnli va Edge-TTS ovozli xabarlarni (golos) yuborish
"""
import asyncio
import json
import logging
import os
import re
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

import edge_tts
from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.contacts import GetContactsRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import Channel, Chat, User

from config import settings

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "guruhi", "guruhiga", "guruh", "chati", "chatiga", "chat",
    "kanali", "kanaliga", "kanal", "aka", "akaga", "opa", "opaga",
    "toga", "togaga", "sinfi", "sinfiga", "ga", "ka", "qa", "a",
    "degan", "kontaktga", "kontakt", "userga", "user"
}

UZBEK_SUFFIXES = (
    "ning", "dan", "dagi", "daka", "dek", "ga", "ka", "qa",
    "ni", "da", "imga", "im", "ing", "imiz", "ingiz", "lari", "lar",
    "jonimga", "jonim", "jonga", "jon", "xon", "voy", "voyim"
)


def _normalize_text(s: str) -> str:
    """Unicode NFKD normalizatsiyasi (matematik, qalin, kursiv shriftlarni oddiy harflarga aylantiradi)."""
    if not s:
        return ""
    norm = unicodedata.normalize("NFKD", s)
    norm = re.sub(r"['`ʻʼ‘“”—]", "", norm)
    return norm.lower().strip()


def _clean_tokens(s: str) -> List[str]:
    norm = _normalize_text(s)
    cleaned = re.sub(r"[^\w\s]", " ", norm)
    tokens = []
    for w in cleaned.split():
        if w in STOP_WORDS or len(w) < 2:
            continue
        tokens.append(w)
        for suff in UZBEK_SUFFIXES:
            if w.endswith(suff) and len(w) - len(suff) >= 3:
                stem = w[:-len(suff)]
                if stem not in STOP_WORDS:
                    tokens.append(stem)
                break
    return list(set(tokens))


def _clean_str(s: str) -> str:
    norm = _normalize_text(s)
    cleaned = re.sub(r"[^\w\s]", " ", norm)
    words = [w for w in cleaned.split() if w not in STOP_WORDS and len(w) > 1]
    return " ".join(words)


def find_web_image(query: str) -> Optional[str]:
    """Internetdan (Wikimedia Commons va Wikipedia) yuqori sifatli rasm qidirish."""
    headers = {"User-Agent": "TelegramManagerBot/2.0 (student; contact: muhammadali@example.com)"}
    clean_q = query.strip()

    # 1. Wikimedia Commons orqali qidirish (Optimallashtirilgan 1280px thumbnail)
    url1 = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrsearch={urllib.parse.quote(clean_q)}&gsrlimit=1&prop=imageinfo&iiprop=url&iiurlwidth=1280&format=json"
    try:
        req = urllib.request.Request(url1, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as r:
            d = json.loads(r.read().decode("utf-8"))
            pages = d.get("query", {}).get("pages", {})
            for k, v in pages.items():
                info = v.get("imageinfo", [])
                if info:
                    return info[0].get("thumburl") or info[0].get("url")
    except Exception as e:
        logger.warning(f"Commons qidiruv xatosi: {e}")

    # 2. Wikipedia maqolasi rasmi
    url2 = f"https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(clean_q)}&gsrlimit=1&prop=pageimages&piprop=thumbnail&pithumbsize=1280&format=json"
    try:
        req = urllib.request.Request(url2, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as r:
            d = json.loads(r.read().decode("utf-8"))
            pages = d.get("query", {}).get("pages", {})
            for k, v in pages.items():
                thumb = v.get("thumbnail", {})
                if "source" in thumb:
                    return thumb["source"]
    except Exception as e:
        logger.warning(f"Wikipedia qidiruv xatosi: {e}")

    return None


class UserbotManager:
    def __init__(self):
        self.session_str = settings.TELEGRAM_STRING_SESSION
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        self.client: Optional[TelegramClient] = None
        self._cached_dialogs: List[Dict[str, Any]] = []
        self._last_dialogs_fetch: float = 0.0
        self._cached_contacts: List[Dict[str, Any]] = []
        self._last_contacts_fetch: float = 0.0

    async def start(self):
        """Telethon mijozini ishga tushirish."""
        logger.info("Telethon Userbot mijoziga ulanmoqda...")
        self.client = TelegramClient(
            StringSession(self.session_str),
            self.api_id,
            self.api_hash
        )
        await self.client.connect()
        if not await self.client.is_user_authorized():
            raise RuntimeError("Xatolik: Telethon sessiyasi tasdiqlanmagan (unauthorized)!")
        me = await self.client.get_me()
        logger.info(f"Telethon muvaffaqiyatli ulandi! Egasi: {me.first_name} (@{me.username}) ID={me.id}")
        await self.refresh_dialogs()
        await self.refresh_contacts()

    async def stop(self):
        """Telethon mijozini to'xtatish."""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            logger.info("Telethon Userbot to'xtatildi.")

    def is_connected(self) -> bool:
        return bool(self.client and self.client.is_connected())

    async def refresh_dialogs(self, limit: int = 60) -> List[Dict[str, Any]]:
        """Oxirgi suhbatlar ro'yxatini olish va keshda saqlash."""
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

    async def refresh_contacts(self) -> List[Dict[str, Any]]:
        """Telegram kontaktlar ro'yxatini olish va keshda saqlash."""
        if not self.client:
            return []
        contacts = []
        try:
            res = await self.client(GetContactsRequest(hash=0))
            for u in res.users:
                fn = u.first_name or ""
                ln = u.last_name or ""
                full = f"{fn} {ln}".strip() if ln else fn
                contacts.append({
                    "id": u.id,
                    "name": full or u.username or f"User {u.id}",
                    "first_name": fn,
                    "last_name": ln,
                    "title": "",
                    "username": u.username or "",
                    "phone": u.phone or "",
                    "type": "contact",
                    "entity": u
                })
            self._cached_contacts = contacts
            self._last_contacts_fetch = time.time()
        except Exception as e:
            logger.error(f"Kontaktlarni olishda xatolik: {e}")
        return self._cached_contacts

    def _format_entity_name(self, entity: Any) -> str:
        if not entity:
            return "Noma'lum"
        first = getattr(entity, "first_name", None) or getattr(entity, "title", None) or ""
        last = getattr(entity, "last_name", None)
        username = getattr(entity, "username", None)
        full = f"{first} {last}".strip() if last else first
        return f"{full} (@{username})" if username else full

    async def resolve_peer(self, target: str) -> Tuple[Any, str]:
        """Aqlli qidiruv orqali peer (chat/foydalanuvchi) ob'ektini topish."""
        if not self.client:
            raise RuntimeError("Telethon mijozi ulanmagan!")

        cleaned = str(target).strip()
        lowered = _normalize_text(cleaned)
        cleaned_words = _clean_str(cleaned)
        target_tokens = set(_clean_tokens(cleaned))

        # 1. Aliaslar orqali tekshirish
        for alias_key, alias_id in settings.KNOWN_ALIASES.items():
            ak = _normalize_text(alias_key)
            if ak == lowered or ak == cleaned_words or lowered.startswith(ak) or (ak in target_tokens):
                cleaned = alias_id
                break

        # Keshni yangilash
        if not self._cached_dialogs or (time.time() - self._last_dialogs_fetch > 300):
            await self.refresh_dialogs()
        if not self._cached_contacts or (time.time() - self._last_contacts_fetch > 300):
            await self.refresh_contacts()

        # 2. Agar raqam bo'lsa (ID)
        is_num = cleaned.lstrip("-").isdigit()
        if is_num:
            peer_id = int(cleaned)
            for d in (self._cached_dialogs + self._cached_contacts):
                if d["id"] == peer_id:
                    return d["entity"], d["name"]
            try:
                entity = await self.client.get_entity(peer_id)
                return entity, self._format_entity_name(entity)
            except Exception as e:
                logger.warning(f"ID orqali entity topilmadi ({peer_id}): {e}")

        # 3. Agar @username bo'lsa
        if cleaned.startswith("@"):
            uname = _normalize_text(cleaned.lstrip("@"))
            for d in (self._cached_dialogs + self._cached_contacts):
                if _normalize_text(d.get("username", "")) == uname:
                    return d["entity"], d["name"]
            try:
                entity = await self.client.get_entity(cleaned)
                return entity, self._format_entity_name(entity)
            except Exception as e:
                logger.warning(f"Username orqali entity topilmadi ({cleaned}): {e}")

        # 4. Aqlli dialoglar va kontaktlar qidiruvi
        all_peers = self._cached_dialogs + self._cached_contacts
        bot_token_id = settings.TELEGRAM_BOT_TOKEN.split(":")[0] if ":" in settings.TELEGRAM_BOT_TOKEN else ""
        
        best_peer = None
        best_score = 0.0

        for p in all_peers:
            pid_str = str(p.get("id", ""))
            # Botning o'ziga xabar yuborishni cheklaymiz
            if bot_token_id and pid_str == bot_token_id:
                continue

            p_clean = _clean_str(p.get("name", ""))
            p_user = _normalize_text(p.get("username", ""))
            p_first = _clean_str(p.get("first_name", ""))
            p_tokens = set(_clean_tokens(p.get("name", ""))) | set(_clean_tokens(p.get("username", "")))

            # Bo'sh nom yoki faqat emoji bo'lgan kontaktlarni nomuvofiq deb hisoblaymiz
            if not p_clean and not p_user:
                continue

            score = 0.0

            # A. Aniq to'liq moslik (Exact match)
            if cleaned_words and (cleaned_words == p_clean or cleaned_words == p_user or cleaned_words == p_first):
                score = 100.0
            # B. Qidiruv so'zi kontakt nomi ichida mavjudligi (masalan: "oyijon" -> "OYIJONIM")
            elif cleaned_words and len(cleaned_words) >= 3 and len(p_clean) >= 3 and cleaned_words in p_clean:
                score = 85.0
            # C. Kontakt nomi qidiruv so'zi ichida mavjudligi (masalan: "Boboxon" -> "boboxonga")
            elif cleaned_words and len(p_clean) >= 3 and p_clean in cleaned_words:
                score = 80.0
            # D. Tokenlar kesishuvi (O'zaklar bo'yicha)
            elif target_tokens and p_tokens:
                overlap = target_tokens.intersection(p_tokens)
                if overlap:
                    score = 60.0 * (len(overlap) / max(len(target_tokens), 1))

            if score > best_score:
                best_score = score
                best_peer = p

        if best_peer and best_score >= 50.0:
            return best_peer["entity"], best_peer["name"]

        # 5. Keshni qayta yangilab oxirgi marta izlash
        await self.refresh_dialogs(limit=100)
        await self.refresh_contacts()
        all_peers = self._cached_dialogs + self._cached_contacts

        for p in all_peers:
            p_clean = _clean_str(p.get("name", ""))
            if not p_clean:
                continue
            if cleaned_words and len(cleaned_words) >= 3 and len(p_clean) >= 3:
                if cleaned_words == p_clean or cleaned_words in p_clean or p_clean in cleaned_words:
                    return p["entity"], p["name"]

        # 6. So'nggi chora: get_entity
        try:
            entity = await self.client.get_entity(cleaned)
            return entity, self._format_entity_name(entity)
        except Exception:
            raise ValueError(f"Qabul qiluvchi topilmadi: '{target}'. Iltimos, kontakt yoki guruh nomini to'g'ri yozing.")

    # ========================================================
    # XABARLAR TARIXI VA KONTEKST OLISH
    # ========================================================
    async def get_recent_messages(self, chat_target: str, limit: int = 15) -> Tuple[List[Dict[str, Any]], str, Any]:
        """Berilgan chatning oxirgi xabarlar tarixini to'liq ma'lumotlari bilan qaytaradi."""
        entity, target_name = await self.resolve_peer(chat_target)
        messages = []
        async for m in self.client.iter_messages(entity, limit=limit):
            sender = await m.get_sender()
            sender_name = "Noma'lum"
            sender_username = ""
            sender_id = m.sender_id

            if sender:
                fn = getattr(sender, "first_name", "") or getattr(sender, "title", "") or ""
                ln = getattr(sender, "last_name", "") or ""
                sender_name = f"{fn} {ln}".strip() if ln else fn
                sender_username = getattr(sender, "username", "") or ""

            messages.append({
                "id": m.id,
                "sender_id": sender_id,
                "sender_name": sender_name,
                "sender_username": sender_username,
                "text": m.text or "[media/fayl]",
                "date": m.date.strftime("%Y-%m-%d %H:%M:%S") if m.date else "",
                "out": m.out
            })

        # Xabarlarni eskidan yangiga qarab tartiblaymiz
        ordered_messages = list(reversed(messages))
        return ordered_messages, target_name, entity

    # ========================================================
    # XABAR VA OVOZLI XABAR YUBORISH (REPLY QO'LLAB-QUVVATLANADI)
    # ========================================================
    async def send_text_message(
        self,
        recipient: str,
        text: str,
        reply_to_msg_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Matnli xabar yuborish (agar reply_to_msg_id berilsa, iqtibos qiladi)."""
        entity, target_name = await self.resolve_peer(recipient)
        msg = await self.client.send_message(
            entity,
            text,
            reply_to=reply_to_msg_id
        )
        return {
            "success": True,
            "target_name": target_name,
            "target_id": getattr(entity, "id", None),
            "message_id": msg.id,
            "reply_to": reply_to_msg_id,
            "text": text,
            "type": "text"
        }

    async def send_voice_message(
        self,
        recipient: str,
        text: str,
        voice: Optional[Any] = None,
        reply_to_msg_id: Optional[int] = None,
        rate: str = "+0%",
        volume: str = "+0%"
    ) -> Dict[str, Any]:
        """Ovozli xabar (Edge-TTS golos) yuborish."""
        entity, target_name = await self.resolve_peer(recipient)
        
        # Ovoz nomi qat'iy str bo'lishi shart (True, None yoki noto'g'ri turlar bo'lsa default olinadi)
        if isinstance(voice, str) and voice.strip() and voice.startswith("uz-"):
            selected_voice = voice.strip()
        else:
            selected_voice = settings.DEFAULT_VOICE

        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"voice_{int(time.time() * 1000)}.ogg")

        try:
            communicate = edge_tts.Communicate(text, selected_voice, rate=rate, volume=volume)
            await communicate.save(temp_file)

            msg = await self.client.send_file(
                entity,
                temp_file,
                voice_note=True,
                reply_to=reply_to_msg_id
            )

            return {
                "success": True,
                "target_name": target_name,
                "target_id": getattr(entity, "id", None),
                "message_id": msg.id,
                "reply_to": reply_to_msg_id,
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

    async def send_photo_message(
        self,
        recipient: str,
        query_or_url: str,
        caption: str = "",
        reply_to_msg_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Internetdan rasm qidirib yoki to'g'ridan-to'g'ri URL bo'yicha haqiqiy rasm (photo) qilib jo'natish."""
        if not self.client:
            raise RuntimeError("Telethon mijozi ulanmagan!")

        entity, target_name = await self.resolve_peer(recipient)

        if query_or_url.startswith("http://") or query_or_url.startswith("https://"):
            image_url = query_or_url
        else:
            image_url = find_web_image(query_or_url)
            if not image_url:
                raise ValueError(f"'{query_or_url}' bo'yicha rasm topilmadi. Iltimos, boshqacha nom bilan qidirib ko'ring.")

        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"photo_{int(time.time() * 1000)}.jpg")

        req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            with open(temp_file, "wb") as f:
                f.write(r.read())

        try:
            msg = await self.client.send_file(
                entity,
                temp_file,
                caption=caption,
                reply_to=reply_to_msg_id
            )
            return {
                "success": True,
                "target_name": target_name,
                "target_id": getattr(entity, "id", None),
                "message_id": msg.id,
                "caption": caption,
                "image_url": image_url,
                "type": "photo"
            }
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    # ========================================================
    # PROFIL VA NASTROYKALARNI BOSHQARISH (PFP, BIO, ISM, USERNAME)
    # ========================================================
    async def update_profile(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        about: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ism, familiya va Bio (about) ma'lumotlarini o'zgartirish."""
        if not self.client:
            raise RuntimeError("Telethon mijozi ulanmagan!")

        kwargs = {}
        if first_name is not None:
            kwargs["first_name"] = first_name
        if last_name is not None:
            kwargs["last_name"] = last_name
        if about is not None:
            kwargs["about"] = about

        await self.client(UpdateProfileRequest(**kwargs))
        me = await self.client.get_me()
        return {
            "success": True,
            "first_name": me.first_name,
            "last_name": me.last_name,
            "about": about,
            "username": me.username
        }

    async def update_profile_photo(self, photo_path: str) -> Dict[str, Any]:
        """Profil rasmini (PFP avatar) yangilash."""
        if not self.client:
            raise RuntimeError("Telethon mijozi ulanmagan!")
        if not os.path.exists(photo_path):
            raise FileNotFoundError(f"Rasm topilmadi: {photo_path}")

        uploaded_file = await self.client.upload_file(photo_path)
        await self.client(UploadProfilePhotoRequest(file=uploaded_file))
        return {
            "success": True,
            "message": "Profil rasmi muvaffaqiyatli o'zgartirildi!"
        }

    async def update_username(self, username: str) -> Dict[str, Any]:
        """Telegram @username'ni o'zgartirish."""
        if not self.client:
            raise RuntimeError("Telethon mijozi ulanmagan!")
        clean_user = username.lstrip("@").strip()
        await self.client(UpdateUsernameRequest(username=clean_user))
        return {
            "success": True,
            "username": clean_user
        }

    async def get_my_profile(self) -> Dict[str, Any]:
        """Joriy profil ma'lumotlarini olish."""
        if not self.client:
            raise RuntimeError("Telethon mijozi ulanmagan!")
        me = await self.client.get_me()
        full = await self.client(GetFullUserRequest(me))
        return {
            "id": me.id,
            "first_name": me.first_name or "",
            "last_name": me.last_name or "",
            "username": me.username or "",
            "phone": me.phone or "",
            "about": getattr(full.full_user, "about", "") or "(bo'sh)"
        }


userbot_manager = UserbotManager()
