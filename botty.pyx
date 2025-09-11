# bot_telegram.py
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
from api_request import get_otp, submit_otp, get_profile, get_balance, get_package, get_family
from auth_helper import AuthInstance
from crypto_helper import load_ax_fp
from my_package import fetch_my_packages
from paket_custom_family import get_packages_by_family
from paket_xut import get_package_xut
from purchase_api import get_payment_methods, settlement_qris, get_qris_code, settlement_multipayment
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
    load_ax_fp()
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
        token_confirmation = package_details["token_confirmation"]
        # 7. Simpan informasi paket di context.user_data dengan KEY YANG SESUAI
        # Gunakan 'selected_package' agar bisa dibaca oleh buy_xut_with_qris
        context.user_data['selected_package'] = {
            'code': package_code,
            'name': package_name,
            'price': package_price,
            'token_confirmation': token_confirmation,
            # Tambahkan field lain jika diperlukan
            'validity': package_details["package_option"]["validity"],
            'benefits': package_details["package_option"]["benefits"],
            'tnc': package_details["package_option"]["tnc"]
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
    # Validasi format nomor
    if not phone_number.startswith("628") or not phone_number[1:].isdigit() or len(phone_number) < 10 or len(phone_number) > 15:
        await update.message.reply_text(
            "❌ Nomor telepon tidak valid.\n"
            "Pastikan formatnya adalah `628XXXXXXXXXX` (awali dengan 62).\n"
            "Contoh: `6281234567890`\n"
            "Silakan kirimkan nomor yang benar:"
        )
        return

    AuthInstance.load_tokens() # Muat token terbaru
    user_exists = any(str(user['number']) == phone_number for user in AuthInstance.refresh_tokens)
    active_user = AuthInstance.get_active_user()
    is_active = active_user and str(active_user['number']) == phone_number

    if state == 'waiting_phone_number_login':
        if user_exists:
            # Jika sudah ada, langsung aktifkan
            success = AuthInstance.set_active_user(int(phone_number))
            if success:
                await update.message.reply_text(f"✅ Akun `{phone_number}` sudah ada dan berhasil diaktifkan!", parse_mode='Markdown')
                await asyncio.sleep(1)
                await show_main_menu(update, context)
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
            return
        else:
            # Jika belum ada, minta OTP
            context.user_data['temp_phone'] = phone_number
            context.user_data['state'] = 'waiting_otp'
            await request_and_send_otp(update, phone_number)

    elif state == 'waiting_phone_number_switch':
        if user_exists:
            # Jika ada, langsung aktifkan
            success = AuthInstance.set_active_user(int(phone_number))
            if success:
                await update.message.reply_text(f"✅ Berhasil beralih ke akun `{phone_number}`.", parse_mode='Markdown')
                await asyncio.sleep(1)
                await show_main_menu(update, context)
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
            return
        else:
            # Jika tidak ada, minta OTP untuk login akun baru ini
            context.user_data['temp_phone'] = phone_number
            context.user_data['state'] = 'waiting_otp'
            await request_and_send_otp(update, phone_number)

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
        from api_request import send_api_request  # Tambahkan ini jika belum ada di import
        # Gunakan fungsi dari api_request.py
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
            from api_request import get_package  # Tambahkan ini jika belum ada di import
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
        from api_request import purchase_package
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
        payment_methods_data = get_payment_methods(
            api_key=api_key,
            tokens=tokens,
            token_confirmation=token_confirmation,
            payment_target=package_code,
        )
        if not payment_methods_data:
            await query.message.edit_text("❌ Gagal mendapatkan metode pembayaran QRIS.")
            return
        token_payment = payment_methods_data["token_payment"]
        ts_to_sign = payment_methods_data["timestamp"]
        # 2. Buat transaksi QRIS
        logger.info("Creating QRIS settlement...")
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
        if 'selected_package' in context.user_data:
            del context.user_data['selected_package']
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
    """Menangani input Family Code"""
    if context.user_data.get('state') != 'waiting_family_code':
        return # Bukan saatnya menerima Family Code
    family_code = update.message.text.strip()
    is_enterprise = context.user_data.get('enterprise', False)
    # Simpan family code dan tampilkan paket
    context.user_data['selected_family_code'] = family_code
    await update.message.reply_text("🔄 Mengambil daftar paket...")
    await show_family_packages(update, context, family_code, is_enterprise)
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
        if not data:
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.message.edit_text("❌ Gagal memuat data family.")
            else:
                await update.message.reply_text("❌ Gagal memuat data family.")
            return
        package_variants = data["package_variants"]
        if not package_variants:
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.message.edit_text("📭 Tidak ada paket tersedia untuk family ini.")
            else:
                await update.message.reply_text("📭 Tidak ada paket tersedia untuk family ini.")
            return
        # Simpan data untuk referensi nanti
        context.user_data['family_data'] = data
        context.user_data['family_packages'] = []
        message = f"*Family Name:* {data['package_family']['name']}\n"
        keyboard = []
        option_number = 1
        for variant in package_variants:
            variant_name = variant["name"]
            message += f"🔹 *Variant:* {variant_name}\n"
            for option in variant["package_options"]:
                option_name = option["name"]
                price = option["price"]
                code = option["package_option_code"]
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
    await buy_xut_with_qris(update, context)  # Gunakan fungsi yang sama
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
        if not profile_data:
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
# === HANDLER CALLBACK (Perubahan) ===
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
    else:
        await query.message.edit_text("❌ Fitur belum diimplementasikan.")
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /menu"""
    await show_main_menu(update, context)
# === MAIN FUNCTION (Pastikan urutan handler benar) ===
def main() -> None:
    """Menjalankan bot"""
    logger.info("Starting MyXL Telegram Bot...")
    # Buat aplikasi Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    # Tambahkan handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command)) # <-- TAMBAHKAN INI
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

