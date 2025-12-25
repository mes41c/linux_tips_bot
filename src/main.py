import json
import os
import sys
import random
import datetime
import hashlib  # <--- YENI: Guvenlik icin gerekli
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

def get_hash(text):
    """Verilen metnin SHA256 ozetini dondurur. (Tek Yonlu Sifreleme)"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

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
    print("DEBUG: Script baslatiliyor (Secure Hash Modu)...")

    # 1. ORTAM DEGISKENLERI (Secret'tan Ham Veriyi Al)
    token = os.getenv("TELEGRAM_TOKEN")
    raw_chat_ids = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not raw_chat_ids:
        print("KRITIK: Token veya Chat ID eksik.")
        sys.exit(1)

    # Ham ID listesini olustur (RAM'de tutulur, diske yazilmaz)
    target_ids_list = [x.strip() for x in raw_chat_ids.split(',') if x.strip()]
    
    # 2. DURUM YONETIMI
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    
    status_data = load_json(STATUS_FILE)
    tips_data = load_json(DATA_FILE)

    if not status_data or not tips_data:
        print("KRITIK: Veri dosyalari okunamadi.")
        sys.exit(1)

    # --- YENI GUN KONTROLU ---
    # Eger gun degistiyse status dosyasini sifirla
    if status_data.get("date") != today_str:
        print(f"BILGI: Yeni gun ({today_str}).")
        
        unpublished_pool = [tip for tip in tips_data if not tip.get("is_published", False)]
        
        if not unpublished_pool:
            print("BILGI: Yayinlanacak ipucu kalmadi.")
            sys.exit(0)
            
        selected_tip = random.choice(unpublished_pool)
        
        status_data = {
            "date": today_str,
            "target_tip_id": selected_tip['id'],
            "completed_hashes": [], # <--- ARTIK ID DEGIL HASH TUTUYORUZ
            "is_completed": False
        }
        save_json(STATUS_FILE, status_data)
    
    # --- GOREV KONTROLU ---
    if status_data["is_completed"]:
        print("BILGI: Bugunun gorevi tamamlanmis.")
        sys.exit(0)

    target_tip = next((t for t in tips_data if t["id"] == status_data["target_tip_id"]), None)
    if not target_tip:
        print("HATA: Hedef ipucu bulunamadi.")
        sys.exit(1)

    # 3. GONDERIM DONGUSU
    # Ham ID'leri dolasiyoruz, ama kontrolu Hash uzerinden yapiyoruz
    message = format_tip(target_tip)
    completed_hashes = status_data.get("completed_hashes", [])
    any_failure = False

    for uid in target_ids_list:
        uid_hash = get_hash(uid) # ID'yi hashle
        
        # Eger bu Hash zaten tamamlananlar listesindeyse atla
        if uid_hash in completed_hashes:
            print(f"ATLANDI (Zaten gonderildi): {uid_hash[:8]}...")
            continue

        try:
            notifier = TelegramNotifier(token, uid)
            if notifier.send_message(message):
                print(f"BASARILI (Hash): {uid_hash[:8]}...")
                completed_hashes.append(uid_hash)
            else:
                print(f"ULASILAMADI: {uid_hash[:8]}...")
                any_failure = True
        except Exception as e:
            print(f"HATA: {e}")
            any_failure = True

    # 4. DURUM GUNCELLEME
    status_data["completed_hashes"] = completed_hashes

    # Eger hicbir hata yoksa ve tum hedefler tamamlandiysa
    if not any_failure and len(completed_hashes) == len(target_ids_list):
        print("SONUC: Tum hedeflere ulasildi.")
        status_data["is_completed"] = True
        
        for tip in tips_data:
            if tip["id"] == target_tip["id"]:
                tip["is_published"] = True
                break
        save_json(DATA_FILE, tips_data)
    else:
        print("BILGI: Bazi hedeflere ulasilamadi, sonra tekrar denenecek.")

    save_json(STATUS_FILE, status_data)

if __name__ == "__main__":
    main()
