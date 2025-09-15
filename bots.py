# FILE: bot_telegram.py (VERSI LENGKAP & FINAL)

# =============================================================================
# Bagian 1: Imports
# =============================================================================
import os
import logging
import asyncio
from functools import wraps
from io import BytesIO
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

import qrcode
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Import dari file proyek Anda
from database import initialize_database, add_user, get_user_count, set_user_access, is_user_authorized
from api_request import get_otp, submit_otp, get_profile, get_balance, get_package, get_family, send_api_request
from auth_helper import AuthInstance
from crypto_helper import load_ax_fp
from paket_xut import get_package_xut
from purchase_api import get_payment_methods, settlement_qris, get_qris_code
from util import display_html, ensure_api_key

# =============================================================================
# Bagian 2: Konfigurasi & Inisialisasi
# =============================================================================
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Nonaktifkan warning SSL untuk requests
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
original_request = requests.request
def patched_request(method, url, **kwargs):
    kwargs['verify'] = False
    return original_request(method, url, **kwargs)
requests.request = patched_request

# Konfigurasi Bot
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set")

ADMIN_ID = 876081450  # !!! PASTIKAN INI ADALAH USER ID TELEGRAM ANDA !!!

# Inisialisasi AuthInstance (API MyXL)
try:
    AuthInstance.api_key = ensure_api_key()
    load_ax_fp()
    logger.info("Auth initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Auth: {e}")
    raise

# =============================================================================
# Bagian 3: Decorator untuk Otorisasi
# =============================================================================
def authorized_only(func):
    """Decorator untuk membatasi akses hanya untuk pengguna yang diotorisasi."""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        
        user_id = user.id
        if not is_user_authorized(user_id):
            logger.warning(f"Akses DITOLAK untuk user tidak terdaftar: {user_id}")
            if update.message:
                await update.message.reply_text("⛔ Anda tidak memiliki izin untuk menggunakan perintah ini.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Akses ditolak.", show_alert=True)
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

# =============================================================================
# Bagian 4: Fungsi Pembantu
# =============================================================================
def format_benefit(benefit):
    """Format benefit menjadi string yang mudah dibaca."""
    name = benefit['name']
    total = benefit.get('total', 0)
    if "Call" in name and total > 0:
        minutes = total / 60
        return f"• {name}: {minutes:.0f} menit"
    elif total > 0:
        if total >= 1_000_000_000: value, unit = total / (1024 ** 3), "GB"
        elif total >= 1_000_000: value, unit = total / (1024 ** 2), "MB"
        elif total >= 1_000: value, unit = total / 1024, "KB"
        else: value, unit = total, ""
        return f"• {name}: {value:.2f} {unit}" if unit else f"• {name}: {value}"
    else:
        return f"• {name}: {total}"

# =============================================================================
# Bagian 5: Handler Perintah Dasar & Admin
# =============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /start. Mendaftarkan pengguna baru."""
    user = update.effective_user
    add_user(user_id=user.id, username=user.username, first_name=user.first_name)
    logger.info(f"User {user.id} ({user.username}) started the bot. Saving to DB.")
    await update.message.reply_text(
        "Selamat datang! Akun Anda telah terdaftar.\n"
        "Untuk mendapatkan akses penuh, silakan hubungi admin."
    )

@authorized_only
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /menu. Menampilkan menu utama."""
    await show_main_menu(update, context)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(Admin) Menampilkan jumlah total pengguna."""
    if update.effective_user.id != ADMIN_ID:
        return
    user_count = get_user_count()
    await update.message.reply_text(f"📊 Jumlah total pengguna bot: {user_count} orang.")

async def grant_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(Admin) Memberikan akses ke pengguna. Format: /grant [user_id]"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
        return
    try:
        user_id_to_grant = int(context.args[0])
        set_user_access(user_id_to_grant, True)
        await update.message.reply_text(f"✅ Akses berhasil diberikan kepada user ID: {user_id_to_grant}")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Format salah. Gunakan: /grant [user_id]")

