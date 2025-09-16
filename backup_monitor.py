# backup_monitor.py
import os
import time
import logging
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- KONFIGURASI ---
# Pastikan token ini masih aktif dan benar
TELEGRAM_BOT_TOKEN = "8486193618:AAHf-bNLvZG_iqtnGq79TS4Q13bRMXdxJEU"
# Pastikan ini adalah ID numerik Anda dari @userinfobot
CHAT_ID = "876081450" 
# Pastikan path ini 100% benar
FILE_TO_WATCH = "/root/botty/refresh-tokens.json"

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
            caption_text = f"Backup otomatis untuk `{os.path.basename(file_path)}`"
            data = {'chat_id': CHAT_ID, 'caption': caption_text}
            
            logger.info(f"Mengirim backup {os.path.basename(file_path)} ke Telegram...")
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                logger.info("Backup berhasil dikirim.")
            else:
                logger.error(f"Gagal mengirim backup. Status: {response.status_code}, Respon: {response.text}")

    except Exception as e:
        logger.error(f"Terjadi error saat mengirim file: {e}", exc_info=True)


# --- Kelas Handler untuk Memantau Perubahan File (Versi Diperbaiki) ---
class BackupEventHandler(FileSystemEventHandler):
    """Handler yang akan dipicu saat file dimodifikasi, dibuat, atau dipindahkan."""

    def _send_if_relevant(self, path):
        """Fungsi internal untuk memeriksa path dan mengirim file."""
        # Hanya proses jika path sesuai dengan file yang kita pantau
        if path == FILE_TO_WATCH:
            logger.info(f"Perubahan relevan terdeteksi pada: {path}")
            # Tunggu sebentar untuk memastikan file sudah selesai ditulis
            time.sleep(1)
            send_backup_to_telegram(path)

    def on_modified(self, event):
        # Dipicu saat file yang sudah ada diubah isinya
        if not event.is_directory:
            self._send_if_relevant(event.src_path)

    def on_created(self, event):
        # Dipicu saat file baru dibuat (berguna untuk save-atomic)
        if not event.is_directory:
            self._send_if_relevant(event.src_path)

    def on_moved(self, event):
        # Dipicu saat file di-rename. Kita cek tujuan akhirnya.
        if not event.is_directory:
            self._send_if_relevant(event.dest_path)

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
        logger.error(f"File awal '{FILE_TO_WATCH}' tidak ditemukan. Pastikan path sudah benar dan file sudah ada.")
    else:
        # Lakukan pengiriman backup pertama kali saat skrip dijalankan
        logger.info("Mengirim backup awal saat skrip dimulai...")
        send_backup_to_telegram(FILE_TO_WATCH)
        # Mulai memantau perubahan
        start_monitoring(FILE_TO_WATCH)
