import os
import requests
import time
import logging

# Loglama konfigürasyonu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        if not token or not chat_id:
            raise ValueError("Telegram token veya Chat ID eksik.")
        self.base_url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send_message(self, message: str, retries: int = 3) -> bool:
        """
        Mesajı Telegram'a gönderir. Ağ hatası durumunda 'retries' kadar tekrar dener.
        """
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown", # Kod blokları için gerekli
            "disable_web_page_preview": True
        }

        for attempt in range(retries):
            try:
                response = requests.post(self.base_url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info("Mesaj başarıyla gönderildi.")
                return True
            except requests.exceptions.RequestException as e:
                logger.warning(f"Gönderim hatası (Deneme {attempt + 1}/{retries}): {e}")
                time.sleep(2) # Backoff stratejisi
        
        logger.error("Mesaj gönderimi tamamen başarısız oldu.")
        return False