# =============================================================================
# Bagian 6: Handler Fitur-Fitur Bot (Semua dilindungi)
# =============================================================================
@authorized_only
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan menu utama bot."""
    active_user = AuthInstance.get_active_user()
    main_buttons = [
        InlineKeyboardButton("Cek Login", callback_data='switch_account_menu'),
        InlineKeyboardButton("XLUNLI", callback_data='buy_xut_vidio_direct'),
        InlineKeyboardButton("Lihat Paket Saya", callback_data='view_packages'),
        InlineKeyboardButton("🎯 Tembak Paket Aniv", callback_data='buy_aniv_direct'),
    ]
    keyboard = [main_buttons[i:i + 2] for i in range(0, len(main_buttons), 2)]
    if active_user:
        keyboard.append([InlineKeyboardButton("💳 Akun Saya", callback_data='account_info')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_message = "              *TEMBAK PAKET XL DAR DER DOR*\n"
    if active_user:
        welcome_message += f"✅ *Nomor Aktif: *`{active_user['number']}`\n"
    else:
        welcome_message += "🔐 *Status:* Belum login\n"
    welcome_message += "Silakan pilih menu di bawah ini:"
    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

@authorized_only
async def initiate_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses login - meminta nomor HP"""
    query = update.callback_query
    if query: await query.answer()
    message = (
        "📱 *Login ke MyXL*\n"
        "Silakan kirimkan nomor telepon Anda.\n"
        "Format: `08...` atau `628...`"
    )
    context.user_data['state'] = 'waiting_phone_number_login'
    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

@authorized_only
async def initiate_switch_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses ganti akun - meminta nomor HP"""
    query = update.callback_query
    if query: await query.answer()
    message = (
        "🔄 *Cek Login*\n"
        "Silakan kirimkan nomor telepon yang ingin diaktifkan.\n"
        "Format: `08...` atau `628...`"
    )
    context.user_data['state'] = 'waiting_phone_number_switch'
    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_phone_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani input nomor telepon untuk login atau ganti akun. Dijalankan via MessageHandler."""
    state = context.user_data.get('state')
    if state not in ['waiting_phone_number_login', 'waiting_phone_number_switch']:
        return

    phone_number = update.message.text.strip()
    original_input = phone_number

    if phone_number.startswith("08"):
        phone_number = "62" + phone_number[1:]
        logger.info(f"[LOGIN/SWITCH] Nomor dikonversi dari {original_input} ke {phone_number}")
    elif not phone_number.startswith("628"):
        await update.message.reply_text(f"❌ Format nomor `{original_input}` tidak valid. Harap gunakan `08...` atau `628...`.")
        return

    if not phone_number.isdigit() or len(phone_number) < 11 or len(phone_number) > 15:
        await update.message.reply_text(f"❌ Nomor telepon `{phone_number}` tidak valid setelah konversi. Pastikan panjangnya benar.")
        return

    AuthInstance.load_tokens()
    user_exists = any(str(user['number']) == phone_number for user in AuthInstance.refresh_tokens)

    if state == 'waiting_phone_number_login':
        if user_exists:
            success = AuthInstance.set_active_user(int(phone_number))
            if success:
                await update.message.reply_text(f"✅ Akun `{phone_number}` sudah ada dan berhasil diaktifkan!", parse_mode='Markdown')
                await asyncio.sleep(1)
                await show_main_menu(update, context)
            else:
                await update.message.reply_text(f"❌ Gagal mengaktifkan akun `{phone_number}`. Token mungkin sudah kadaluarsa. Meminta OTP...", parse_mode='Markdown')
                context.user_data['temp_phone'] = phone_number
                context.user_data['state'] = 'waiting_otp'
                await request_and_send_otp(update, phone_number)
        else:
            context.user_data['temp_phone'] = phone_number
            context.user_data['state'] = 'waiting_otp'
            await request_and_send_otp(update, phone_number)

    elif state == 'waiting_phone_number_switch':
        if user_exists:
            success = AuthInstance.set_active_user(int(phone_number))
            if success:
                await update.message.reply_text(f"✅ Berhasil beralih ke akun `{phone_number}`.", parse_mode='Markdown')
                await asyncio.sleep(1)
                await show_main_menu(update, context)
            else:
                await update.message.reply_text(f"❌ Gagal mengaktifkan akun `{phone_number}`. Token mungkin sudah kadaluarsa. Meminta OTP...", parse_mode='Markdown')
                context.user_data['temp_phone'] = phone_number
                context.user_data['state'] = 'waiting_otp'
                await request_and_send_otp(update, phone_number)
        else:
            await update.message.reply_text(f"❌ Akun `{phone_number}` tidak ditemukan. Memulai proses login baru...", parse_mode='Markdown')
            context.user_data['temp_phone'] = phone_number
            context.user_data['state'] = 'waiting_otp'
            await request_and_send_otp(update, phone_number)

