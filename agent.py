"""
AI Agent moduli (Kengaytirilgan v2.0):
Google Gemini AI orqali:
1. Foydalanuvchi niyatini (Intent) aniqlaydi:
   - smart_reply: Guruh yoki shaxsiy chatdagi oxirgi xabarga munosib iqtibos (reply) bilan javob berish
   - read_and_summarize: Chatda nimalar bo'layotganini o'qib, qisqa mazmunini tushuntirib berish
   - update_profile: Bio, Ism, Familiya yoki @username ni o'zgartirish
   - get_profile: Profil ma'lumotlarini ko'rish
   - send_message: Oddiy to'g'ridan-to'g'ri xabar jo'natish
   - send_voice: Ovozli xabar (golos) jo'natish
2. Chat tarixini o'qib, kim nima deganini (masalan: Aziz / Aza) tushunadi va Toshkent personasida javob tuzadi.
"""
import json
import logging
import socket
from typing import Any, Dict, List, Optional
import aiohttp

from config import settings

logger = logging.getLogger(__name__)

PERSONA_RULES = """
MUHIM YOZISH USLUBI VA PERSONA QOIDALARI (100% RIOYA QILINISHI SHART):
1. Umumiy ohang va aksent:
   - Toshkent shahar yoshlarining jonli tili: Tabiiy, do'stona, erkin va o'ta lo'nda.
   - Hech qanday kitobiy, sun'iy yoki rasmiy ("Hurmatli...", "Ma'lum qilamanki...") jumlalar MUTLAQO ishlatilmaydi.
   - Jumlalar qisqa, 1-2 qatordan oshmaydi.
2. Xos leksika va grammatik shakllar:
   - Qo'shimchalar: -votti / -votdi (qivotti, ishlavotti, uxlashvotti, orivatti, dvomman), -dee / -de (mumkunmasdee, bilmadimde, qildimde).
   - Fe'llar: etdim, ettim, etib, boromiman, kelomiman, ob kelaman, chiqaztirib, korur, tashur.
   - Sevimli so'zlar: qchu, karoche, prosta, tochno, daje, nma, nmaga, hoz, botta, oshatga, bomasam, hop, hop boladi, xop, ok, da, yo, yoq.
3. Qabul qiluvchiga qarab moslashish:
   - Ustozlar bilan (Behruz aka, Ustoz):
     Boshlanishi: "Assalamu Alaykum Ustoz" yoki "Assalomu alaykum ustoz".
     Tasdiq: "Hop ustoz", "Hop boladi", "Tushunarli", "Raxmat ustoz".
     Ohang: Hurmat bilan, ammo qotib qolmagan, jonli va ochiq.
   - Ota-ona (Adajon, Oyijon):
     "Adajon", "Oyijon", "Hop boladi", "Tel qilaman", "Osha etganizni".
   - Do'stlar / Jigar / Tengdoshlar / Guruhdoshlar (Aziz, Aza, Bilol, Islom, Humoyun, sinfdoshlar):
     Murojaat: "jigar", "jgar", "jigarim", "bro", "jonkam".
     Xabarlar: "Qalesan jigar", "nma gap", "karoche...", "qchu...", "bla", "haha", "axaxa".
   - Ingliz tili aralashgan do'stlar:
     "bro", "bruh", "yea", "got it", "lol", "crazy".
4. Format va orfografiya:
   - Tutuq belgisi (') tushirib qoldiriladi: boladi, bomasam, ogir.
   - Xabarlar qisqa va aniq bo'ladi.
"""

ROUTER_SYSTEM_PROMPT = f"""
Sen — Muhammad Ali Gafurovning Telegram AI Boshqaruvchisissan.
Foydalanuvchi (Muhammad Ali) buyrug'ini tahlil qilib, qaysi harakatni bajarish kerakligini aniqla.

{PERSONA_RULES}

HARAKAT TURLARI (action):
1. "smart_reply": Agar Muhammad Ali biror chatdagi/guruhdagi biror odamga (masalan: Azizga, Ustozga) yoki oxirgi xabarga javob berishni so'rasa.
   Misollar:
   - "Sinfdoshlar guruhiga Aziz yozgan oxirgi xabariga javob ber"
   - "Sinfdoshlarga javob yoz"
   - "Ustozga javob ber"
   Parameters:
   - chat: Qaysi chat yoki guruh (masalan: "sinfdoshlar", "ustoz")
   - target_person: Kimning xabariga javob berilishi kerak (masalan: "Aziz", "Ustoz", yoki null)
   - instruction: Foydalanuvchining qo'shimcha ko'rsatmasi (agar bo'lsa)
   - voice: har doim "uz-UZ-SardorNeural" yoki "uz-UZ-MadinaNeural" (hech qachon boolean true/false emas!)

2. "read_and_summarize": Agar chatdagi oxirgi gaplar, nima bo'layotgani haqida so'rasa.
   Misollar:
   - "Sinfdoshlar guruhida nima gaplar?"
   - "Guruhda nima yozishvotti oxirgi payt?"
   Parameters:
   - chat: Chat nomi

3. "update_profile": Profil sozlamalarini (Bio, Ism, Familiya, Username) o'zgartirish.
   Misollar:
   - "Bio ni 'AI Developer' deb o'zgartir"
   - "Ismimni Muhammadali qil"
   - "Usernameni gg_ali ga o'zgartir"
   Parameters:
   - first_name, last_name, about, username (faqat o'zgartirilishi kerak bo'lganlari)

4. "get_profile": Profil ma'lumotlarini ko'rsatish so'ralsa.
   Misollar: "Profilimni ko'rsat", "Bio'da nima yozilgan?"

5. "send_voice": Ovozli xabar jo'natish so'ralsa (agar oldingi xabarlarni o'qish shart bo'lmasa).
   Misollar: "Adajonga kech qolaman deb golos yubor"
   Parameters: recipient, message_text, voice

6. "send_message": Oddiy to'g'ridan-to'g'ri xabar jo'natish.
   Misollar: "Ustozimga salom deb yoz", "Bilolga nma gap deb yoz"
   Parameters: recipient, message_text

7. "clarify": Agar umuman tushunarsiz bo'lsa.

JAVOBNI FAQAT QUYIDAGI JSON FORMATIDA BER:
{{
  "action": "smart_reply" | "read_and_summarize" | "update_profile" | "get_profile" | "send_message" | "send_voice" | "clarify",
  "chat": "chat yoki guruh nomi",
  "recipient": "qabul qiluvchi",
  "target_person": "kimga javob",
  "instruction": "yo'riqnoma",
  "message_text": "matn",
  "voice": "uz-UZ-SardorNeural",
  "first_name": null,
  "last_name": null,
  "about": null,
  "username": null,
  "explanation": "qisqa izoh"
}}
"""


