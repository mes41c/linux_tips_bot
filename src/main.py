import json
import os
import sys
import random
import datetime
from pathlib import Path
from notifier import TelegramNotifier

# --- AYARLAR ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "tips.json"
STATUS_FILE = BASE_DIR / "data" / "status.json"

# --- YARDIMCI FONKSIYONLAR ---
def load_json(path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
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
    print("DEBUG: Script baslatiliyor (Retry Modu)...")

    # 1. ORTAM DEGISKENLERI
    token = os.getenv("TELEGRAM_TOKEN")
    raw_chat_ids = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not raw_chat_ids:
        print("KRITIK: Token veya Chat ID eksik.")
        sys.exit(1) # Konfigurasyon hatasi varsa fail olsun

    all_target_ids = [x.strip() for x in raw_chat_ids.split(',') if x.strip()]
    
    # 2. DURUM YONETIMI (STATE MANAGEMENT)
    # Bugunun tarihini al (UTC kullanmak action icin daha guvenli)
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    
    status_data = load_json(STATUS_FILE)
    tips_data = load_json(DATA_FILE)

    if not status_data or not tips_data:
        print("KRITIK: Veri dosyalari okunamadi.")
        sys.exit(1)

    # --- YENI GUN KONTROLU ---
    # Eger status dosyasindaki tarih bugun degilse, yeni bir gun baslamistir.
    # Eski gun tamamlanmadiysa bile artik sifirlanir (User'in "ertelesin" istegi).
    if status_data.get("date") != today_str:
        print(f"BILGI: Yeni gun tespit edildi ({today_str}). Gunluk islem baslatiliyor.")
        
        # Yeni bir ipucu sec
        unpublished_pool = [tip for tip in tips_data if not tip.get("is_published", False)]
        
        if not unpublished_pool:
            print("BILGI: Yayinlanacak ipucu kalmadi.")
            sys.exit(0)
            
        selected_tip = random.choice(unpublished_pool)
        
        # Status dosyasini bugun icin sifirla
        status_data = {
            "date": today_str,
            "target_tip_id": selected_tip['id'],
            "pending_ids": all_target_ids, # Herkes beklemede
            "is_completed": False
        }
        save_json(STATUS_FILE, status_data)
    
    # --- GOREV KONTROLU ---
    if status_data["is_completed"]:
        print("BILGI: Bugunun gorevi zaten tamamlanmis. Cikis yapiliyor.")
        sys.exit(0)

    # Hedef ipucunu tips_data icinden bul
    target_tip = next((t for t in tips_data if t["id"] == status_data["target_tip_id"]), None)
    if not target_tip:
        print("HATA: Hedef ipucu veritabaninda bulunamadi.")
        sys.exit(1)

    # 3. GONDERIM DONGUSU (Sadece pending_ids icin)
    pending_list = status_data["pending_ids"]
    print(f"DEBUG: Bekleyen alicilar: {pending_list}")
    
    still_pending = []
    message = format_tip(target_tip)
    success_in_this_run = False

    for uid in pending_list:
        try:
            notifier = TelegramNotifier(token, uid)
            if notifier.send_message(message):
                print(f"BASARILI: {uid}")
                success_in_this_run = True
            else:
                print(f"ULASILAMADI (Retrying later): {uid}")
                still_pending.append(uid)
        except Exception as e:
            print(f"HATA ({uid}): {e}")
            still_pending.append(uid)

    # 4. DURUM GUNCELLEME
    status_data["pending_ids"] = still_pending

    # Eger kimse kalmadiysa gorev tamamlanmistir
    if not still_pending:
        print("SONUC: Tum alicilara ulasildi. Gorev tamamlandi.")
        status_data["is_completed"] = True
        
        # Ana veritabaninda da yayinlandi olarak isaretle
        for tip in tips_data:
            if tip["id"] == target_tip["id"]:
                tip["is_published"] = True
                break
        save_json(DATA_FILE, tips_data)
    else:
        print(f"BILGI: {len(still_pending)} aliciya ulasilamadi. Sonraki saat tekrar denenecek.")
        # Burada sys.exit(1) YAPMIYORUZ. Cünkü bu bir hata degil, surecin parcasidir.
        # GitHub Action "Success" verecek ama islem bitmemis olacak.

    save_json(STATUS_FILE, status_data)

if __name__ == "__main__":
    main()