async def request_and_send_otp(update: Update, phone_number: str) -> None:
    """Meminta OTP dan mengirimkannya ke pengguna"""
    await update.message.reply_text("🔄 Mengirimkan permintaan OTP...")
    try:
        subscriber_id = get_otp(phone_number)
        if not subscriber_id:
            await update.message.reply_text("❌ Gagal mengirim OTP.")
            context.user_data.clear() # Hapus state jika gagal
            return
        await update.message.reply_text(f"✅ OTP telah dikirim ke nomor {phone_number}.\nSilakan kirimkan kode OTP 6 digit yang Anda terima:")
    except Exception as e:
        logger.error(f"Error requesting OTP for {phone_number}: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan saat meminta OTP. Silakan coba lagi.")
        context.user_data.clear() # Hapus state jika gagal

async def handle_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani input OTP"""
    if context.user_data.get('state') != 'waiting_otp':
        return
    
    otp = update.message.text.strip()
    if not otp.isdigit() or len(otp) != 6:
        await update.message.reply_text("❌ Kode OTP tidak valid. Harus 6 digit angka.")
        return
        
    phone_number = context.user_data.get('temp_phone')
    if not phone_number:
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan mulai proses login dari awal.")
        context.user_data.clear()
        return

    await update.message.reply_text("🔄 Memverifikasi OTP...")
    try:
        tokens = submit_otp(AuthInstance.api_key, phone_number, otp)
        if not tokens:
            await update.message.reply_text("❌ OTP salah atau telah kedaluwarsa. Silakan coba lagi.")
            # Jangan hapus state, biarkan user mencoba lagi OTP atau nomor baru
            return
        AuthInstance.add_refresh_token(int(phone_number), tokens["refresh_token"])
        AuthInstance.set_active_user(int(phone_number))
        context.user_data.clear() # Hapus state setelah berhasil
        await update.message.reply_text("✅ Login berhasil! Anda sekarang dapat menggunakan semua fitur bot.")
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Error submitting OTP for {phone_number}: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan saat memverifikasi OTP. Silakan coba lagi.")

@authorized_only
async def view_packages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan paket aktif pengguna."""
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
        path = "api/v8/packages/quota-details"
        payload = {"is_enterprise": False, "lang": "en", "family_member_id": ""}
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
            message += f"\n*{i}. {quota['name']}*\n   `{quota['quota_code']}`"
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error viewing packages: {e}")
        await query.message.edit_text("❌ Terjadi kesalahan saat mengambil data paket.")

