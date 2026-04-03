"""Configuration loader for Listrik Bot."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # Connection mode: "cloud" or "local"
    CONNECTION_MODE = os.getenv("CONNECTION_MODE", "cloud").lower()

    # Tuya Cloud API
    TUYA_API_KEY = os.getenv("TUYA_API_KEY", "")
    TUYA_API_SECRET = os.getenv("TUYA_API_SECRET", "")
    TUYA_API_REGION = os.getenv("TUYA_API_REGION", "us")

    # Tuya Device
    DEVICE_ID = os.getenv("DEVICE_ID", "")
    DEVICE_IP = os.getenv("DEVICE_IP", "")
    LOCAL_KEY = os.getenv("LOCAL_KEY", "")
    DEVICE_VERSION = float(os.getenv("DEVICE_VERSION", "3.4"))

    # Monitoring
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
    LOW_BALANCE_KWH = float(os.getenv("LOW_BALANCE_KWH", "10"))

    # Database
    DB_PATH = os.getenv("DB_PATH", "data/listrik.db")

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        errors = []

        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        if not cls.TELEGRAM_CHAT_ID:
            errors.append("TELEGRAM_CHAT_ID is required")
        if not cls.DEVICE_ID:
            errors.append("DEVICE_ID is required")

        if cls.CONNECTION_MODE == "cloud":
            if not cls.TUYA_API_KEY:
                errors.append("TUYA_API_KEY is required for cloud mode")
            if not cls.TUYA_API_SECRET:
                errors.append("TUYA_API_SECRET is required for cloud mode")
        elif cls.CONNECTION_MODE == "local":
            if not cls.DEVICE_IP:
                errors.append("DEVICE_IP is required for local mode")
            if not cls.LOCAL_KEY:
                errors.append("LOCAL_KEY is required for local mode")
        else:
            errors.append(f"Invalid CONNECTION_MODE: {cls.CONNECTION_MODE}")

        if errors:
            raise ValueError("Configuration errors:\n  - " + "\n  - ".join(errors))
