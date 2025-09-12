# bottem.txt
# Modifikasi untuk fitur Tembak Paket Aniv dan perbaikan pembayaran

import os
import json
import logging
import asyncio
import traceback
from io import BytesIO
from dotenv import load_dotenv

# Muat variabel lingkungan
load_dotenv()

# Import library Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Import library untuk membuat QR Code
import qrcode

# Import modul-modul dari project MyXL
# Kita akan menonaktifkan verifikasi SSL untuk menghindari error
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

original_request = requests.request
def patched_request(method, url, **kwargs):
    kwargs['verify'] = False  # Nonaktifkan verifikasi SSL
    return original_request(method, url, **kwargs)
requests.request = patched_request

# Sekarang import modul MyXL
# Pastikan path dan nama file sesuai dengan struktur proyek Anda
from api_request import get_otp, submit_otp, get_profile, get_balance, get_package, get_family
from auth_helper import AuthInstance
# Impor fungsi kriptografi yang diperlukan
# Anda perlu memastikan file crypto_helper.py ada dan memiliki fungsi-fungsi ini
# Karena file auth.txt kosong, saya asumsikan implementasinya ada di sini
# from crypto_helper import load_ax_fp, decrypt_xdata, encryptsign_xdata, java_like_timestamp, get_x_signature_payment # Sesuaikan path jika perlu
# Untuk sementara, biarkan import ini sebagai placeholder, Anda perlu memperbaikinya
# Impor sementara untuk fungsi kriptografi - GANTILAH DENGAN IMPORT YANG BENAR DARI FILE ASLI ANDA
# Placeholder untuk fungsi kriptografi - GANTILAH DENGAN IMPLEMENTASI ASLI
def decrypt_xdata(*args, **kwargs):
    # Implementasi dummy untuk menghindari error, gantilah dengan yang asli
    raise NotImplementedError("decrypt_xdata belum diimplementasikan. Periksa file crypto_helper.py Anda.")

def encryptsign_xdata(*args, **kwargs):
    # Implementasi dummy untuk menghindari error, gantilah dengan yang asli
    raise NotImplementedError("encryptsign_xdata belum diimplementasikan. Periksa file crypto_helper.py Anda.")

def get_x_signature_payment(*args, **kwargs):
    # Implementasi dummy untuk menghindari error, gantilah dengan yang asli
    raise NotImplementedError("get_x_signature_payment belum diimplementasikan. Periksa file crypto_helper.py Anda.")

def java_like_timestamp(*args, **kwargs):
    # Implementasi dummy untuk menghindari error, gantilah dengan yang asli
    import time
    return str(int(time.time() * 1000))

# Placeholder untuk konstanta - GANTILAH DENGAN NILAI YANG BENAR DARI .env ATAU FILE KONFIGURASI ANDA
BASE_API_URL = os.getenv("BASE_API_URL", "https://my.xl.co.id") # Default jika tidak ditemukan
UA = os.getenv("UA", "Mozilla/5.0") # Default jika tidak ditemukan
API_KEY = os.getenv("API_KEY", "") # Default jika tidak ditemukan

from my_package import fetch_my_packages
from paket_custom_family import get_packages_by_family
from paket_xut import get_package_xut
# from purchase_api import get_payment_methods, settlement_qris, get_qris_code, settlement_multipayment
# Kita akan membuat pengganti settlement_qris sendiri
from util import display_html, ensure_api_key

# === KONFIGURASI ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set")

# Inisialisasi AuthInstance
try:
    AuthInstance.api_key = ensure_api_key()
    # load_ax_fp() # Jika fungsi ini ada dan diperlukan
    logger.info("Auth initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Auth: {e}")
    raise

# === FUNGSI PEMBANTU ===
def format_benefit(benefit):
    """Format benefit menjadi string yang mudah dibaca"""
    name = benefit['name']
    total = benefit['total']
    if "Call" in name and total > 0:
        minutes = total / 60
        return f"• {name}: {minutes:.0f} menit"
    elif total > 0:
        # Format kuota
        if total >= 1_000_000_000: # GB
            value = total / (1024 ** 3)
            unit = "GB"
        elif total >= 1_000_000: # MB
            value = total / (1024 ** 2)
            unit = "MB"
        elif total >= 1_000: # KB
            value = total / 1024
            unit = "KB"
        else:
            value = total
            unit = "" # Bit/Unit lain
        if unit:
            return f"• {name}: {value:.2f} {unit}"
        else:
            return f"• {name}: {value}"
    else:
        return f"• {name}: {total}"

# === PENGGANTI settlement_qris TANPA INPUT ===
# Salinan logika dari purchase.txt tetapi tanpa input() dan dengan amount_int = price
import json
import uuid
import time
import requests
from datetime import datetime, timezone
# Pastikan import ini sesuai dengan struktur proyek Anda
# Placeholder untuk send_api_request - GANTILAH DENGAN IMPORT YANG BENAR
# from engsel import send_api_request # Jika engsel.py ada di direktori yang sama

