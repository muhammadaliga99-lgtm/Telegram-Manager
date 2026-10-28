"""
Konfiguratsiya moduli: Barcha muhit o'zgaruvchilari (environment variables)
va tizim xavfsizlik sozlamalari shu yerda boshqariladi.
"""
from typing import Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram Bot Token (@BotFather bergan token)
    TELEGRAM_BOT_TOKEN: str = Field(..., description="Telegram bot API token")

    # Telegram MTProto Userbot API (my.telegram.org)
    TELEGRAM_API_ID: int = Field(..., description="Telegram App API ID")
    TELEGRAM_API_HASH: str = Field(..., description="Telegram App API Hash")
    TELEGRAM_STRING_SESSION: str = Field(..., description="Telethon StringSession (Renderda sqlite faylsiz ishlash uchun)")

    # Xavfsizlik: Botni faqatgina Muhammad Ali ishlata olishi uchun uning Telegram ID'si
    ADMIN_USER_ID: int = Field(6912373539, description="Bot egasining Telegram ID raqami")

    # Google Gemini AI kaliti va model
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key")
    GEMINI_MODEL: str = Field("gemini-3.5-flash", description="Gemini model nomi")

    # Ovozli xabarlar uchun Edge-TTS ovozi
    DEFAULT_VOICE: str = Field("uz-UZ-SardorNeural", description="O'zbekcha erkak ovozi")
    FEMALE_VOICE: str = Field("uz-UZ-MadinaNeural", description="O'zbekcha ayol ovozi")

    # Render HTTP Web server porti
    PORT: int = Field(8080, description="Web server tinglaydigan port")

    # Ma'lum kontaktlarning tezkor taxalluslar (aliases) lug'ati
    KNOWN_ALIASES: Dict[str, str] = {
        "ustoz": "858709040",         # Behruz aka (@behruz_237)
        "ustozim": "858709040",
        "behruz": "858709040",
        "behruz aka": "858709040",
        "adajon": "5550086617",        # Adajon
        "ada": "5550086617",
        "dada": "5550086617",
        "sinfdoshlar": "-1004297560298",      # Sinfdoshlar guruhi
        "sinfdoshlar guruhi": "-1004297560298",
        "8-a": "-1002494199500",              # 8- “A” sinf
        "8-a sinf": "-1002494199500",
        "8 a": "-1002494199500",
        "8 a sinf": "-1002494199500",
        "humoyun": "6329250150",
        "islom": "8477424170",
        "bilol": "8183284050",
        "hojimurod": "6814184279",
        "aziz": "5755701508",
        "abubakr": "8670628080"
    }


settings = Settings()
