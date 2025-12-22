import json
import os
import sys
import random  # <--- YENI: Rastgelelik icin gerekli kutuphane
from pathlib import Path
from notifier import TelegramNotifier

# --- AYARLAR ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "tips.json"

def load_data():
    if not DATA_FILE.exists():
        print(f"Hata: Veri dosyası bulunamadı: {DATA_FILE}")
        sys.exit(1)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def format_tip(tip):
    hashtag = f"#{tip.get('category', 'linux').replace('_', '')}"
    return (
        f"🚀 **Günün Linux İpucu** {hashtag}\n\n"
        f"**{tip['title']}**\n\n"
        f"📝 *Açıklama:*\n{tip['description']}\n\n"
        f"💻 *Komut:*\n"
        f"```bash\n{tip['command']}\n```\n"
        f"🆔 ID: {tip['id']}"
    )

def main():
    print("DEBUG: Script baslatiliyor (Rastgele Mod)...")

    # 1. ORTAM DEGISKENLERINI AL
    token = os.getenv("TELEGRAM_TOKEN")
    raw_chat_ids = os.getenv("TELEGRAM_CHAT_ID")

    # 2. KONTROLLER
    if not token:
        print("HATA: TELEGRAM_TOKEN environment variable bulunamadi!")
        sys.exit(1)
    
    if not raw_chat_ids:
        print("HATA: TELEGRAM_CHAT_ID environment variable bulunamadi!")
        sys.exit(1)

    target_ids = [x.strip() for x in raw_chat_ids.split(',') if x.strip()]

    if not target_ids:
        print("HATA: Gecerli bir Chat ID bulunamadi.")
        sys.exit(1)

    # 3. VERIYI YUKLE
    data = load_data()
    
    # --- DEGISIKLIK BASLANGICI ---
    
    # A) Yayinlanmamis (is_published: false) tum ipuclarini bir havuza at
    unpublished_pool = [tip for tip in data if not tip.get("is_published", False)]
    
    # B) Havuz bos mu kontrol et
    if not unpublished_pool:
        print("BILGI: Yayinlanacak yeni ipucu kalmadi. Hepsi tukendi.")
        sys.exit(0)
    
    # C) Havuzdan RASTGELE bir tane sec
    target_tip = random.choice(unpublished_pool)
    
    # D) Secilen ipucunun orijinal ana listedeki sirasini (index) bul
    # (Kaydederken dogru satiri guncellemek icin bu sart)
    target_index = data.index(target_tip)
    
    print(f"DEBUG: Rastgele secilen ID: {target_tip['id']}")
    
    # --- DEGISIKLIK BITISI ---

    # 4. GONDERIM DONGUSU
    message = format_tip(target_tip)
    success_count = 0

    for uid in target_ids:
        try:
            notifier = TelegramNotifier(token, uid)
            if notifier.send_message(message):
                print(f"BASARILI: {uid}")
                success_count += 1
            else:
                print(f"BASARISIZ: {uid}")
        except Exception as e:
            print(f"HATA ({uid}): {e}")

    # 5. DURUM GUNCELLEME
    if success_count > 0:
        data[target_index]["is_published"] = True
        save_data(data)
        print(f"SONUC: İpucu {target_tip['id']} yayinlandi ve durum guncellendi.")
    else:
        print("KRITIK: Mesaj gonderilemedi. Veritabani guncellenmedi.")
        sys.exit(1)

if __name__ == "__main__":
    main()
