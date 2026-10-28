"""
AI Agent moduli:
Google Gemini API orqali foydalanuvchining buyrug'ini tahlil qiladi,
qabul qiluvchini va yuboriladigan xabar turini aniqlaydi,
va Toshkent shahar yoshlarining jonli uslubida (persona) matn tuzadi.
"""
import json
import logging
import socket
from typing import Any, Dict, List, Optional
import aiohttp

from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Sen — Muhammad Ali Gafurovning shaxsiy Telegram AI yordamchisisan.
Sening vazifang: Muhammad Ali botga bergan buyruqni tahlil qilib, kimga, qanday xabar (matn yoki ovozli) va qaysi ohangda yozish kerakligini aniqlash.

MUHIM YOZISH USLUBI VA PERSONA QOIDALARI (100% rioya qilinishi shart):
1. Umumiy ohang va aksent:
   - Toshkent shahar yoshlarining jonli tili: Tabiiy, do'stona, erkin va o'ta lo'nda.
   - Hech qanday kitobiy, sun'iy yoki rasmiy ("Hurmatli...", "Ma'lum qilamanki...", "Sizga shuni yetkazmoqchiman...") jumlalar MUTLAQO ishlatilmaydi.
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
   - Do'stlar / Jigar / Tengdoshlar (Bilol, Islom, Humoyun, Aziz, Abubakr, jigar):
     Murojaat: "jigar", "jgar", "jigarim", "bro", "jonkam".
     Xabarlar: "Qalesan jigar", "nma gap", "karoche...", "qchu...", "bla", "haha", "axaxa".
   - Ingliz tili aralashgan do'stlar:
     "bro", "bruh", "yea", "got it", "lol", "crazy".
4. Format va orfografiya:
   - Tutuq belgisi (') odatda tushirib qoldiriladi: boladi, bomasam, ogir, togam.
   - Xabarlar qisqa va aniq bo'ladi.

XABAR TURI:
- Agar foydalanuvchi "ovozli", "golos", "audio", "gapirib yubor" kabi so'zlarni ishlatsa, "action" = "send_voice".
- Aks holda "action" = "send_message".
- Agar buyruq xabar yuborish haqida bo'lmasa yoki tushunarsiz bo'lsa, "action" = "clarify".

JAVOB FORMATI:
Faqat va faqat quyidagi JSON formatida javob ber:
{
  "action": "send_message" | "send_voice" | "clarify",
  "recipient": "qabul qiluvchi (masalan: ustoz, adajon, @username, telefon, yoki ism)",
  "message_text": "Muhammad Ali nomidan yozilgan aniq xabar matni",
  "voice": "uz-UZ-SardorNeural" | "uz-UZ-MadinaNeural",
  "explanation": "Qisqa izoh (o'zbek tilida)"
}
"""


class AIAgent:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.models_to_try = [settings.GEMINI_MODEL, "gemini-flash-latest", "gemini-2.5-pro"]

    async def process_command(self, user_prompt: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Gemini AI orqali foydalanuvchi so'rovini tahlil qilish."""
        prompt_with_context = user_prompt
        if context:
            prompt_with_context = f"Suhbatlar konteksti:\n{context}\n\nFoydalanuvchi buyrug'i: {user_prompt}"

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_with_context}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.3
            }
        }

        # IPv4 ni majburiy qilish Windows/Linux o'rtasidagi DNS va ulanish muammolarini yo'qotadi
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        timeout = aiohttp.ClientTimeout(total=20)

        for model_name in self.models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            try:
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.post(url, json=payload, timeout=timeout) as response:
                        if response.status != 200:
                            err_text = await response.text()
                            logger.warning(f"Gemini API ({model_name}) xatosi ({response.status}): {err_text}")
                            continue

                        data = await response.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            continue

                        raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
                        parsed = json.loads(raw_text)
                        return parsed
            except Exception as e:
                logger.warning(f"Model {model_name} chaqiruvida xatolik: {e}")
                continue

        return {
            "action": "clarify",
            "recipient": "",
            "message_text": "Kechirasiz, sun'iy intellekt serveri bilan bog'lanib bo'lmadi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
            "explanation": "Gemini API unavailable"
        }


ai_agent = AIAgent()
