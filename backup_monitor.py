# backup_monitor.py
import os
import time
import logging
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- KONFIGURASI ---
# Ambil dari environment variable atau tulis langsung di sini
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
# Ganti dengan Chat ID yang Anda dapatkan dari @userinfobot
CHAT_ID = "876081450" 
# Path ke file yang akan dipantau. Pastikan ini benar.
# Jika file berada di folder yang sama, cukup tulis namanya.
FILE_TO_WATCH = "/root/botty/refresh-tokens.json"
# Pastikan path lengkap jika file berada di direktori lain
# Contoh: FILE_TO_WATCH = "/root/xlunli_bot/refresh-tokens.json"

# --- Konfigurasi Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Fungsi untuk Mengirim File ke Telegram ---
def send_backup_to_telegram(file_path):
    """Mengirim file yang ditentukan ke chat Telegram yang dikonfigurasi."""
    if not os.path.exists(file_path):
        logger.error(f"File tidak ditemukan di path: {file_path}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    
    try:
        with open(file_path, 'rb') as f:
            files = {'document': (os.path.basename(file_path), f)}
            data = {'chat_id': CHAT_ID, 'caption': f'Backup otomatis untuk `{os.path.basename(file_path)}`'}
            
            logger.info(f"Mengirim backup {os.path.basename(file_path)} ke Telegram...")
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                logger.info("Backup berhasil dikirim.")
            else:
                logger.error(f"Gagal mengirim backup. Status: {response.status_code}, Respon: {response.text}")

    except Exception as e:
        logger.error(f"Terjadi error saat mengirim file: {e}", exc_info=True)


# --- Kelas Handler untuk Memantau Perubahan File ---
class BackupEventHandler(FileSystemEventHandler):
    """Handler yang akan dipicu saat file dimodifikasi."""
    def on_modified(self, event):
        # Kita hanya peduli jika file yang kita pantau yang berubah
        if not event.is_directory and event.src_path.endswith(FILE_TO_WATCH):
            logger.info(f"Perubahan terdeteksi pada file: {event.src_path}")
            # Tunggu sebentar untuk memastikan file sudah selesai ditulis
            time.sleep(1) 
            send_backup_to_telegram(event.src_path)

# --- Fungsi Utama untuk Menjalankan Pemantau ---
def start_monitoring(path):
    event_handler = BackupEventHandler()
    observer = Observer()
    # Pantau direktori tempat file berada, bukan file itu sendiri
    directory_to_watch = os.path.dirname(os.path.abspath(path))
    observer.schedule(event_handler, directory_to_watch, recursive=False)
    
    logger.info(f"Memulai pemantauan pada direktori: {directory_to_watch} untuk file {os.path.basename(path)}")
    observer.start()
    
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Pemantauan dihentikan.")
    observer.join()


if __name__ == "__main__":
    if not os.path.exists(FILE_TO_WATCH):
        logger.error(f"File awal '{FILE_TO_WATCH}' tidak ditemukan. Pastikan path sudah benar.")
    else:
        start_monitoring(FILE_TO_WATCH)