@authorized_only
async def show_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan informasi akun (saldo & masa aktif)."""
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
        
        profile_data = get_profile(api_key, access_token, id_token)
        msisdn = profile_data.get("profile", {}).get("msisdn", "N/A")
        
        balance_data = get_balance(api_key, id_token)
        remaining = balance_data.get("remaining", 0)
        expired_at = balance_data.get("expired_at", "N/A")
        
        message = (
            f"👤 *Informasi Akun MyXL*\n"
            f"📱 *Nomor:* `{msisdn}`\n"
            f"💰 *Pulsa:* Rp {remaining:,}\n"
            f"📅 *Masa Aktif:* {expired_at}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error showing account info: {e}")
        await query.message.edit_text("❌ Terjadi kesalahan saat mengambil informasi akun.")
        
@authorized_only
async def buy_xut_vidio_direct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Langsung tampilkan detail paket XUT Unlimited Turbo Vidio (nomor 11)"""
    query = update.callback_query
    await query.answer()
    try:
        tokens = AuthInstance.get_active_tokens()
        if not tokens:
            await query.message.edit_text("❌ Tidak ada akun aktif. Silakan login terlebih dahulu.")
            return
        await query.message.edit_text("🔄 Mengambil detail paket XUT Vidio...")
        api_key = AuthInstance.api_key
        packages = get_package_xut()
        if not packages:
            await query.message.edit_text("❌ Gagal mengambil data paket XUT.")
            return
        target_package = next((pkg for pkg in packages if pkg.get('number') == 11), None)
        if not target_package:
            await query.message.edit_text("❌ Paket XUT Unlimited Turbo Vidio (nomor 11) tidak ditemukan.")
            return
            
        package_code = target_package['code']
        package_details = get_package(api_key, tokens, package_code)
        if not package_details:
            await query.message.edit_text("❌ Gagal mengambil detail paket XUT Vidio.")
            return
            
        package_name = target_package['name']
        package_price = target_package['price']
        token_confirmation = package_details["token_confirmation"]
        
        context.user_data['selected_package'] = {
            'code': package_code, 'name': package_name, 'price': package_price,
            'token_confirmation': token_confirmation,
            'validity': package_details["package_option"]["validity"],
            'benefits': package_details["package_option"]["benefits"],
            'tnc': package_details["package_option"]["tnc"]
        }
        
        message = (
            f"📦 *Detail Paket*\n"
            f"🏷 *Nama:* {package_name}\n"
            f"💰 *Harga:* Rp {package_price:,}\n"
            "Pilih metode pembayaran:"
        )
        keyboard = [
            [InlineKeyboardButton("📲 Beli dengan QRIS", callback_data='buy_qris')],
            [InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error fetching XUT Vidio package: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan saat mengambil detail paket.")

@authorized_only
async def buy_aniv_package_direct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Membeli paket Anniversary secara langsung."""
    query = update.callback_query
    await query.answer()
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        await query.message.edit_text("❌ Tidak ada akun aktif.")
        return
    await query.message.edit_text("🔄 Memproses pembelian paket Aniv...")
    try:
        FAMILY_CODE_ANIV = "6fda76ee-e789-4897-89fb-9114da47b805"
        PACKAGE_NUMBER_ANIV = 7
        PACKAGE_NAME_ANIV = "BONUS #TraktiranXL 28th Anniversary"
        
        api_key = AuthInstance.api_key
        family_data = get_family(api_key, tokens, FAMILY_CODE_ANIV, is_enterprise=False)
        if not family_data or not family_data.get("package_variants"):
             await query.message.edit_text("❌ Gagal mengambil data paket Aniv atau paket tidak tersedia.")
             return

        all_packages_list = []
        option_number = 1
        for variant in family_data["package_variants"]:
            for option in variant["package_options"]:
                all_packages_list.append({"number": option_number, "code": option["package_option_code"]})
                option_number += 1

        target_package_info = next((p for p in all_packages_list if p["number"] == PACKAGE_NUMBER_ANIV), None)
        if not target_package_info:
            await query.message.edit_text(f"❌ Paket Aniv (nomor {PACKAGE_NUMBER_ANIV}) tidak ditemukan.")
            return

        package_code = target_package_info['code']
        package_details = get_package(api_key, tokens, package_code)
        if not package_details or "token_confirmation" not in package_details:
             await query.message.edit_text("❌ Gagal mengambil detail konfirmasi paket Aniv.")
             return

        context.user_data['selected_package'] = {
            'code': package_code, 'name': PACKAGE_NAME_ANIV, 'price': 0, # Harga asli 0
            'token_confirmation': package_details["token_confirmation"],
        }
        
        # Panggil fungsi pembayaran dengan flag khusus
        await process_generic_qris_payment(update, context, force_amount=500)

    except Exception as e:
        logger.error(f"[ANIV DIRECT] Error: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan saat memproses paket Aniv.")
        
@authorized_only
async def process_generic_qris_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, force_amount: int = None) -> None:
    """Fungsi generik untuk memproses pembayaran QRIS."""
    query = update.callback_query
    package_info = context.user_data.get('selected_package')
    if not package_info:
        await query.message.edit_text("❌ Informasi paket tidak ditemukan. Silakan pilih paket kembali.")
        return
        
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        await query.message.edit_text("❌ Anda belum login.")
        return

    api_key = AuthInstance.api_key
    package_code = package_info['code']
    price = force_amount if force_amount is not None else package_info['price']
    original_price = package_info['price']
    package_name = package_info['name']
    token_confirmation = package_info['token_confirmation']
    
    await query.message.edit_text(f"🔄 Memproses pembayaran QRIS untuk `{package_name}`...")
    
    try:
        payment_methods_data = get_payment_methods(api_key, tokens, token_confirmation, package_code)
        if not payment_methods_data:
            await query.message.edit_text("❌ Gagal mendapatkan metode pembayaran.")
            return
            
        token_payment = payment_methods_data["token_payment"]
        ts_to_sign = payment_methods_data["timestamp"]
        
        transaction_id = settlement_qris(
            api_key, tokens, token_payment, ts_to_sign, package_code,
            price=original_price, # Kirim harga asli
            item_name=package_name,
            force_amount=bool(force_amount) # Kirim flag
        )
        if not transaction_id:
            await query.message.edit_text(f"❌ Gagal membuat transaksi QRIS untuk `{package_name}`.")
            return
            
        qris_data = get_qris_code(api_key, tokens, transaction_id)
        if not qris_data:
            await query.message.edit_text("❌ Gagal mendapatkan data QRIS.")
            return

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qris_data)
        img_buffer = BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        caption = (
            f"📲 *Pembayaran QRIS*\n"
            f"Silakan scan QR Code untuk membayar.\n\n"
            f"📦 *Paket:* {package_name}\n"
            f"💰 *Harga:* Rp {price:,}"
        )
        await query.message.reply_photo(photo=img_buffer, caption=caption, parse_mode='Markdown')
        await query.message.edit_text("✅ QR Code pembayaran telah dikirim! Silakan selesaikan pembayaran.")
        
    except Exception as e:
        logger.error(f"Error processing QRIS payment: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan fatal saat memproses QRIS.")

# =============================================================================
# Bagian 7: Handler Tombol Utama (Callback Query)
# =============================================================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani semua callback dari tombol inline."""
    query = update.callback_query
    user_id = query.from_user.id

    if not is_user_authorized(user_id):
        logger.warning(f"Akses Tombol DITOLAK untuk user tidak terdaftar: {user_id}")
        await query.answer("⛔ Anda tidak memiliki izin untuk menggunakan tombol ini.", show_alert=True)
        return

    await query.answer()
    data = query.data
    logger.info(f"User {user_id} pressed button: {data}")

    # Router untuk setiap callback data
    if data == 'main_menu': await show_main_menu(update, context)
    elif data == 'switch_account_menu': await initiate_switch_account(update, context)
    elif data == 'login_menu': await initiate_login(update, context)
    elif data == 'view_packages': await view_packages(update, context)
    elif data == 'account_info': await show_account_info(update, context)
    elif data == 'buy_xut_vidio_direct': await buy_xut_vidio_direct(update, context)
    elif data == 'buy_aniv_direct': await buy_aniv_package_direct(update, context)
    elif data == 'buy_qris': await process_generic_qris_payment(update, context)
    else:
        await query.message.edit_text(f"❌ Fitur untuk `{data}` belum diimplementasikan.")

# =============================================================================
# Bagian 8: Fungsi Main
# =============================================================================
def main() -> None:
    """Menjalankan bot."""
    initialize_database()

    logger.info("Starting Bot...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Daftarkan semua handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("grant", grant_access))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Handler untuk input teks sensitif (OTP dan Nomor HP)
    application.add_handler(MessageHandler(filters.Regex(r'^\d{6}$'), handle_otp_input))
    application.add_handler(MessageHandler(filters.Regex(r'^(08|628)\d{8,12}$'), handle_phone_number_input))

    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
