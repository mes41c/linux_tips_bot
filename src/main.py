import json
import os
import sys
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
    print("DEBUG: Script baslatiliyor...")

    # 1. ORTAM DEGISKENLERINI AL
    # GitHub Secrets'tan gelen verileri aliyoruz
    token = os.getenv("TELEGRAM_TOKEN")
    raw_chat_ids = os.getenv("TELEGRAM_CHAT_ID")

    # 2. KONTROLLER
    if not token:
        print("HATA: TELEGRAM_TOKEN environment variable bulunamadi!")
        sys.exit(1)
    
    if not raw_chat_ids:
        print("HATA: TELEGRAM_CHAT_ID environment variable bulunamadi!")
        sys.exit(1)

    # Chat ID'leri virgulden ayirip listeye ceviriyoruz
    # Ornek: "123, 456" -> ['123', '456']
    target_ids = [x.strip() for x in raw_chat_ids.split(',') if x.strip()]

    if not target_ids:
        print("HATA: Gecerli bir Chat ID bulunamadi. Format: ID1,ID2")
        sys.exit(1)

    print(f"DEBUG: Toplam {len(target_ids)} aliciya gonderim yapilacak.")

    # 3. VERIYI YUKLE
    data = load_data()
    target_tip = None
    target_index = -1

    # Yayinlanmamis ipucunu bul
    for index, tip in enumerate(data):
        if not tip.get("is_published", False):
            target_tip = tip
            target_index = index
            break
    
    if not target_tip:
        print("BILGI: Yayinlanacak yeni ipucu kalmadi.")
        sys.exit(0)

    # 4. GONDERIM DONGUSU
    message = format_tip(target_tip)
    success_count = 0

    for uid in target_ids:
        try:
            print(f"DEBUG: {uid} ID'sine gonderiliyor...")
            # Burada 'CHAT_ID' degil, dongudeki 'uid' degiskenini kullaniyoruz
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
        print(f"SONUC: İpucu {target_tip['id']} yayinlandi. Veritabani guncellendi.")
    else:
        print("KRITIK: Hicbir aliciya mesaj gonderilemedi. Veritabani guncellenmedi.")
        sys.exit(1)

if __name__ == "__main__":
    main()