class AIAgent:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.models_to_try = [settings.GEMINI_MODEL, "gemini-3.6-flash", "gemini-2.5-flash"]

    async def _call_gemini(self, system_instruction: str, user_content: str) -> Optional[Dict[str, Any]]:
        """Gemini API chaqiruvi yordamchi funksiyasi."""
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.3
            }
        }
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        timeout = aiohttp.ClientTimeout(total=25)

        async with aiohttp.ClientSession(connector=connector) as session:
            for model_name in self.models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                try:
                    async with session.post(url, json=payload, timeout=timeout) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                text = candidates[0]["content"]["parts"][0]["text"].strip()
                                return json.loads(text)
                        else:
                            err = await resp.text()
                            logger.warning(f"Gemini {model_name} status {resp.status}: {err}")
                except Exception as e:
                    logger.warning(f"Gemini chaqiruvida xatolik ({model_name}): {e}")
                    continue
        return None

    async def classify_intent(self, user_prompt: str) -> Dict[str, Any]:
        """Muhammad Alining kiritgan buyrug'i niyatini aniqlash."""
        res = await self._call_gemini(ROUTER_SYSTEM_PROMPT, user_prompt)
        if res:
            return res
        return {
            "action": "clarify",
            "explanation": "Gemini bilan bog'lanib bo'lmadi."
        }

    async def generate_contextual_reply(
        self,
        chat_name: str,
        messages: List[Dict[str, Any]],
        target_person: Optional[str],
        instruction: Optional[str]
    ) -> Dict[str, Any]:
        """
        Guruh/chat tarixini tahlil qilib, target_person'ning oxirgi xabariga
        Muhammad Alining Toshkent personasida mos javob tayyorlaydi.
        """
        # Xabarlar kontekstini yig'amiz
        formatted_history = []
        for m in messages:
            sender = m.get("sender_name", "Noma'lum")
            s_user = f" (@{m['sender_username']})" if m.get("sender_username") else ""
            formatted_history.append(f"[id={m['id']}] {sender}{s_user}: {m['text']}")

        history_str = "\n".join(formatted_history)

        prompt = f"""
Suhbat: {chat_name}
Oxirgi xabarlar tarixi:
{history_str}

Foydalanuvchi (Muhammad Ali) talabi:
- Kimga javob berish: {target_person or "Oxirgi xabar egasiga"}
- Ko'rsatma: {instruction or "Vaziyatga va uning so'zlariga mos javob ber"}

VAZIFA:
1. Tarixdan {target_person or 'oxirgi'} shaxsning eng so'nggi xabarini top. 
   (Eslatma: 'Aziz' desa, 'Aza' yoki shunga o'xshash qisqartmalarni ham tushun!).
2. Shu xabarga Muhammad Alining yozish uslubida (Toshkent jonli tili, do'stona, samimiy) munosib javob matnini tuz.

{PERSONA_RULES}

Javobni quyidagi JSON formatida ber:
{{
  "target_message_id": 12345,
  "sender_name": "Kimning xabari",
  "quoted_text": "U yozgan xabar matni",
  "reply_text": "Muhammad Ali nomidan yozilgan aniq javob"
}}
"""
        system_instr = "Sen Telegram suhbatlari kontekstini tahlil qiluvchi va Muhammad Ali nomidan munosib javob yozuvchi AI yordamchisan."
        res = await self._call_gemini(system_instr, prompt)
        return res or {}

    async def summarize_chat(self, chat_name: str, messages: List[Dict[str, Any]]) -> str:
        """Guruhdagi so'nggi suhbatlarni qisqa va lo'nda tushuntirib berish."""
        formatted_history = []
        for m in messages:
            formatted_history.append(f"{m['sender_name']}: {m['text']}")
        history_str = "\n".join(formatted_history)

        prompt = f"""
Chat: {chat_name}
Oxirgi xabarlar:
{history_str}

Vazifa: Ushbu suhbatda nimalar gaplashilganini Muhammad Aliga o'zbek tilida (Toshkent uslubida, lo'nda va tushunarli) 2-4 jumlada tushuntirib ber.
"""
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}]
        }
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        timeout = aiohttp.ClientTimeout(total=20)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={self.api_key}"

        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=payload, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Summarize xatolik: {e}")
        return "Suhbat mazmunini umumlashtirishda xatolik yuz berdi."


ai_agent = AIAgent()