async def settlement_qris_no_input(
    api_key: str,
    tokens: dict,
    token_payment: str,
    ts_to_sign: int,
    payment_target: str, # package_code
    price: int,          # confirmed_price (akan digunakan sebagai amount_int)
    item_name: str = "",
):
    """
    Melakukan settlement QRIS tanpa meminta input manual untuk harga.
    Meniru logika dari purchase.txt::settlement_qris tetapi menggunakan `price` langsung
    sebagai `amount_int` jika tidak ada input manual (karena tidak ada input di bot).
    Ini mensimulasikan perilaku saat pengguna di Termux menekan Enter pada prompt input.
    """
    try:
        # --- LOGIKA YANG DISALIN DARI purchase.txt ---
        # TIDAK ADA pemanggilan input() di sini.
        
        # Logika penentuan amount_int seperti di purchase.txt jika input kosong
        # Kita asumsikan tidak ada input manual, jadi amount_int = price
        # Ini mensimulasikan apa yang terjadi di Termux jika pengguna hanya menekan Enter.
        amount_int = price # <-- INI PERUBAHAN UTAMA: Gunakan price langsung

        # --- SISANYA ADALAH SALINAN LANGSUNG DARI settlement_qris ---
        # Settlement request
        path = "payments/api/v8/settlement-multipayment/qris"
        settlement_payload = {
            "akrab": {"akrab_members": [], "akrab_parent_alias": "", "members": []},
            "can_trigger_rating": False,
            "total_discount": 0,
            "coupon": "",
            "payment_for": "BUY_PACKAGE",
            "topup_number": "",
            "is_enterprise": False,
            "autobuy": {"is_using_autobuy": False, "activated_autobuy_code": "", "autobuy_threshold_setting": {"label": "", "type": "", "value": 0}},
            "access_token": tokens.get("access_token", ""), # Gunakan .get untuk menghindari KeyError
            "is_myxl_wallet": False,
            "additional_data": {
                "original_price": price,
                "is_spend_limit_temporary": False,
                "migration_type": "",
                "spend_limit_amount": 0,
                "is_spend_limit": False,
                "tax": 0,
                "benefit_type": "",
                "quota_bonus": 0,
                "cashtag": "",
                "is_family_plan": False,
                "combo_details": [],
                "is_switch_plan": False,
                "discount_recurring": 0,
                "has_bonus": False,
                "discount_promo": 0
            },
            "total_amount": amount_int, # <-- Gunakan amount_int yang sudah ditentukan
            "total_fee": 0,
            "is_use_point": False,
            "lang": "en",
            "items": [{
                "item_code": payment_target,
                "product_type": "",
                "item_price": price,
                "item_name": item_name,
                "tax": 0
            }],
            "verification_token": token_payment,
            "payment_method": "QRIS",
            "timestamp": int(time.time()) # Akan ditimpa oleh ts_to_sign
        }

        # Enkripsi payload
        # Karena fungsi kriptografi adalah placeholder, ini akan gagal.
        # Anda perlu memperbaiki import dan implementasi decrypt_xdata, encryptsign_xdata di atas.
        encrypted_payload = encryptsign_xdata(
            api_key=api_key,
            method="POST",
            path=path,
            id_token=tokens.get("id_token", ""), # Gunakan .get untuk menghindari KeyError
            payload=settlement_payload
        )
        
        xtime = int(encrypted_payload["encrypted_body"]["xtime"])
        sig_time_sec = (xtime // 1000)
        x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
        # Timpa timestamp dengan ts_to_sign yang diberikan
        settlement_payload["timestamp"] = ts_to_sign 
        
        body = encrypted_payload["encrypted_body"]
        x_sig = get_x_signature_payment(
            api_key,
            tokens.get("access_token", ""), # Gunakan .get untuk menghindari KeyError
            ts_to_sign, # <-- Gunakan ts_to_sign
            payment_target,
            token_payment,
            "QRIS"
        )
        
        headers = {
            "host": BASE_API_URL.replace("https://", ""),
            "content-type": "application/json; charset=utf-8",
            "user-agent": UA,
            "x-api-key": API_KEY,
            "authorization": f"Bearer {tokens.get('id_token', '')}", # Gunakan .get untuk menghindari KeyError
            "x-hv": "v3",
            "x-signature-time": str(sig_time_sec),
            "x-signature": x_sig,
            "x-request-id": str(uuid.uuid4()),
            "x-request-at": java_like_timestamp(x_requested_at),
            "x-version-app": "8.6.0",
        }
        
        url = f"{BASE_API_URL}/{path}"
        
        logger.info("Sending settlement request (no input)...")
        # Kirim request
        # Catatan: Untuk menjaga konsistensi async/await di bot, idealnya menggunakan aiohttp
        # Tapi untuk kesederhanaan dan kompatibilitas, kita tetap gunakan requests.
        # Jika terjadi blocking, pertimbangkan untuk menjalankan ini dalam executor.
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
        
        # Dekripsi response
        # Karena fungsi kriptografi adalah placeholder, ini akan gagal.
        # Anda perlu memperbaiki import dan implementasi decrypt_xdata di atas.
        decrypted_body = decrypt_xdata(api_key, json.loads(resp.text))
        
        if decrypted_body.get("status") != "SUCCESS": # Gunakan .get untuk menghindari KeyError
            logger.error(f"Failed to initiate settlement (no input). Error: {decrypted_body}")
            # Kembalikan seluruh response error untuk debugging lebih lanjut di pemanggil
            return decrypted_body 
            
        transaction_id = decrypted_body["data"]["transaction_code"]
        logger.info(f"Settlement initiated successfully. Transaction ID: {transaction_id}")
        return transaction_id
        
    except Exception as e:
        logger.error(f"[settlement_qris_no_input] Error: {e}", exc_info=True)
        # Kembalikan None atau objek error untuk menunjukkan kegagalan
        return None
# --- AKHIR PENGGANTI ---

# === HANDLER UTAMA ===
async def buy_xut_vidio_direct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Langsung tampilkan detail paket XUT Unlimited Turbo Vidio (nomor 11)"""
    query = update.callback_query
    await query.answer()
    try:
        # 1. Pastikan pengguna sudah login
        tokens = AuthInstance.get_active_tokens()
        if not tokens:
            await query.message.edit_text("❌ Tidak ada akun aktif. Silakan login terlebih dahulu.")
            return
        await query.message.edit_text("🔄 Mengambil detail paket XUT Vidio...")
        # 2. Dapatkan API key
        api_key = AuthInstance.api_key
        # 3. Panggil fungsi get_package_xut() untuk mendapatkan daftar paket
        packages = get_package_xut()
        if not packages:
            await query.message.edit_text("❌ Gagal mengambil data paket XUT.")
            return
        # 4. Cari paket dengan nomor 11
        target_package = None
        for pkg in packages:
            if pkg.get('number') == 11:  # Cari paket nomor 11
                target_package = pkg
                break
        if not target_package:
            await query.message.edit_text("❌ Paket XUT Unlimited Turbo Vidio (nomor 11) tidak ditemukan.")
            return
        # 5. Ambil detail paket lengkap untuk mendapatkan token_confirmation
        package_code = target_package['code']
        package_details = get_package(api_key, tokens, package_code)
        if not package_details:
            await query.message.edit_text("❌ Gagal mengambil detail paket XUT Vidio.")
            return
        # 6. Ekstrak informasi yang dibutuhkan
        package_name = target_package['name']
        package_price = target_package['price']
        token_confirmation = package_details.get("token_confirmation", "") # Gunakan .get
        # 7. Simpan informasi paket di context.user_data dengan KEY YANG SESUAI
        # Gunakan 'selected_package' agar bisa dibaca oleh buy_xut_with_qris
        context.user_data['selected_package'] = {
            'code': package_code,
            'name': package_name,
            'price': package_price,
            'token_confirmation': token_confirmation,
            # Tambahkan field lain jika diperlukan
            'validity': package_details.get("package_option", {}).get("validity", ""),
            'benefits': package_details.get("package_option", {}).get("benefits", []),
            'tnc': package_details.get("package_option", {}).get("tnc", "")
        }
        # 8. Tampilkan detail paket dan opsi pembayaran
        message = (
            f"📦 *Detail Paket XUT*\n"
            f"🏷 *Nama:* {package_name}\n"
            f"💰 *Harga:* Rp {package_price}\n"
            "Pilih metode pembayaran:"
        )
        keyboard = [
            [InlineKeyboardButton("💳 Beli dengan Pulsa", callback_data='buy_xut_pulsa')],
            [InlineKeyboardButton("💳 Beli dengan E-Wallet", callback_data='buy_xut_ewallet')],
            [InlineKeyboardButton("📲 Beli dengan QRIS", callback_data='buy_xut_qris')], # Pastikan callback_data ini
            [InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error fetching XUT Vidio package: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan saat mengambil detail paket XUT Vidio.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /start"""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan menu utama"""
    # Periksa akun aktif
    active_user = AuthInstance.get_active_user()
    main_buttons = [
        InlineKeyboardButton("1. Login", callback_data='login_menu'),
        InlineKeyboardButton("2. Ganti Akun", callback_data='switch_account_menu'),
        InlineKeyboardButton("3. Lihat Paket Saya", callback_data='view_packages'),
        InlineKeyboardButton(" XLUNLI", callback_data='buy_xut_vidio_direct'), # Langsung ke Vidio
        InlineKeyboardButton("5. Family Code", callback_data='buy_family'),
        InlineKeyboardButton("🎯 Tembak Paket Aniv", callback_data='buy_aniv_direct'), # Tambahkan tombol Aniv
    ]
    keyboard = [main_buttons[i:i + 2] for i in range(0, len(main_buttons), 2)]
    # Tambahkan tombol "Akun Saya" hanya jika sudah login
    if active_user:
        keyboard.append([InlineKeyboardButton("💳 Akun Saya", callback_data='account_info')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_message = " *TEMBAK PAKET XLUNLI*\n"
    # Tampilkan informasi akun aktif jika ada
    if active_user:
        welcome_message += f" *Nomor Aktif:* `{active_user['number']}`\n"
    else:
        welcome_message += "🔐 *Status:* Belum login\n"
    welcome_message += "Silakan pilih menu di bawah ini:"
    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# === LOGIN & GANTI AKUN (MODIFIKASI TOTAL) ===

# Fungsi untuk memulai proses login
async def initiate_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses login - meminta nomor HP"""
    query = update.callback_query
    if query:
        await query.answer()
    message = (
        "📱 *Login ke MyXL*\n"
        "Silakan kirimkan nomor telepon Anda yang terdaftar di MyXL.\n"
        "Format: `628XXXXXXXXXX` (awali dengan 62)\n"
        "Contoh: `6281234567890`"
    )
    # Simpan state bahwa user sedang menunggu input nomor untuk login
    context.user_data['state'] = 'waiting_phone_number_login'
    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Untuk MessageHandler
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

# Fungsi untuk memulai proses ganti akun
async def initiate_switch_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses ganti akun - meminta nomor HP"""
    query = update.callback_query
    if query:
        await query.answer()
    message = (
        "🔄 *Ganti Akun*\n"
        "Silakan kirimkan nomor telepon yang ingin diaktifkan.\n"
        "Format: `628XXXXXXXXXX` (awali dengan 62)\n"
        "Contoh: `6281234567890`"
    )
    # Simpan state bahwa user sedang menunggu input nomor untuk ganti akun
    context.user_data['state'] = 'waiting_phone_number_switch'
    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Untuk MessageHandler
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

# Fungsi utama yang menangani input nomor telepon
async def handle_phone_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani input nomor telepon untuk login atau ganti akun"""
    state = context.user_data.get('state')
    if state not in ['waiting_phone_number_login', 'waiting_phone_number_switch']:
        return # Bukan saatnya menerima nomor

    phone_number = update.message.text.strip()
    
    # --- VALIDASI NOMOR (HANYA 628) ---
    # Validasi format nomor
    if not phone_number.startswith("628") or not phone_number[1:].isdigit() or len(phone_number) < 10 or len(phone_number) > 15:
        await update.message.reply_text(
            "❌ Nomor telepon tidak valid.\n"
            "Pastikan formatnya adalah `628XXXXXXXXXX` (awali dengan 62).\n"
            "Contoh: `6281234567890`\n"
            "Silakan kirimkan nomor yang benar:"
        )
        return
    # --- AKHIR VALIDASI ---

    # Muat token terbaru
    AuthInstance.load_tokens() 
    user_exists = any(str(user['number']) == phone_number for user in AuthInstance.refresh_tokens)

    if state == 'waiting_phone_number_login':
        if user_exists:
            # Jika sudah ada, langsung aktifkan
            success = AuthInstance.set_active_user(int(phone_number))
            if success:
                await update.message.reply_text(f"✅ Akun `{phone_number}` sudah ada dan berhasil diaktifkan!", parse_mode='Markdown')
                await asyncio.sleep(1)
                await show_main_menu(update, context)
                return # TAMBAHKAN return DI SINI
            else:
                 await update.message.reply_text(
                    f"❌ Gagal mengaktifkan akun `{phone_number}`. Token mungkin sudah kadaluarsa.\n"
                    "Silakan login ulang untuk akun ini.",
                    parse_mode='Markdown'
                )
                # Reset state dan mulai OTP flow
                context.user_data['temp_phone'] = phone_number
                context.user_data['state'] = 'waiting_otp'
                await request_and_send_otp(update, phone_number)
                return # TAMBAHKAN return DI SINI
        else:
            # Jika belum ada, minta OTP
            context.user_data['temp_phone'] = phone_number
            context.user_data['state'] = 'waiting_otp'
            await request_and_send_otp(update, phone_number)
            return # TAMBAHKAN return DI SINI

    elif state == 'waiting_phone_number_switch':
        if user_exists:
            # Jika ada, langsung aktifkan
            success = AuthInstance.set_active_user(int(phone_number))
            if success:
                await update.message.reply_text(f"✅ Berhasil beralih ke akun `{phone_number}`.", parse_mode='Markdown')
                await asyncio.sleep(1)
                await show_main_menu(update, context)
                return # TAMBAHKAN return DI SINI
            else:
                 await update.message.reply_text(
                    f"❌ Gagal mengaktifkan akun `{phone_number}`. Token mungkin sudah kadaluarsa.\n"
                    "Silakan login ulang untuk akun ini.",
                    parse_mode='Markdown'
                )
                 # Reset state dan mulai OTP flow
                context.user_data['temp_phone'] = phone_number
                context.user_data['state'] = 'waiting_otp'
                await request_and_send_otp(update, phone_number)
                return # TAMBAHKAN return DI SINI
        else:
            # Jika tidak ada, minta OTP untuk login akun baru ini
            context.user_data['temp_phone'] = phone_number
            context.user_data['state'] = 'waiting_otp'
            await request_and_send_otp(update, phone_number)
            return # TAMBAHKAN return DI SINI

# Fungsi bantu untuk meminta dan mengirim OTP
async def request_and_send_otp(update: Update, phone_number: str) -> None:
    """Meminta OTP dan mengirimkannya ke pengguna"""
    await update.message.reply_text("🔄 Mengirimkan permintaan OTP...")
    try:
        subscriber_id = get_otp(phone_number)
        if not subscriber_id:
            await update.message.reply_text("❌ Gagal mengirim OTP.")
            return
        await update.message.reply_text(
            f"✅ OTP telah dikirim ke nomor {phone_number}.\n"
            "Silakan kirimkan kode OTP 6 digit yang Anda terima:"
        )
    except Exception as e:
        logger.error(f"Error requesting OTP for {phone_number}: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan saat meminta OTP. Silakan coba lagi.")

# Handler OTP tetap sama, hanya perlu memastikan state-nya benar
async def handle_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani input OTP"""
    if context.user_data.get('state') != 'waiting_otp':
        return # Bukan saatnya menerima OTP
    otp = update.message.text.strip()
    # Validasi format OTP
    if not otp.isdigit() or len(otp) != 6:
        await update.message.reply_text(
            "❌ Kode OTP tidak valid.\n"
            "Pastikan OTP terdiri dari 6 digit angka.\n"
            "Silakan kirimkan OTP yang benar:"
        )
        return
    phone_number = context.user_data.get('temp_phone')
    if not phone_number:
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan mulai proses login dari awal.")
        context.user_data.clear() # Reset state
        return
    await update.message.reply_text("🔄 Memverifikasi OTP...")
    try:
        # Submit OTP
        tokens = submit_otp(AuthInstance.api_key, phone_number, otp)
        if not tokens:
            await update.message.reply_text("❌ OTP salah atau telah kedaluwarsa. Silakan coba lagi.")
            context.user_data['state'] = 'waiting_phone_number_login' # Kembali ke input nomor login
            return
        # Simpan token
        AuthInstance.add_refresh_token(int(phone_number), tokens["refresh_token"])
        AuthInstance.set_active_user(int(phone_number))
        # Reset state
        context.user_data.clear()
        await update.message.reply_text(
            "✅ Login berhasil!\n"
            "Anda sekarang dapat menggunakan semua fitur bot."
        )
        # Tampilkan menu utama
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Error submitting OTP for {phone_number}: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan saat memverifikasi OTP. Silakan coba lagi.")
        
# === LIHAT PAKET SAYA ===
async def view_packages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View user's packages"""
    query = update.callback_query
    await query.answer()
    try:
        tokens = AuthInstance.get_active_tokens()
        if not tokens:
            await query.message.edit_text("❌ Tidak ada akun aktif. Silakan login terlebih dahulu.")
            return
        await query.message.edit_text("🔄 Mengambil daftar paket Anda...")
        api_key = AuthInstance.api_key
        id_token = tokens.get("id_token")
        # Gunakan fungsi send_api_request yang diimpor dari api_request.py
        # Placeholder untuk send_api_request - GANTILAH DENGAN IMPORT YANG BENAR
        # from api_request import send_api_request  # Tambahkan ini jika belum ada di import
        # Karena file engsel.txt kosong, kita tidak bisa menggunakan send_api_request
        # Anda perlu memastikan implementasi send_api_request ada.
        # Untuk sementara, kita beri pesan error.
        await query.message.edit_text("❌ Fitur Lihat Paket Saya belum sepenuhnya dikonfigurasi. Periksa implementasi API request.")
        # Contoh logika jika send_api_request ada:
        """
        path = "api/v8/packages/quota-details"
        payload = {
            "is_enterprise": False,
            "lang": "en",
            "family_member_id": ""
        }
        res = send_api_request(api_key, path, payload, id_token, "POST")
        if res.get("status") != "SUCCESS":
            await query.message.edit_text("❌ Gagal mengambil data paket.")
            return
        quotas = res["data"]["quotas"]
        if not quotas:
            await query.message.edit_text("📭 Anda tidak memiliki paket aktif.")
            return
        message = "*📦 Paket Saya:*\n"
        for i, quota in enumerate(quotas, 1):
            quota_code = quota["quota_code"]
            name = quota["name"]
            group_code = quota["group_code"]
            # Get package details
            # Kita juga perlu mengimpor get_package jika belum diimpor
            # from api_request import get_package  # Tambahkan ini jika belum ada di import
            package_details = get_package(api_key, tokens, quota_code)
            family_code = "N/A"
            if package_details:
                family_code = package_details["package_family"]["package_family_code"]
            message += (
                f"📦 *Paket {i}*\n"
                f"   Nama: {name}\n"
                f"   Kode Kuota: `{quota_code}`\n"
                f"   Kode Family: `{family_code}`\n"
                f"   Kode Grup: `{group_code}`\n"
            )
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        """
    except Exception as e:
        logger.error(f"Error viewing packages: {e}")
        await query.message.edit_text("❌ Terjadi kesalahan saat mengambil data paket.")

# === PEMBELIAN PAKET XUT ===
async def buy_xut_packages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display XUT packages"""
    query = update.callback_query
    await query.answer()
    try:
        tokens = AuthInstance.get_active_tokens()
        if not tokens:
            await query.message.edit_text("❌ Tidak ada akun aktif. Silakan login terlebih dahulu.")
            return
        await query.message.edit_text("🔄 Mengambil daftar paket XUT...")
        packages = get_package_xut()
        if not packages:
            await query.message.edit_text("❌ Gagal mengambil data paket XUT.")
            return
        # Simpan daftar paket di context
        context.user_data['xut_packages'] = packages
        message = "*🛒 Paket XUT (Unli Turbo)*\n"
        keyboard = []
        for index, pkg in enumerate(packages):
            message += f"{pkg['number']}. {pkg['name']} - Rp {pkg['price']}\n"
            keyboard.append([InlineKeyboardButton(
                f"{pkg['number']}. {pkg['name']} (Rp {pkg['price']})",
                callback_data=f'xut_select_{index}'  # Gunakan index yang pendek
            )])
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error fetching XUT packages: {e}")
        await query.message.edit_text("❌ Terjadi kesalahan saat mengambil data paket XUT.")

async def show_xut_package_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan detail paket XUT yang dipilih"""
    query = update.callback_query
    await query.answer()
    try:
        # Parse index dari callback_data
        _, _, index_str = query.data.split('_')
        index = int(index_str)
        packages = context.user_data.get('xut_packages', [])
        if not packages or index >= len(packages):
            await query.message.edit_text("❌ Paket tidak ditemukan.")
            return
        package_info = packages[index]
        package_code = package_info['code']
        # Ambil detail paket
        await query.message.edit_text("🔄 Mengambil detail paket...")
        tokens = AuthInstance.get_active_tokens()
        api_key = AuthInstance.api_key
        package_details = get_package(api_key, tokens, package_code)
        if not package_details:
            await query.message.edit_text("❌ Gagal mengambil detail paket.")
            return
        # Ekstrak informasi
        name1 = package_details.get("package_family", {}).get("name", "")
        name2 = package_details.get("package_detail_variant", {}).get("name", "")
        name3 = package_details.get("package_option", {}).get("name", "")
        package_name = f"{name1} {name2} {name3}".strip()
        price = package_details["package_option"]["price"]
        validity = package_details["package_option"]["validity"]
        tnc = display_html(package_details["package_option"]["tnc"])
        token_confirmation = package_details["token_confirmation"]
        benefits = package_details["package_option"]["benefits"]
        # Simpan informasi paket untuk pembelian
        context.user_data['selected_package'] = {
            'code': package_code,
            'name': package_name,
            'price': price,
            'validity': validity,
            'tnc': tnc,
            'token_confirmation': token_confirmation,
            'benefits': benefits
        }
        # Format pesan detail
        benefits_text = "\n".join([format_benefit(b) for b in benefits]) if benefits else "Tidak ada informasi benefit."
        message = (
            f"📦 *Detail Paket XUT*\n"
            f"🏷 *Nama:* {package_name}\n"
            f"💰 *Harga:* Rp {price}\n"
            f"📅 *Masa Aktif:* {validity} hari\n"
            f"🔷 *Benefits:*\n{benefits_text}\n"
            f"📝 *Syarat & Ketentuan:*\n{tnc[:300]}..." # Batasi panjang T&C
        )
        keyboard = [
            [InlineKeyboardButton("💳 Beli dengan Pulsa", callback_data='buy_xut_pulsa')],
            [InlineKeyboardButton("💳 Beli dengan E-Wallet", callback_data='buy_xut_ewallet')],
            [InlineKeyboardButton("📲 Beli dengan QRIS", callback_data='buy_xut_qris')],
            [InlineKeyboardButton("🔙 Kembali", callback_data='buy_xut')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    except (ValueError, IndexError):
        await query.message.edit_text("❌ Data paket tidak valid.")
    except Exception as e:
        logger.error(f"Error showing XUT package details: {e}")
        await query.message.edit_text("❌ Terjadi kesalahan saat menampilkan detail paket.")

async def buy_xut_with_pulsa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pembelian paket XUT dengan Pulsa"""
    query = update.callback_query
    await query.answer()
    package_info = context.user_data.get('selected_package')
    if not package_info:
        await query.message.edit_text("❌ Informasi paket tidak ditemukan. Silakan pilih paket kembali.")
        return
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        await query.message.edit_text("❌ Anda belum login. Silakan login terlebih dahulu.")
        return
    api_key = AuthInstance.api_key
    package_code = package_info['code']
    await query.message.edit_text("🔄 Memproses pembelian dengan Pulsa...")
    try:
        # Panggil fungsi pembelian dari api_request.py
        # Placeholder untuk purchase_package - GANTILAH DENGAN IMPORT YANG BENAR
        # from api_request import purchase_package
        # Karena file engsel.txt kosong, kita tidak bisa menggunakan purchase_package
        # Anda perlu memastikan implementasi purchase_package ada.
        # Untuk sementara, kita beri pesan error.
        await query.message.edit_text("❌ Fitur Beli dengan Pulsa untuk XUT belum sepenuhnya dikonfigurasi. Periksa implementasi API purchase.")
        # Contoh logika jika purchase_package ada:
        """
        result = purchase_package(api_key, tokens, package_code)
        if result and result.get("status") == "SUCCESS":
            await query.message.edit_text(
                "✅ Pembelian paket dengan Pulsa berhasil diinisiasi!\n"
                "Silakan cek hasil pembelian di aplikasi MyXL."
            )
        else:
            await query.message.edit_text(
                "❌ Gagal membeli paket dengan Pulsa.\n"
                "Silakan coba lagi atau gunakan metode pembayaran lain."
            )
        """
    except Exception as e:
        logger.error(f"Error processing Pulsa payment: {e}")
        await query.message.edit_text(
            "❌ Terjadi kesalahan saat memproses pembelian dengan Pulsa.\n"
            "Silakan coba lagi."
        )

async def buy_xut_with_ewallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pembelian paket XUT dengan E-Wallet (simulasi)"""
    query = update.callback_query
    await query.answer()
    package_info = context.user_data.get('selected_package')
    if not package_info:
        await query.message.edit_text("❌ Informasi paket tidak ditemukan. Silakan pilih paket kembali.")
        return
    # Simulasi pembelian dengan E-Wallet
    message = (
        "💳 *Pembelian dengan E-Wallet*\n"
        "Untuk menyelesaikan pembelian dengan E-Wallet:\n"
        "1. Buka aplikasi pembayaran Anda (DANA, OVO, GoPay, ShopeePay)\n"
        "2. Pilih menu Bayar atau Scan QR\n"
        "3. Gunakan kode pembayaran berikut:\n"
        f"   `EW-{package_info['code']}-{int(package_info['price'])}`\n"
        f"4. Konfirmasi pembayaran sebesar Rp {package_info['price']}\n"
        "Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
    )
    keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def buy_xut_with_qris(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pembelian paket XUT dengan QRIS"""
    query = update.callback_query
    await query.answer()
    package_info = context.user_data.get('selected_package')
    if not package_info:
        await query.message.edit_text("❌ Informasi paket tidak ditemukan. Silakan pilih paket kembali.")
        return
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        await query.message.edit_text("❌ Anda belum login. Silakan login terlebih dahulu.")
        return
    api_key = AuthInstance.api_key
    package_code = package_info['code']
    price = package_info['price']
    package_name = package_info['name']
    token_confirmation = package_info['token_confirmation']
    await query.message.edit_text("🔄 Memproses pembayaran QRIS...")
    try:
        # 1. Dapatkan metode pembayaran
        logger.info("Fetching payment methods for QRIS...")
        # Impor fungsi get_payment_methods
        # Placeholder untuk get_payment_methods - GANTILAH DENGAN IMPORT YANG BENAR
        # from purchase_api import get_payment_methods
        # Karena file purchase.txt tidak memiliki fungsi ini secara eksplisit (didefinisikan di dalam fungsi lain),
        # kita perlu memastikan implementasi send_api_request ada untuk menggunakannya.
        # Untuk sementara, kita beri pesan error.
        await query.message.edit_text("❌ Fitur Beli dengan QRIS untuk XUT belum sepenuhnya dikonfigurasi. Periksa implementasi API payment methods.")
        # Contoh logika jika get_payment_methods ada atau bisa dibuat:
        """
        payment_methods_data = get_payment_methods(
            api_key=api_key,
            tokens=tokens,
            token_confirmation=token_confirmation,
            payment_target=package_code,
        )
        if not payment_methods_
            await query.message.edit_text("❌ Gagal mendapatkan metode pembayaran QRIS.")
            return
        token_payment = payment_methods_data["token_payment"]
        ts_to_sign = payment_methods_data["timestamp"]
        # 2. Buat transaksi QRIS
        logger.info("Creating QRIS settlement...")
        # Impor fungsi settlement_qris
        # from purchase_api import settlement_qris
        transaction_id = settlement_qris(
            api_key=api_key,
            tokens=tokens,
            token_payment=token_payment,
            ts_to_sign=ts_to_sign,
            payment_target=package_code,
            price=price,
            item_name=package_name
        )
        if not transaction_id:
            await query.message.edit_text("❌ Gagal membuat transaksi QRIS.")
            return
        # 3. Dapatkan data QRIS
        logger.info("Fetching QRIS code...")
        # Impor fungsi get_qris_code
        # from purchase_api import get_qris_code
        qris_data = get_qris_code(api_key, tokens, transaction_id)
        if not qris_data:
            await query.message.edit_text("❌ Gagal mendapatkan data QRIS.")
            return
        # 4. Buat dan kirim QR Code
        logger.info("Generating QR Code image...")
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qris_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        # Simpan gambar ke buffer
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        # Kirim QR Code sebagai foto
        caption = (
            f"📲 *Pembayaran QRIS*\n"
            f"Silakan scan QR Code di bawah ini untuk menyelesaikan pembayaran.\n"
            f"📦 *Paket:* {package_name}\n"
            f"💰 *Harga:* Rp {price}\n"
            f"Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )
        await query.message.reply_photo(photo=img_buffer, caption=caption, parse_mode='Markdown')
        # Edit pesan sebelumnya
        await query.message.edit_text(
            "✅ QR Code pembayaran telah dikirim!\n"
            "Silakan scan QR Code yang dikirim di atas untuk menyelesaikan pembayaran.\n"
            "Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )
        # Reset state pembelian
        if 'selected_package' in context.user_
            del context.user_data['selected_package']
        """
    except Exception as e:
        logger.error(f"Error processing QRIS payment: {e}", exc_info=True)
        await query.message.edit_text(
            "❌ Terjadi kesalahan saat memproses pembayaran QRIS.\n"
            "Silakan coba lagi atau hubungi administrator jika masalah berlanjut."
        )
        
# === PEMBELIAN PAKET BERDASARKAN FAMILY CODE ===
async def request_family_code(update: Update, context: ContextTypes.DEFAULT_TYPE, is_enterprise: bool) -> None:
    """Minta Family Code dari pengguna"""
    query = update.callback_query
    await query.answer()
    context.user_data['state'] = 'waiting_family_code'
    context.user_data['enterprise'] = is_enterprise
    message = "🔍 Silakan kirimkan Family Code"
    if is_enterprise:
        message += " (Enterprise)"
    message += ":"
    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(message, reply_markup=reply_markup)

async def handle_family_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani input Family Code ATAU input amount manual untuk QRIS Family"""
    
    state = context.user_data.get('state')
    
    # --- PENANGANAN INPUT AMOUNT MANUAL UNTUK FAMILY QRIS ---
    if state == 'waiting_family_qris_amount':
        # 1. Ambil input jumlah dari pengguna
        amount_text = update.message.text.strip()
        
        # 2. Validasi format jumlah (harus angka)
        if not amount_text.isdigit():
            await update.message.reply_text(
                "❌ Jumlah tidak valid. Harap masukkan angka saja (tanpa titik/koma).\n"
                "Contoh: `500`, `1000`, `50000`\n"
                "Masukkan jumlah:"
            )
            return # Tunggu input ulang
        
        # 3. Konversi ke integer
        try:
            confirmed_amount = int(amount_text)
            if confirmed_amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            await update.message.reply_text(
                "❌ Jumlah tidak valid. Harus berupa angka positif.\n"
                "Contoh: `500`, `1000`, `50000`\n"
                "Masukkan jumlah:"
            )
            return # Tunggu input ulang
            
        # 4. Ambil data paket sementara yang disimpan sebelumnya
        tmp_data = context.user_data.get('tmp_family_qris_data')
        if not tmp_
             await update.message.reply_text("❌ Terjadi kesalahan. Data paket tidak ditemukan. Silakan ulangi proses pembelian.")
             context.user_data.pop('state', None)
             return
        
        # 5. Ambil data yang diperlukan
        tokens = AuthInstance.get_active_tokens()
        if not tokens:
            await update.message.reply_text("❌ Anda belum login. Silakan login terlebih dahulu.")
            context.user_data.pop('state', None)
            return
        api_key = AuthInstance.api_key
        
        package_code = tmp_data['package_code']
        package_name = tmp_data['package_name']
        token_confirmation = tmp_data['token_confirmation']
        
        # 6. Panggil fungsi internal untuk memproses pembayaran dengan amount yang dikonfirmasi
        # Karena ini dari MessageHandler, kita gunakan update.message sebagai 'query' untuk _process_family_qris_payment
        await _process_family_qris_payment(
            update.message, context,
            api_key, tokens,
            package_code, package_name, token_confirmation, confirmed_amount
        )
        
        # State dan data sementara sudah dihapus di dalam _process_family_qris_payment
        return # Selesai
        
    # --- PENANGANAN INPUT FAMILY CODE (ALUR NORMAL) ---
    # Ini adalah bagian asli handle_family_code_input
    if state != 'waiting_family_code':
        return # Bukan saatnya menerima Family Code
    
    family_code = update.message.text.strip()
    is_enterprise = context.user_data.get('enterprise', False)
    
    # Simpan family code dan tampilkan paket
    context.user_data['selected_family_code'] = family_code
    await update.message.reply_text("🔄 Mengambil daftar paket...")
    await show_family_packages(update, context, family_code, is_enterprise)
    
    # Hapus state setelah digunakan
    context.user_data.pop('state', None)

async def show_family_packages(update: Update, context: ContextTypes.DEFAULT_TYPE, family_code: str, is_enterprise: bool) -> None:
    """Display packages for a specific family code"""
    try:
        tokens = AuthInstance.get_active_tokens()
        if not tokens:
            # Cek apakah ini dari callback query atau message
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.message.edit_text("❌ Tidak ada akun aktif. Silakan login terlebih dahulu.")
            else:
                await update.message.reply_text("❌ Tidak ada akun aktif. Silakan login terlebih dahulu.")
            return
        api_key = AuthInstance.api_key
        data = get_family(api_key, tokens, family_code, is_enterprise)
        if not  # Periksa jika data itu sendiri None atau False
             if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.message.edit_text("❌ Gagal memuat data family.")
             else:
                await update.message.reply_text("❌ Gagal memuat data family.")
             return
        package_variants = data.get("package_variants", []) # Gunakan .get
        if not package_variants:
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.message.edit_text("📭 Tidak ada paket tersedia untuk family ini.")
            else:
                await update.message.reply_text("📭 Tidak ada paket tersedia untuk family ini.")
            return
        # Simpan data untuk referensi nanti
        context.user_data['family_data'] = data
        context.user_data['family_packages'] = []
        message = f"*Family Name:* {data.get('package_family', {}).get('name', 'N/A')}\n" # Gunakan .get
        keyboard = []
        option_number = 1
        for variant in package_variants:
            variant_name = variant.get("name", "N/A") # Gunakan .get
            message += f"🔹 *Variant:* {variant_name}\n"
            for option in variant.get("package_options", []): # Gunakan .get
                option_name = option.get("name", "N/A") # Gunakan .get
                price = option.get("price", 0) # Gunakan .get
                code = option.get("package_option_code", "") # Gunakan .get
                context.user_data['family_packages'].append({
                    "number": option_number,
                    "name": option_name,
                    "price": price,
                    "code": code
                })
                message += f"{option_number}. {option_name} - Rp {price}\n"
                keyboard.append([InlineKeyboardButton(
                    f"{option_number}. {option_name} (Rp {price})", 
                    callback_data=f'family_pkg_{option_number}'  # Gunakan nomor yang pendek
                )])
                option_number += 1
        message += "\n00. Kembali ke menu sebelumnya"
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error fetching family packages: {e}")
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.edit_text("❌ Terjadi kesalahan saat mengambil data paket family.")
        else:
            await update.message.reply_text("❌ Terjadi kesalahan saat mengambil data paket family.")

async def show_family_package_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan detail paket family yang dipilih"""
    query = update.callback_query
    await query.answer()
    try:
        # Parse nomor dari callback_data
        _, _, pkg_number_str = query.data.split('_')
        pkg_number = int(pkg_number_str)
        packages = context.user_data.get('family_packages', [])
        selected_pkg = next((p for p in packages if p["number"] == pkg_number), None)
        if not selected_pkg:
            await query.message.edit_text("❌ Paket tidak ditemukan.")
            return
        package_code = selected_pkg['code']
        # Ambil detail paket
        await query.message.edit_text("🔄 Mengambil detail paket...")
        tokens = AuthInstance.get_active_tokens()
        api_key = AuthInstance.api_key
        package_details = get_package(api_key, tokens, package_code)
        if not package_details:
            await query.message.edit_text("❌ Gagal mengambil detail paket.")
            return
        # Ekstrak informasi
        name1 = package_details.get("package_family", {}).get("name", "")
        name2 = package_details.get("package_detail_variant", {}).get("name", "")
        name3 = package_details.get("package_option", {}).get("name", "")
        package_name = f"{name1} {name2} {name3}".strip()
        price = package_details["package_option"]["price"]
        validity = package_details["package_option"]["validity"]
        tnc = display_html(package_details["package_option"]["tnc"])
        token_confirmation = package_details["token_confirmation"]
        benefits = package_details["package_option"]["benefits"]
        # Simpan informasi paket untuk pembelian
        context.user_data['selected_package'] = {
            'code': package_code,
            'name': package_name,
            'price': price,
            'validity': validity,
            'tnc': tnc,
            'token_confirmation': token_confirmation,
            'benefits': benefits
        }
        # Format pesan detail
        benefits_text = "\n".join([format_benefit(b) for b in benefits]) if benefits else "Tidak ada informasi benefit."
        message = (
            f"📦 *Detail Paket Family*\n"
            f"🏷 *Nama:* {package_name}\n"
            f"💰 *Harga:* Rp {price}\n"
            f"📅 *Masa Aktif:* {validity} hari\n"
            f"🔷 *Benefits:*\n{benefits_text}\n"
            f"📝 *Syarat & Ketentuan:*\n{tnc[:300]}..." # Batasi panjang T&C
        )
        keyboard = [
            [InlineKeyboardButton("💳 Beli dengan Pulsa", callback_data='buy_family_pulsa')],
            [InlineKeyboardButton("💳 Beli dengan E-Wallet", callback_data='buy_family_ewallet')],
            [InlineKeyboardButton("📲 Beli dengan QRIS", callback_data='buy_family_qris')],
            [InlineKeyboardButton("🔙 Kembali", callback_data='buy_family')], # Ini akan perlu ditangani kembali
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    except (ValueError, IndexError):
        await query.message.edit_text("❌ Data paket tidak valid.")
    except Exception as e:
        logger.error(f"Error showing family package details: {e}")
        await query.message.edit_text("❌ Terjadi kesalahan saat menampilkan detail paket.")

async def buy_family_with_pulsa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pembelian paket family dengan Pulsa"""
    await buy_xut_with_pulsa(update, context)  # Gunakan fungsi yang sama

async def buy_family_with_ewallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pembelian paket family dengan E-Wallet (simulasi)"""
    await buy_xut_with_ewallet(update, context)  # Gunakan fungsi yang sama

async def buy_family_with_qris(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pembelian paket family dengan QRIS"""
    query = update.callback_query
    await query.answer()
    
    # 1. Ambil informasi paket yang dipilih sebelumnya dan disimpan di context.user_data
    package_info = context.user_data.get('selected_package')
    
    # 2. Validasi: Apakah informasi paket ada?
    if not package_info:
        await query.message.edit_text("❌ Informasi paket tidak ditemukan. Silakan pilih paket kembali.")
        return

    # 3. Validasi: Apakah pengguna sudah login?
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        await query.message.edit_text("❌ Anda belum login. Silakan login terlebih dahulu.")
        return

    # 4. Ambil API key yang diperlukan untuk memanggil API MyXL
    api_key = AuthInstance.api_key

    # 5. Ekstrak data paket dasar
    package_code = package_info['code']
    package_name = package_info['name']
    # --- PERBEDAAN UTAMA ---
    # Ambil harga dari paket. Untuk Family Code, ini bisa 0 atau tidak sesuai.
    package_price_from_info = package_info['price'] 
    token_confirmation = package_info['token_confirmation']

    # --- LOGIKA PENENTUAN HARGA ---
    # Cek apakah harga dari info paket adalah 0 atau tidak valid.
    # Anda bisa menyesuaikan kondisi ini (misalnya < 1000) sesuai kebutuhan.
    if package_price_from_info <= 0:
        # 6a. Jika harga 0, masuki mode konfirmasi amount manual
        logger.info(f"[FAMILY QRIS] Harga paket terdeteksi 0 ({package_price_from_info}). Meminta konfirmasi amount.")
        
        # Simpan state bahwa bot sedang menunggu input amount manual
        context.user_data['state'] = 'waiting_family_qris_amount'
        # Simpan data paket sementara untuk digunakan setelah amount dimasukkan
        # Kita tidak bisa menimpa 'selected_package' karena masih dibutuhkan.
        context.user_data['tmp_family_qris_data'] = {
            'package_code': package_code,
            'package_name': package_name,
            'token_confirmation': token_confirmation
        }
        # Simpan referensi pesan utama untuk pengeditan nanti
        context.user_data['tmp_family_qris_main_message'] = query.message
        
        # Kirim pesan meminta amount ke pengguna
        await query.message.edit_text(
            f"⚠️ *Konfirmasi Harga untuk {package_name}*\n"
            "Harga paket terdeteksi sebagai Rp 0. "
            "Silakan masukkan jumlah pembayaran yang *VALID* (dalam Rupiah, tanpa titik/koma).\n\n"
            "*Petunjuk:*\n"
            "• Coba masukkan harga paket yang umum: `500`, `1000`, `2500`, `5000`, `10000`, `25000`, `50000`\n"
            "• Harga biasanya dalam kelipatan 500 atau 1000.\n"
            "• Pastikan jumlahnya sesuai dengan paket yang Anda pilih.\n"
            "Masukkan jumlah:",
            parse_mode='Markdown'
        )
        # Fungsi berhenti di sini. Nanti akan dilanjutkan oleh handler pesan teks.
        return
    else:
        # 6b. Jika harga tidak 0, gunakan harga tersebut dan lanjutkan ke pembayaran
        confirmed_price = package_price_from_info
        logger.info(f"[FAMILY QRIS] Menggunakan harga paket: Rp {confirmed_price}")
        # Langsung panggil fungsi internal untuk membuat QRIS
        # Kirim pesan utama (query.message) untuk pengeditan
        await _process_family_qris_payment(
            query.message, context, 
            api_key, tokens,
            package_code, package_name, token_confirmation, confirmed_price
        )

# --- FUNGSI PEMBANTU PEMBAYARAN FAMILY QRIS ---
async def _process_family_qris_payment(
    main_message, context: ContextTypes.DEFAULT_TYPE,
    api_key: str, tokens: dict,
    package_code: str, package_name: str, token_confirmation: str, confirmed_price: int
):
    """
    Fungsi internal untuk memproses pembayaran QRIS setelah harga dikonfirmasi.
    """
    # 1. Kirim pesan ke pengguna bahwa proses pembayaran QRIS sedang dimulai
    # Gunakan pesan utama untuk pengeditan
    try:
        await main_message.edit_text("🔄 Memproses pembayaran QRIS untuk paket Family...")
    except Exception as e:
        logger.error(f"[FAMILY QRIS] Gagal mengedit pesan utama: {e}")
        # Jika gagal edit, kirim pesan baru
        # Perlu objek update/query untuk reply, fallback ke context.user_data jika perlu
        # Untuk saat ini, log error dan hentikan
        return

    try:
        # --- LANGKAH 1: Dapatkan metode pembayaran dari API ---
        logger.info("[FAMILY QRIS] Fetching payment methods...")
        # Impor fungsi get_payment_methods
        # Placeholder untuk get_payment_methods - GANTILAH DENGAN IMPORT YANG BENAR
        # from purchase_api import get_payment_methods
        # Karena file purchase.txt tidak memiliki fungsi ini secara eksplisit (didefinisikan di dalam fungsi lain),
        # kita perlu memastikan implementasi send_api_request ada untuk menggunakannya.
        # Untuk sementara, kita beri pesan error.
        await main_message.edit_text("❌ Fitur Pembayaran QRIS untuk Family belum sepenuhnya dikonfigurasi. Periksa implementasi API payment methods.")
        # Contoh logika jika get_payment_methods ada atau bisa dibuat:
        """
        payment_methods_data = get_payment_methods(
            api_key=api_key,
            tokens=tokens,
            token_confirmation=token_confirmation,
            payment_target=package_code,
        )
        
        if not payment_methods_
            await main_message.edit_text("❌ Gagal mendapatkan metode pembayaran QRIS untuk paket Family.")
            return

        token_payment = payment_methods_data["token_payment"]
        ts_to_sign = payment_methods_data["timestamp"]

        # --- LANGKAH 2: Buat transaksi QRIS ---
        logger.info("[FAMILY QRIS] Creating QRIS settlement...")
        logger.info(f"[FAMILY QRIS DEBUG] Mengirim price: {confirmed_price} untuk paket {package_code}")
        # GUNAKAN FUNGSI PENGGANTI YANG TIDAK MEMINTA INPUT
        transaction_id = await settlement_qris_no_input(
            api_key=api_key,
            tokens=tokens,
            token_payment=token_payment,
            ts_to_sign=ts_to_sign,
            payment_target=package_code,
            price=confirmed_price,
            item_name=package_name
        )
        
        if not transaction_id:
            # --- PENANGANAN ERROR INVALID_PRICE ---
            error_msg = (
                "❌ Gagal membuat transaksi QRIS untuk paket Family.\n\n"
                "*Penyebab yang Diketahui (berdasarkan error sebelumnya):*\n"
                "• *INVALID_PRICE*: Jumlah pembayaran yang Anda masukkan (Rp {price}) mungkin tidak dikenali atau tidak valid untuk paket ini.\n\n"
                "*Solusi:*\n"
                "1. Pastikan jumlah yang Anda masukkan adalah kelipatan 500 atau 1000 (misalnya 500, 1000, 2500, 5000).\n"
                "2. Coba harga paket umum lainnya: 500, 1000, 2500, 5000, 10000, 25000, 50000.\n"
                "3. Jika masalah berlanjut, coba metode pembayaran lain atau hubungi admin."
            ).format(price=confirmed_price)
            await main_message.edit_text(error_msg, parse_mode='Markdown')
            logger.error(f"[FAMILY QRIS] Gagal membuat settlement. Price yang dikirim: {confirmed_price}")
            return

        # --- LANGKAH 3: Dapatkan data QRIS (kode QR) dari API ---
        logger.info("[FAMILY QRIS] Fetching QRIS code...")
        # Impor fungsi get_qris_code
        # from purchase_api import get_qris_code
        qris_data = get_qris_code(api_key, tokens, transaction_id)
        
        if not qris_
            await main_message.edit_text("❌ Gagal mendapatkan data QRIS untuk paket Family.")
            return

        # --- LANGKAH 4: Buat dan kirim QR Code sebagai gambar ---
        logger.info("[FAMILY QRIS] Generating QR Code image...")
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qris_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        caption = (
            f"📲 *Pembayaran QRIS (Family Code)*\n"
            f"Silakan scan QR Code di bawah ini untuk menyelesaikan pembayaran.\n"
            f"📦 *Paket:* {package_name}\n"
            f"💰 *Harga:* Rp {confirmed_price:,}\n"
            f"Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )
        # Kirim QR Code
        await main_message.reply_photo(photo=img_buffer, caption=caption, parse_mode='Markdown')

        # Edit pesan utama untuk memberi tahu bahwa QR Code sudah dikirim
        await main_message.edit_text(
            "✅ QR Code pembayaran untuk paket Family telah dikirim!\n"
            "Silakan scan QR Code yang dikirim di atas untuk menyelesaikan pembayaran.\n"
            "Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )

        # Reset state pembelian dan data sementara
        context.user_data.pop('selected_package', None)
        context.user_data.pop('tmp_family_qris_data', None)
        context.user_data.pop('tmp_family_qris_main_message', None)
        context.user_data.pop('state', None)
        """
    except Exception as e:
        logger.error(f"[FAMILY QRIS] Error processing payment: {e}", exc_info=True)
        try:
            await main_message.edit_text(
                "❌ Terjadi kesalahan saat memproses pembayaran QRIS untuk paket Family.\n"
                "Silakan coba lagi atau hubungi administrator jika masalah berlanjut."
            )
        except:
            pass # Abaikan error saat mencoba mengirim pesan error
        # Reset state juga jika error
        context.user_data.pop('selected_package', None)
        context.user_data.pop('tmp_family_qris_data', None)
        context.user_data.pop('tmp_family_qris_main_message', None)
        context.user_data.pop('state', None)

# === PEMBELIAN PAKET ANIV SECARA LANGSUNG ===

async def buy_aniv_package_direct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Membeli paket "BONUS #TraktiranXL 28th Anniversary" secara langsung.
    - Family Code: 6fda76ee-e789-4897-89fb-9114da47b805
    - Package Number: 7 (berdasarkan analisis Anda)
    - Price: 0 (dari API), Amount: 500 (dikonfirmasi manual untuk QRIS)
    """
    query = update.callback_query
    await query.answer()

    # 1. Pastikan pengguna sudah login
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        await query.message.edit_text("❌ Tidak ada akun aktif. Silakan login terlebih dahulu.")
        return

    await query.message.edit_text("🔄 Memproses pembelian paket Aniv...")

    try:
        # --- DATA PAKET ANIV ---
        FAMILY_CODE_ANIV = "6fda76ee-e789-4897-89fb-9114da47b805"
        PACKAGE_NUMBER_ANIV = 7
        PACKAGE_NAME_ANIV = "BONUS #TraktiranXL 28th Anniversary"
        PACKAGE_CODE_ANIV = "" # Akan diambil dari daftar paket
        TOKEN_CONFIRMATION_ANIV = "" # Akan diambil dari detail paket
        AMOUNT_ANIV = 500 # Harga tetap yang dikonfirmasi
        # --- AKHIR DATA ---

        # 2. Dapatkan daftar paket untuk Family Code Aniv
        api_key = AuthInstance.api_key
        # Fungsi get_family berasal dari api_request.py
        family_data = get_family(api_key, tokens, FAMILY_CODE_ANIV, is_enterprise=False)
        
        if not family_
             await query.message.edit_text("❌ Gagal mengambil data paket Aniv.")
             return

        package_variants = family_data.get("package_variants", [])
        if not package_variants:
             await query.message.edit_text("📭 Tidak ada paket tersedia untuk Family Code Aniv.")
             return

        # 3. Temukan paket dengan nomor 7
        # Logika ini meniru cara kerja show_family_packages dan show_family_package_details
        all_packages_list = []
        option_number = 1
        for variant in package_variants:
            # variant_name = variant["name"] # Tidak digunakan untuk pencarian
            for option in variant["package_options"]:
                # option_name = option["name"] # Tidak digunakan untuk pencarian
                # price = option["price"] # Tidak digunakan untuk pencarian
                code = option["package_option_code"]
                all_packages_list.append({
                    "number": option_number,
                    "code": code
                    # name, price bisa ditambahkan jika perlu untuk info
                })
                option_number += 1

        target_package_info = next((p for p in all_packages_list if p["number"] == PACKAGE_NUMBER_ANIV), None)
        
        if not target_package_info:
            await query.message.edit_text(
                f"❌ Paket nomor {PACKAGE_NUMBER_ANIV} ({PACKAGE_NAME_ANIV}) tidak ditemukan "
                f"pada Family Code `{FAMILY_CODE_ANIV}`."
            )
            return

        PACKAGE_CODE_ANIV = target_package_info['code']

        # 4. Ambil detail paket untuk mendapatkan token_confirmation
        # Fungsi get_package berasal dari api_request.py
        package_details = get_package(api_key, tokens, PACKAGE_CODE_ANIV)
        
        if not package_details:
             await query.message.edit_text("❌ Gagal mengambil detail paket Aniv.")
             return

        TOKEN_CONFIRMATION_ANIV = package_details.get("token_confirmation", "")

        if not TOKEN_CONFIRMATION_ANIV:
             await query.message.edit_text("❌ Gagal mendapatkan token konfirmasi untuk paket Aniv.")
             return

        logger.info(f"[ANIV DIRECT] Paket ditemukan: {PACKAGE_NAME_ANIV} ({PACKAGE_CODE_ANIV})")

        # 5. Siapkan data paket untuk pembayaran (mirip dengan context.user_data['selected_package'])
        # Simpan informasi paket sementara untuk pembayaran
        context.user_data['tmp_direct_aniv_data'] = {
            'package_code': PACKAGE_CODE_ANIV,
            'package_name': PACKAGE_NAME_ANIV,
            'token_confirmation': TOKEN_CONFIRMATION_ANIV,
            'confirmed_price': AMOUNT_ANIV # Gunakan amount tetap
        }
        
        # 6. Langsung panggil fungsi pembayaran QRIS internal dengan amount yang sudah ditentukan
        # Kita buat fungsi internal kecil untuk ini
        await _process_direct_aniv_qris_payment(query.message, context, api_key, tokens)

    except Exception as e:
        logger.error(f"[ANIV DIRECT] Error memulai pembelian: {e}", exc_info=True)
        await query.message.edit_text(
            "❌ Terjadi kesalahan saat memulai pembelian paket Aniv.\n"
            "Silakan coba lagi atau hubungi administrator."
        )


# --- FUNGSI PEMBANTU PEMBAYARAN ANIV LANGSUNG ---
async def _process_direct_aniv_qris_payment(
    main_message, context: ContextTypes.DEFAULT_TYPE,
    api_key: str, tokens: dict
):
    """
    Fungsi internal untuk memproses pembayaran QRIS paket Aniv dengan amount otomatis.
    """
    # Ambil data paket yang disimpan sementara
    tmp_data = context.user_data.get('tmp_direct_aniv_data')
    if not tmp_
        await main_message.edit_text("❌ Data paket Aniv tidak ditemukan. Silakan ulangi proses.")
        return

    package_code = tmp_data['package_code']
    package_name = tmp_data['package_name']
    token_confirmation = tmp_data['token_confirmation']
    confirmed_price = tmp_data['confirmed_price'] # Ini sudah 500

    # 1. Kirim pesan ke pengguna bahwa proses pembayaran QRIS sedang dimulai
    try:
        await main_message.edit_text(f"🔄 Memproses pembayaran QRIS untuk paket:\n`{package_name}`", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"[ANIV QRIS] Gagal mengedit pesan utama: {e}")
        return

    try:
        # --- LANGKAH 1: Dapatkan metode pembayaran dari API ---
        logger.info("[ANIV QRIS] Fetching payment methods...")
        # Impor fungsi get_payment_methods
        # Placeholder untuk get_payment_methods - GANTILAH DENGAN IMPORT YANG BENAR
        # from purchase_api import get_payment_methods
        # Karena file purchase.txt tidak memiliki fungsi ini secara eksplisit (didefinisikan di dalam fungsi lain),
        # kita perlu memastikan implementasi send_api_request ada untuk menggunakannya.
        # Untuk sementara, kita beri pesan error.
        await main_message.edit_text("❌ Fitur Pembayaran QRIS untuk Paket Aniv belum sepenuhnya dikonfigurasi. Periksa implementasi API payment methods.")
        # Contoh logika jika get_payment_methods ada atau bisa dibuat:
        """
        payment_methods_data = get_payment_methods(
            api_key=api_key,
            tokens=tokens,
            token_confirmation=token_confirmation,
            payment_target=package_code,
        )
        
        if not payment_methods_data:
            await main_message.edit_text("❌ Gagal mendapatkan metode pembayaran QRIS untuk paket Aniv.")
            return

        token_payment = payment_methods_data["token_payment"]
        ts_to_sign = payment_methods_data["timestamp"]

        # --- LANGKAH 2: Buat transaksi QRIS ---
        logger.info("[ANIV QRIS] Creating QRIS settlement...")
        logger.info(f"[ANIV QRIS DEBUG] Mengirim price: {confirmed_price} untuk paket {package_code}")
        # GUNAKAN FUNGSI PENGGANTI YANG TIDAK MEMINTA INPUT
        transaction_id = await settlement_qris_no_input(
            api_key=api_key,
            tokens=tokens,
            token_payment=token_payment,
            ts_to_sign=ts_to_sign,
            payment_target=package_code,
            price=confirmed_price, # Gunakan harga tetap 500
            item_name=package_name
        )
        
        if not transaction_id:
            error_msg = (
                f"❌ Gagal membuat transaksi QRIS untuk paket Aniv (`{package_name}`).\n\n"
                f"*Harga yang dikirim:* Rp {confirmed_price}\n\n"
                "*Penyebab yang Mungkin:*\n"
                "• Jumlah pembayaran (Rp 500) tidak dikenali untuk paket ini oleh API MyXL.\n"
                "• Token konfirmasi mungkin sudah kadaluarsa.\n\n"
                "*Solusi:*\n"
                "1. Coba lagi dalam beberapa menit.\n"
                "2. Gunakan metode pembayaran lain melalui menu 'Family Code' -> pilih paket -> QRIS.\n"
                "3. Hubungi administrator jika masalah berlanjut."
            )
            await main_message.edit_text(error_msg, parse_mode='Markdown')
            logger.error(f"[ANIV QRIS] Gagal membuat settlement. Price yang dikirim: {confirmed_price}")
            return

        # --- LANGKAH 3: Dapatkan data QRIS (kode QR) dari API ---
        logger.info("[ANIV QRIS] Fetching QRIS code...")
        # Impor fungsi get_qris_code
        # from purchase_api import get_qris_code
        qris_data = get_qris_code(api_key, tokens, transaction_id)
        
        if not qris_
            await main_message.edit_text("❌ Gagal mendapatkan data QRIS untuk paket Aniv.")
            return

        # --- LANGKAH 4: Buat dan kirim QR Code sebagai gambar ---
        logger.info("[ANIV QRIS] Generating QR Code image...")
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qris_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        caption = (
            f"🎉 *Pembayaran QRIS (Paket Aniv)*\n"
            f"Silakan scan QR Code di bawah ini untuk menyelesaikan pembayaran.\n"
            f"📦 *Paket:* `{package_name}`\n"
            f"💰 *Harga:* Rp {confirmed_price:,}\n"
            f"Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )
        # Kirim QR Code
        await main_message.reply_photo(photo=img_buffer, caption=caption, parse_mode='Markdown')

        # Edit pesan utama untuk memberi tahu bahwa QR Code sudah dikirim
        await main_message.edit_text(
            f"✅ QR Code pembayaran untuk paket Aniv (`{package_name}`) telah dikirim!\n"
            "Silakan scan QR Code yang dikirim di atas untuk menyelesaikan pembayaran.\n"
            "Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )

        # Reset data sementara
        context.user_data.pop('tmp_direct_aniv_data', None)
        """
    except Exception as e:
        logger.error(f"[ANIV QRIS] Error processing payment: {e}", exc_info=True)
        try:
            await main_message.edit_text(
                "❌ Terjadi kesalahan saat memproses pembayaran QRIS untuk paket Aniv.\n"
                "Silakan coba lagi atau hubungi administrator jika masalah berlanjut."
            )
        except:
            pass # Abaikan error saat mencoba mengirim pesan error
        # Reset data juga jika error
        context.user_data.pop('tmp_direct_aniv_data', None)

# --- AKHIR FUNGSI PEMBELIAN ANIV LANGSUNG ---

# === INFORMASI AKUN ===
async def show_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display account information"""
    query = update.callback_query
    await query.answer()
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        await query.message.edit_text("❌ Tidak ada akun aktif. Silakan login terlebih dahulu.")
        return
    try:
        await query.message.edit_text("🔄 Mengambil informasi akun...")
        api_key = AuthInstance.api_key
        id_token = tokens.get("id_token")
        access_token = tokens.get("access_token")
        # Get profile
        profile_data = get_profile(api_key, access_token, id_token)
        if not profile_
            await query.message.edit_text("❌ Gagal mengambil data profil.")
            return
        msisdn = profile_data.get("profile", {}).get("msisdn", "N/A")
        # Get balance
        balance_data = get_balance(api_key, id_token)
        if not balance_data:
            await query.message.edit_text("❌ Gagal mengambil data saldo.")
            return
        remaining = balance_data.get("remaining", 0)
        expired_at = balance_data.get("expired_at", "N/A")
        message = (
            f"👤 *Informasi Akun MyXL*\n"
            f"📱 *Nomor:* {msisdn}\n"
            f"💰 *Pulsa:* Rp {remaining:,}\n"
            f"📅 *Masa Aktif:* {expired_at}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error showing account info: {e}")
        await query.message.edit_text("❌ Terjadi kesalahan saat mengambil informasi akun.")

# === HANDLER CALLBACK ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani semua callback dari tombol"""
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"User {query.from_user.id} pressed button: {data}")

    # Menu Utama
    if data == 'main_menu':
        await show_main_menu(update, context)
    # Login & Ganti Akun (Perubahan)
    elif data == 'login_menu':
        await initiate_login(update, context) # Gunakan fungsi baru
    elif data == 'switch_account_menu': # Ganti nama callback untuk ganti akun
        await initiate_switch_account(update, context) # Gunakan fungsi baru
    # Lihat Paket Saya
    elif data == 'view_packages':
        await view_packages(update, context)
    # Beli Paket XUT
    elif data == 'buy_xut':
        await buy_xut_packages(update, context)
     # Beli Paket XUT Vidio Langsung
    elif data == 'buy_xut_vidio_direct':  # <-- Tambahkan ini
        await buy_xut_vidio_direct(update, context)
    elif data.startswith('xut_select_'):
        await show_xut_package_details(update, context)
    elif data == 'buy_xut_pulsa':
        await buy_xut_with_pulsa(update, context)
    elif data == 'buy_xut_ewallet':
        await buy_xut_with_ewallet(update, context)
    elif data == 'buy_xut_qris':
        await buy_xut_with_qris(update, context)
    # Beli Paket Berdasarkan Family Code
    elif data == 'buy_family':
        await request_family_code(update, context, is_enterprise=False)
    elif data == 'buy_family_enterprise':
        await request_family_code(update, context, is_enterprise=True)
    elif data.startswith('family_pkg_'):
        try:
            _, _, pkg_number_str = data.split('_')
            pkg_number = int(pkg_number_str)
            packages = context.user_data.get('family_packages', [])
            selected_pkg = next((p for p in packages if p["number"] == pkg_number), None)
            if selected_pkg:
                # Simpan paket yang dipilih untuk pembelian
                context.user_data['selected_package'] = {
                    'code': selected_pkg['code'],
                    'name': selected_pkg['name'],
                    'price': selected_pkg['price'],
                    'validity': "N/A",
                    'tnc': "N/A",
                    'token_confirmation': "N/A",  # Akan diambil saat pembelian
                    'benefits': []
                }
                # Langsung tampilkan detail paket
                await show_family_package_details(update, context)
            else:
                await query.message.edit_text("❌ Paket tidak ditemukan.")
        except (ValueError, IndexError):
            await query.message.edit_text("❌ Data paket tidak valid.")
    elif data == 'buy_family_pulsa':
        await buy_family_with_pulsa(update, context)
    elif data == 'buy_family_ewallet':
        await buy_family_with_ewallet(update, context)
    elif data == 'buy_family_qris':
        await buy_family_with_qris(update, context)
    # Informasi Akun
    elif data == 'account_info':
        await show_account_info(update, context)
    # Pembelian Paket Aniv Langsung
    elif data == 'buy_aniv_direct':
        await buy_aniv_package_direct(update, context)
    else:
        await query.message.edit_text("❌ Fitur belum diimplementasikan.")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /menu"""
    await show_main_menu(update, context)

# === MAIN FUNCTION ===
def main() -> None:
    """Menjalankan bot"""
    logger.info("Starting MyXL Telegram Bot...")
    # Buat aplikasi Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    # Tambahkan handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    # Handler untuk input OTP (6 digit) - HARUS DITAMBAHKAN SEBELUM handler nomor HP
    application.add_handler(MessageHandler(filters.Regex(r'^\d{6}$') & ~filters.COMMAND, handle_otp_input))
    # Handler untuk input nomor telepon (628...) - HARUS SETELAH handler OTP
    application.add_handler(MessageHandler(filters.Regex(r'^628\d{8,12}$') & ~filters.COMMAND, handle_phone_number_input))
    # Handler untuk input Family Code (atau teks lainnya)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_family_code_input))
    # Jalankan bot
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
