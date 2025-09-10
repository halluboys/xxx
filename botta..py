# bot_telegram.py
import os
import json
import logging
import asyncio
import traceback
import re
from io import BytesIO
from dotenv import load_dotenv
from typing import Optional

# Muat variabel lingkungan
load_dotenv()

# Import library Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters, 
    ContextTypes
)

# Import library untuk membuat QR Code
import qrcode

# Nonaktifkan peringatan SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch requests untuk menonaktifkan verifikasi SSL
import requests
original_request = requests.request

def patched_request(method, url, **kwargs):
    kwargs['verify'] = False  # Nonaktifkan verifikasi SSL
    return original_request(method, url, **kwargs)

requests.request = patched_request

# Import modul-modul dari project MyXL
from api_request import get_otp, submit_otp, get_profile, get_balance, get_package, get_family
from auth_helper import AuthInstance
from crypto_helper import load_ax_fp
from my_package import fetch_my_packages
from paket_custom_family import get_packages_by_family
from paket_xut import get_package_xut
from purchase_api import get_payment_methods, settlement_qris, get_qris_code
from util import display_html, ensure_api_key

# === KONFIGURASI ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    # filename='/var/log/myxl_bot.log', # Uncomment jika ingin log ke file
    # filemode='a'
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
    try:
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
    except (KeyError, TypeError) as e:
        logger.error(f"Error formatting benefit: {e}")
        return "• Benefit tidak diketahui"

def cleanup_xut_vidio_direct_context(context):
    """Membersihkan data sementara dari context.user_data untuk XUT Vidio direct"""
    keys_to_remove = [
        'state',
        'xut_vidio_direct_payment_method',
        'target_number_for_xut_vidio_direct', 
        'previous_active_user_for_xut_vidio_direct',
        'manual_price', # Untuk harga manual jika diperlukan
        # Tambahkan key lain jika ada
    ]
    for key in keys_to_remove:
        if key in context.user_data:
            del context.user_data[key]

# === HANDLER UTAMA ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /start"""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    try:
        # Pastikan API key tersedia
        api_key = AuthInstance.api_key
        if not api_key:
            await update.message.reply_text("❌ API key tidak ditemukan. Silakan atur terlebih dahulu.")
            return
    except Exception as e:
        logger.error(f"Error loading API key: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan saat memuat API key.")
        return
        
    await show_main_menu(update, context)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /menu"""
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan menu utama"""
    try:
        # Periksa akun aktif
        active_user = AuthInstance.get_active_user()
        
        keyboard = [
            [InlineKeyboardButton("1. Login/Ganti akun", callback_data='login_menu')],
            [InlineKeyboardButton("2. Lihat Paket Saya", callback_data='view_packages')],
            [InlineKeyboardButton("🎬 XUT Vidio (DIRECT)", callback_data='buy_xut_vidio_direct_start')],
            [InlineKeyboardButton("3. Paket ALL XUT", callback_data='buy_xut')],
            [InlineKeyboardButton("4. Family Code", callback_data='buy_family')],
            [InlineKeyboardButton("5. Family Code (Enterprise)", callback_data='buy_family_enterprise')],
        ]
        
        # Tambahkan tombol "Akun Saya" hanya jika sudah login
        if active_user:
            keyboard.append([InlineKeyboardButton("💳 Akun Saya", callback_data='account_info')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = "*TEMBAK PAKET XLUNLI!*\n\n"
        
        # Tampilkan informasi akun aktif jika ada
        if active_user:
            welcome_message += f"*Nomor Aktif:* `{active_user['number']}`\n\n"
        else:
            welcome_message += "🔐 *Status:* Belum login\n\n"
            
        welcome_message += "Silakan pilih menu di bawah ini:"
        
        if update.message:
            await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.message.edit_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error showing main menu: {e}", exc_info=True)
        error_message = "❌ Terjadi kesalahan saat menampilkan menu utama. Silakan coba lagi."
        if update.message:
            await update.message.reply_text(error_message)
        else:
            await update.callback_query.message.edit_text(error_message)

# === LOGIN & GANTI AKUN ===

async def show_login_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display login menu"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Muat ulang token untuk mendapatkan daftar akun terkini
        AuthInstance.load_tokens()
        users = AuthInstance.refresh_tokens
        active_user = AuthInstance.get_active_user()
        
        keyboard = []
        message = "*🔐 Login / Ganti Akun*\n\n"
        
        # Jika ada akun tersimpan, tampilkan daftar akun
        if users:
            message += "*📱 Akun Tersimpan:*\n"
            for idx, user in enumerate(users):
                is_active = active_user and user["number"] == active_user["number"]
                active_marker = " ✅ *(Aktif)*" if is_active else ""
                keyboard.append([InlineKeyboardButton(
                    f"{idx + 1}. {user['number']}{active_marker}",
                    callback_data=f'switch_account_{idx}'
                )])
            message += "\n"
            
            # Tambahkan instruksi untuk ganti akun cepat
            message += "📱 *Ganti Akun Cepat:*\n"
            message += "Kirimkan nomor telepon yang sudah pernah login untuk langsung mengganti akun.\n\n"
            
            # Tambahkan tombol untuk aksi akun
            keyboard.append([InlineKeyboardButton("➕ Tambah Akun Baru", callback_data='request_otp')])
            keyboard.append([InlineKeyboardButton("🗑️ Hapus Akun Aktif", callback_data='delete_active_account')])
        else:
            # Jika tidak ada akun tersimpan
            message += "📭 Tidak ada akun tersimpan.\n\n"
            keyboard.append([InlineKeyboardButton("➕ Tambah Akun Baru", callback_data='request_otp')])
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error showing login menu: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan saat menampilkan menu login.")

async def request_otp_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Langkah 1: Minta nomor telepon"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "📱 *Login ke MyXL*\n\n"
        "Silakan kirimkan nomor telepon Anda yang terdaftar di MyXL.\n"
        "Format: `628XXXXXXXXXX` (awali dengan 62)\n\n"
        "Contoh: `6281234567890`"
    )
    
    # Simpan state bahwa user sedang menunggu input nomor
    context.user_data['state'] = 'waiting_phone_number'
    
    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='login_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_phone_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani input nomor telepon"""
    # Cek apakah ini untuk login atau ganti akun cepat
    if context.user_data.get('state') == 'waiting_phone_number':
        # Ini untuk login baru
        phone_number = update.message.text.strip()
        
        # Validasi format nomor
        if not phone_number.startswith("628") or not phone_number[1:].isdigit() or len(phone_number) < 10 or len(phone_number) > 15:
            await update.message.reply_text(
                "❌ Nomor telepon tidak valid.\n"
                "Pastikan formatnya adalah `628XXXXXXXXXX` (awali dengan 62).\n"
                "Contoh: `6281234567890`\n\n"
                "Silakan kirimkan nomor yang benar:"
            )
            return
        
        # Simpan nomor dan minta OTP
        context.user_data['temp_phone'] = phone_number
        await update.message.reply_text("🔄 Mengirimkan permintaan OTP...")
        
        try:
            subscriber_id = get_otp(phone_number)
            if not subscriber_id:
                await update.message.reply_text("❌ Gagal mengirim OTP.")
                return
                
            # Simpan state bahwa user sedang menunggu OTP
            context.user_data['state'] = 'waiting_otp'
            await update.message.reply_text(
                f"✅ OTP telah dikirim ke nomor {phone_number}.\n"
                "Silakan kirimkan kode OTP 6 digit yang Anda terima:"
            )
            
        except Exception as e:
            logger.error(f"Error requesting OTP for {phone_number}: {e}")
            await update.message.reply_text("❌ Terjadi kesalahan saat meminta OTP. Silakan coba lagi.")
    else:
        # Ini mungkin untuk ganti akun cepat
        await handle_switch_account_by_number(update, context)

async def handle_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani input OTP"""
    if context.user_data.get('state') != 'waiting_otp':
        return # Bukan saatnya menerima OTP
        
    otp = update.message.text.strip()
    
    # Validasi format OTP
    if not otp.isdigit() or len(otp) != 6:
        await update.message.reply_text(
            "❌ Kode OTP tidak valid.\n"
            "Pastikan OTP terdiri dari 6 digit angka.\n\n"
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
            context.user_data['state'] = 'waiting_phone_number' # Kembali ke input nomor
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

async def switch_account(update: Update, context: ContextTypes.DEFAULT_TYPE, account_index: int) -> None:
    """Beralih ke akun yang dipilih"""
    query = update.callback_query
    await query.answer()
    
    try:
        AuthInstance.load_tokens()
        users = AuthInstance.refresh_tokens
        
        if not users or account_index >= len(users):
            await query.message.edit_text("❌ Akun tidak ditemukan.")
            return
        
        selected_user = users[account_index]
        number = selected_user['number']
        
        # Coba set akun aktif
        success = AuthInstance.set_active_user(int(number))
        
        if success:
            await query.message.edit_text(f"✅ Berhasil beralih ke akun `{number}`.", parse_mode='Markdown')
            # Tunggu sebentar lalu kembali ke menu utama
            await asyncio.sleep(1)
            await show_main_menu(update, context)
        else:
            await query.message.edit_text(
                f"❌ Gagal beralih ke akun `{number}`. Token mungkin sudah kadaluarsa.\n\n"
                "Silakan login ulang untuk akun ini.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error switching account: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan saat mengganti akun.")

async def delete_active_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hapus akun aktif"""
    query = update.callback_query
    await query.answer()
    
    try:
        active_user = AuthInstance.get_active_user()
        
        if not active_user:
            await query.message.edit_text("❌ Tidak ada akun aktif untuk dihapus.")
            return
        
        number = active_user['number']
        
        # Konfirmasi penghapusan
        keyboard = [
            [InlineKeyboardButton("✅ Ya, Hapus", callback_data=f'confirm_delete_{number}')],
            [InlineKeyboardButton("❌ Batal", callback_data='login_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            f"⚠️ *Konfirmasi Penghapusan*\n\n"
            f"Yakin ingin menghapus akun `{number}`?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error deleting active account: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan saat menghapus akun.")

async def confirm_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE, number: int) -> None:
    """Konfirmasi dan hapus akun"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Hapus akun
        AuthInstance.remove_refresh_token(int(number))
        
        # Muat ulang token
        AuthInstance.load_tokens()
        
        await query.message.edit_text(f"✅ Akun `{number}` berhasil dihapus.", parse_mode='Markdown')
        # Tunggu sebentar lalu kembali ke menu login
        await asyncio.sleep(1)
        await show_login_menu(update, context)
        
    except Exception as e:
        logger.error(f"Error confirming delete account: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan saat mengonfirmasi penghapusan akun.")

async def handle_switch_account_by_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani ganti akun dengan mengirim nomor telepon"""
    phone_number = update.message.text.strip()
    
    # Validasi format nomor
    if not re.match(r'^628\d{8,12}$', phone_number):
        # Jika bukan format nomor, abaikan (bukan untuk handler ini)
        return
    
    try:
        # Muat ulang token untuk mendapatkan daftar akun terkini
        AuthInstance.load_tokens()
        users = AuthInstance.refresh_tokens
        
        # Cari apakah nomor sudah pernah login
        user_exists = any(str(user['number']) == phone_number for user in users)
        
        if not user_exists:
            # Nomor belum pernah login
            message = (
                f"❌ Nomor {phone_number} belum pernah login di bot ini.\n\n"
                "Silakan login terlebih dahulu melalui menu 'Login/Ganti akun' "
                "atau kirimkan perintah /start untuk memulai proses login."
            )
            await update.message.reply_text(message)
            return
            
        # Nomor sudah pernah login, coba set akun aktif
        success = AuthInstance.set_active_user(int(phone_number))
        
        if success:
            await update.message.reply_text(
                f"✅ Berhasil beralih ke akun `{phone_number}`.\n"
                "Nomor ini sekarang menjadi akun utama di bot."
            )
            # Tampilkan menu utama
            await show_main_menu(update, context)
        else:
            await update.message.reply_text(
                f"❌ Gagal menggunakan akun `{phone_number}` untuk pembelian.\n"
                "Token mungkin sudah kadaluarsa. Silakan login ulang untuk nomor ini."
            )
            
    except Exception as e:
        logger.error(f"Error handling switch account by number {phone_number}: {e}", exc_info=True)
        await update.message.reply_text("❌ Terjadi kesalahan saat mengganti akun. Silakan coba lagi.")

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
        
        # Gunakan fungsi dari api_request.py
        from api_request import send_api_request
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
            
        message = "*📦 Paket Saya:*\n\n"
        for i, quota in enumerate(quotas, 1):
            quota_code = quota["quota_code"]
            name = quota["name"]
            group_code = quota["group_code"]
            
            # Get package details
            package_details = get_package(api_key, tokens, quota_code)
            family_code = "N/A"
            if package_details:
                family_code = package_details["package_family"]["package_family_code"]
                
            message += (
                f"📦 *Paket {i}*\n"
                f"   Nama: {name}\n"
                f"   Kode Kuota: `{quota_code}`\n"
                f"   Kode Family: `{family_code}`\n"
                f"   Kode Grup: `{group_code}`\n\n"
            )
            
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error viewing packages: {e}", exc_info=True)
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
        
        message = "*🛒 Paket XUT (Unli Turbo)*\n\n"
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
        logger.error(f"Error fetching XUT packages: {e}", exc_info=True)
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
            f"📦 *Detail Paket XUT*\n\n"
            f"🏷 *Nama:* {package_name}\n"
            f"💰 *Harga:* Rp {price}\n"
            f"📅 *Masa Aktif:* {validity} hari\n\n"
            f"🔷 *Benefits:*\n{benefits_text}\n\n"
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
        logger.error(f"Error showing XUT package details: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan saat menampilkan detail paket.")

async def buy_xut_with_pulsa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pembelian paket XUT dengan Pulsa"""
    query = update.callback_query
    await query.answer()
    
    try:
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
        logger.error(f"Error processing Pulsa payment: {e}", exc_info=True)
        await query.message.edit_text(
            "❌ Terjadi kesalahan saat memproses pembelian dengan Pulsa.\n"
            "Silakan coba lagi."
        )

async def buy_xut_with_ewallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pembelian paket XUT dengan E-Wallet (simulasi)"""
    query = update.callback_query
    await query.answer()
    
    try:
        package_info = context.user_data.get('selected_package')
        if not package_info:
            await query.message.edit_text("❌ Informasi paket tidak ditemukan. Silakan pilih paket kembali.")
            return
        
        # Simulasi pembelian dengan E-Wallet
        message = (
            "💳 *Pembelian dengan E-Wallet*\n\n"
            "Untuk menyelesaikan pembelian dengan E-Wallet:\n\n"
            "1. Buka aplikasi pembayaran Anda (DANA, OVO, GoPay, ShopeePay)\n"
            "2. Pilih menu Bayar atau Scan QR\n"
            "3. Gunakan kode pembayaran berikut:\n"
            f"   `EW-{package_info['code']}-{int(package_info['price'])}`\n"
            f"4. Konfirmasi pembayaran sebesar Rp {package_info['price']}\n\n"
            "Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error processing E-Wallet payment: {e}", exc_info=True)
        await query.message.edit_text(
            "❌ Terjadi kesalahan saat memproses pembelian dengan E-Wallet.\n"
            "Silakan coba lagi."
        )

async def buy_xut_with_qris(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pembelian paket XUT dengan QRIS"""
    query = update.callback_query
    await query.answer()
    
    try:
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
        
        # 1. Dapatkan metode pembayaran dengan amount yang sudah di-set
        logger.info("Fetching payment methods for QRIS with amount...")
        payment_methods_data = get_payment_methods(
            api_key=api_key,
            tokens=tokens,
            token_confirmation=token_confirmation,
            payment_target=package_code,
            amount=price  # OTOMATIS SET AMOUNT SESUAI HARGA PAKET
        )
        
        if not payment_methods_
            await query.message.edit_text(
                "❌ Gagal mendapatkan metode pembayaran QRIS.\n"
                "Kemungkinan penyebab:\n"
                "• Token login sudah kadaluarsa.\n"
                "• Informasi paket tidak valid.\n"
                "• Gangguan jaringan sementara.\n\n"
                "Silakan coba login ulang atau pilih paket lain."
            )
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
        
        if not qris_
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
            f"📲 *Pembayaran QRIS*\n\n"
            f"Silakan scan QR Code di bawah ini untuk menyelesaikan pembayaran.\n\n"
            f"📦 *Paket:* {package_name}\n"
            f"💰 *Harga:* Rp {price:,}\n\n"
            f"Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )
        
        await query.message.reply_photo(photo=img_buffer, caption=caption, parse_mode='Markdown')
        
        # Edit pesan sebelumnya
        await query.message.edit_text(
            "✅ QR Code pembayaran telah dikirim!\n"
            "Silakan scan QR Code yang dikirim di atas untuk menyelesaikan pembayaran.\n\n"
            "Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )
        
        # Reset state pembelian
        if 'selected_package' in context.user_
            del context.user_data['selected_package']
            
    except Exception as e:
        logger.error(f"Error processing QRIS payment: {e}", exc_info=True)
        await query.message.edit_text(
            "❌ Terjadi kesalahan saat memproses pembayaran QRIS.\n"
            "Silakan coba lagi atau hubungi administrator jika masalah berlanjut."
        )

# === PEMBELIAN PAKET XUT VIDIO DIRECT ===

async def buy_xut_vidio_direct_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Langsung ke pemilihan metode pembayaran untuk XUT Vidio (nomor 11)"""
    query = update.callback_query
    await query.answer()

    # Tampilkan opsi metode pembayaran langsung untuk paket XUT Vidio nomor 11
    message = (
        "🎬 *Beli XUT Vidio (Langsung - Nomor 11)*\n\n"
        "Pilih metode pembayaran:"
    )

    keyboard = [
        [InlineKeyboardButton("💳 Pulsa", callback_data='buy_xut_vidio_direct_pulsa')],
        [InlineKeyboardButton("💳 E-Wallet", callback_data='buy_xut_vidio_direct_ewallet')],
        [InlineKeyboardButton("📲 QRIS", callback_data='buy_xut_vidio_direct_qris')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_xut_vidio_direct_payment_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani pilihan metode pembayaran untuk XUT Vidio direct dan meminta nomor tujuan"""
    query = update.callback_query
    await query.answer()

    payment_method = query.data.split('_')[-1] # Dapatkan metode pembayaran (pulsa, ewallet, qris)
    
    # Simpan metode pembayaran yang dipilih
    context.user_data['xut_vidio_direct_payment_method'] = payment_method
    
    # Minta nomor tujuan
    message = (
        f"📲 *Pembelian XUT Vidio via {payment_method.capitalize()}*\n\n"
        "Silakan masukkan *nomor XL* tujuan yang ingin dibelikan paket XUT Unlimited Turbo Vidio (nomor 11).\n\n"
        "Format: `628XXXXXXXXXX`\n"
        "Contoh: `6281234567890`"
    )
    
    # Simpan state bahwa user sedang menunggu input nomor tujuan untuk XUT Vidio direct
    context.user_data['state'] = 'waiting_target_number_for_xut_vidio_direct'
    
    keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_target_number_for_xut_vidio_direct_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani input nomor tujuan untuk pembelian XUT Vidio direct"""
    # Cek apakah ini adalah state yang benar
    if context.user_data.get('state') != 'waiting_target_number_for_xut_vidio_direct':
        return # Bukan saatnya menerima input ini
        
    target_number = update.message.text.strip()
    
    # Validasi format nomor
    if not re.match(r'^628\d{8,12}$', target_number):
        await update.message.reply_text(
            "❌ Nomor tidak valid.\n"
            "Pastikan formatnya adalah `628XXXXXXXXXX`.\n"
            "Contoh: `6281234567890`\n\n"
            "Silakan kirimkan nomor yang benar:"
        )
        return
    
    try:
        # Simpan nomor target sementara
        context.user_data['target_number_for_xut_vidio_direct'] = target_number
        
        # Periksa apakah nomor ini sudah pernah login
        AuthInstance.load_tokens() # Muat ulang token
        users = AuthInstance.refresh_tokens
        
        user_exists = any(str(user['number']) == target_number for user in users)
        
        if not user_exists:
            # Nomor belum pernah login
            message = (
                f"❌ Nomor {target_number} belum pernah login di bot ini.\n\n"
                "Silakan login terlebih dahulu untuk nomor tersebut melalui menu 'Login/Ganti akun'."
            )
            keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data='main_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup)
            # Reset state
            if 'state' in context.user_
                del context.user_data['state']
            return
            
        # Nomor sudah pernah login, lanjutkan ke proses pembayaran
        payment_method = context.user_data.get('xut_vidio_direct_payment_method', 'qris')
        
        if payment_method == 'qris':
            await process_xut_vidio_direct_qris_payment(update, context)
        elif payment_method == 'pulsa':
            await process_xut_vidio_direct_pulsa_payment(update, context)
        elif payment_method == 'ewallet':
            await process_xut_vidio_direct_ewallet_payment(update, context)
        else:
            # Default ke QRIS jika metode tidak dikenali
            await process_xut_vidio_direct_qris_payment(update, context)
            
    except Exception as e:
        logger.error(f"Error handling target number for XUT Vidio direct: {e}", exc_info=True)
        # Reset state
        if 'state' in context.user_
            del context.user_data['state']
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi dari awal.")

async def process_xut_vidio_direct_qris_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Proses pembayaran QRIS untuk XUT Vidio direct ke nomor tujuan"""
    # Kita bisa menggunakan pesan dari input sebelumnya atau kirim pesan baru
    # Untuk menyederhanakan, kita asumsi ini dipanggil dari handler pesan
    message_obj = update.message
    
    target_number = context.user_data.get('target_number_for_xut_vidio_direct')
    
    if not target_number:
        await message_obj.reply_text("❌ Informasi nomor tujuan tidak ditemukan. Silakan mulai dari awal.")
        return
        
    try:
        await message_obj.reply_text("🔄 Memproses pembayaran QRIS untuk nomor tujuan...")
        
        # 1. Set akun aktif ke nomor target (karena kita butuh token untuk pembayaran)
        # Simpan akun aktif sebelumnya untuk dikembalikan nanti (opsional)
        previous_active_user = AuthInstance.get_active_user()
        context.user_data['previous_active_user_for_xut_vidio_direct'] = previous_active_user['number'] if previous_active_user else None
        
        success = AuthInstance.set_active_user(int(target_number))
        if not success:
            # Bersihkan context
            cleanup_xut_vidio_direct_context(context)
            error_message = (
                f"⚠️ Tidak dapat menggunakan akun {target_number} untuk pembelian.\n"
                f"Kemungkinan penyebab:\n"
                f"• Token login sudah kadaluarsa.\n"
                f"• Akun belum pernah login di bot ini.\n\n"
                f"Silakan:\n"
                f"1. Login ulang untuk nomor {target_number} melalui menu 'Login/Ganti akun'.\n"
                f"2. Atau kembali ke menu utama."
            )
            keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data='main_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message_obj.reply_text(error_message, reply_markup=reply_markup)
            return # Hentikan eksekusi
            
        # 2. Dapatkan token yang baru saja di-set
        tokens = AuthInstance.get_active_tokens()
        api_key = AuthInstance.api_key
        
        if not tokens:
            # Bersihkan context
            cleanup_xut_vidio_direct_context(context)
            await message_obj.reply_text("❌ Gagal mendapatkan token untuk pembelian.")
            return
            
        # 3. Dapatkan paket XUT Vidio nomor 11
        packages = get_package_xut()
        if not packages:
            # Bersihkan context
            cleanup_xut_vidio_direct_context(context)
            await message_obj.reply_text("❌ Gagal mengambil data paket XUT.")
            return
            
        # Cari paket nomor 11
        target_package = next((pkg for pkg in packages if pkg.get('number') == 11), None)
        if not target_package:
            # Bersihkan context
            cleanup_xut_vidio_direct_context(context)
            await message_obj.reply_text("❌ Paket XUT Unlimited Turbo Vidio (nomor 11) tidak ditemukan.")
            return
            
        # 4. Dapatkan detail paket lengkap untuk token_confirmation
        package_code = target_package['code']
        package_details = get_package(api_key, tokens, package_code)
        
        if not package_details:
            # Bersihkan context
            cleanup_xut_vidio_direct_context(context)
            await message_obj.reply_text("❌ Gagal mengambil detail paket untuk pembelian.")
            return
            
        token_confirmation = package_details["token_confirmation"]
        package_name = target_package['name']
        price = target_package['price']
        
        # 5. Proses pembayaran QRIS (mirip dengan buy_xut_with_qris tapi khusus)
        # a. Dapatkan metode pembayaran dengan amount yang sudah di-set
        payment_methods_data = get_payment_methods(
            api_key=api_key,
            tokens=tokens,
            token_confirmation=token_confirmation,
            payment_target=package_code,
            amount=price  # OTOMATIS SET AMOUNT SESUAI HARGA PAKET
        )
        
        if not payment_methods_
            # Bersihkan context
            cleanup_xut_vidio_direct_context(context)
            await message_obj.reply_text("❌ Gagal mendapatkan metode pembayaran QRIS.")
            return
            
        token_payment = payment_methods_data["token_payment"]
        ts_to_sign = payment_methods_data["timestamp"]
        
        # b. Buat transaksi QRIS
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
            # Bersihkan context
            cleanup_xut_vidio_direct_context(context)
            await message_obj.reply_text("❌ Gagal membuat transaksi QRIS.")
            return
            
        # c. Dapatkan data QRIS
        qris_data = get_qris_code(api_key, tokens, transaction_id)
        
        if not qris_
            # Bersihkan context
            cleanup_xut_vidio_direct_context(context)
            await message_obj.reply_text("❌ Gagal mendapatkan data QRIS.")
            return
            
        # d. Buat dan kirim QR Code
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qris_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        caption = (
            f"📲 *Pembayaran QRIS untuk {target_number}*\n\n"
            f"Silakan scan QR Code di bawah ini untuk menyelesaikan pembayaran.\n\n"
            f"📦 *Paket:* {package_name}\n"
            f"💰 *Harga:* Rp {price:,}\n\n"
            f"Setelah pembayaran berhasil, paket akan otomatis masuk ke nomor {target_number}."
        )
        
        await message_obj.reply_photo(photo=img_buffer, caption=caption, parse_mode='Markdown')
        
        # Kirim pesan konfirmasi
        await message_obj.reply_text(
            f"✅ QR Code pembayaran telah dikirim!\n"
            f"Silakan scan QR Code yang dikirim di atas untuk menyelesaikan pembayaran untuk nomor {target_number}.\n\n"
            f"Setelah pembayaran berhasil, paket akan otomatis masuk ke akun tersebut."
        )
        
        # Bersihkan context
        cleanup_xut_vidio_direct_context(context)
                
    except Exception as e:
        logger.error(f"Error processing QRIS payment for {target_number} (direct): {e}", exc_info=True)
        # Bersihkan context
        cleanup_xut_vidio_direct_context(context)
        await message_obj.reply_text(
            f"❌ Terjadi kesalahan saat memproses pembayaran QRIS untuk {target_number}.\n"
            f"Silakan coba lagi dari awal atau hubungi administrator."
        )

# Fungsi untuk metode pembayaran lainnya (simulasi)
async def process_xut_vidio_direct_pulsa_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Simulasi proses pembelian dengan Pulsa untuk XUT Vidio direct"""
    message_obj = update.message
    target_number = context.user_data.get('target_number_for_xut_vidio_direct')
    
    # Dapatkan detail paket (sama seperti QRIS)
    try:
        AuthInstance.set_active_user(int(target_number))
        tokens = AuthInstance.get_active_tokens()
        api_key = AuthInstance.api_key
        
        packages = get_package_xut()
        target_package = next((pkg for pkg in packages if pkg.get('number') == 11), None)
        if not target_package:
            await message_obj.reply_text("❌ Paket tidak ditemukan.")
            return
            
        package_code = target_package['code']
        package_details = get_package(api_key, tokens, package_code)
        if not package_details:
            await message_obj.reply_text("❌ Gagal mengambil detail paket.")
            return
            
        package_name = target_package['name']
        price = target_package['price']
        
        # Simulasi pembelian dengan Pulsa (panggil API asli)
        from api_request import purchase_package
        result = purchase_package(api_key, tokens, package_code)
        
        if result and result.get("status") == "SUCCESS":
            await message_obj.reply_text(
                f"✅ Pembelian paket {package_name} untuk nomor {target_number} dengan Pulsa berhasil diinisiasi!\n"
                f"Silakan cek hasil pembelian di aplikasi MyXL."
            )
        else:
            await message_obj.reply_text(
                f"❌ Gagal membeli paket {package_name} untuk nomor {target_number} dengan Pulsa.\n"
                f"Silakan coba lagi atau gunakan metode pembayaran lain."
            )
            
        # Bersihkan context
        cleanup_xut_vidio_direct_context(context)
        
    except Exception as e:
        logger.error(f"Error processing Pulsa payment for {target_number} (direct XUT Vidio): {e}")
        cleanup_xut_vidio_direct_context(context)
        await message_obj.reply_text(
            f"❌ Terjadi kesalahan saat memproses pembelian dengan Pulsa untuk {target_number}.\n"
            f"Silakan coba lagi."
        )

async def process_xut_vidio_direct_ewallet_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Simulasi proses pembelian dengan E-Wallet untuk XUT Vidio direct"""
    message_obj = update.message
    target_number = context.user_data.get('target_number_for_xut_vidio_direct')
    
    # Dapatkan detail paket (sama seperti QRIS)
    try:
        # Kita tidak perlu mengganti akun aktif untuk simulasi E-Wallet
        packages = get_package_xut()
        target_package = next((pkg for pkg in packages if pkg.get('number') == 11), None)
        if not target_package:
            await message_obj.reply_text("❌ Paket tidak ditemukan.")
            return
            
        package_name = target_package['name']
        price = target_package['price']
        package_code = target_package['code']
        
        # Simulasi pembelian dengan E-Wallet
        message = (
            f"💳 *Pembelian dengan E-Wallet untuk {target_number}*\n\n"
            f"Untuk menyelesaikan pembelian paket {package_name}:\n\n"
            f"1. Buka aplikasi pembayaran Anda (DANA, OVO, GoPay, ShopeePay)\n"
            f"2. Pilih menu Bayar atau Scan QR\n"
            f"3. Gunakan kode pembayaran berikut:\n"
            f"   `EW-{package_code}-{int(price)}`\n"
            f"4. Konfirmasi pembayaran sebesar Rp {price:,}\n\n"
            f"Setelah pembayaran berhasil, paket akan otomatis masuk ke nomor {target_number}."
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message_obj.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Bersihkan context
        cleanup_xut_vidio_direct_context(context)
        
    except Exception as e:
        logger.error(f"Error processing E-Wallet payment for {target_number} (direct XUT Vidio): {e}")
        cleanup_xut_vidio_direct_context(context)
        await message_obj.reply_text(
            f"❌ Terjadi kesalahan saat memproses pembelian dengan E-Wallet untuk {target_number}.\n"
            f"Silakan coba lagi."
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
        
        message = f"*Family Name:* {data['package_family']['name']}\n\n"
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
        logger.error(f"Error fetching family packages: {e}", exc_info=True)
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
            f"📦 *Detail Paket Family*\n\n"
            f"🏷 *Nama:* {package_name}\n"
            f"💰 *Harga:* Rp {price}\n"
            f"📅 *Masa Aktif:* {validity} hari\n\n"
            f"🔷 *Benefits:*\n{benefits_text}\n\n"
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
        logger.error(f"Error showing family package details: {e}", exc_info=True)
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
    
    try:
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
        
        # Dapatkan token_confirmation dengan mengambil detail paket
        try:
            package_details = get_package(api_key, tokens, package_code)
            if not package_details:
                await query.message.edit_text("❌ Gagal mengambil detail paket untuk pembayaran.")
                return
                
            token_confirmation = package_details["token_confirmation"]
        except Exception as e:
            logger.error(f"Error getting package details: {e}")
            await query.message.edit_text("❌ Gagal mengambil informasi paket.")
            return
        
        await query.message.edit_text("🔄 Memproses pembayaran QRIS...")
        
        # 1. Dapatkan metode pembayaran dengan amount yang sudah di-set
        logger.info("Fetching payment methods for QRIS with amount...")
        payment_methods_data = get_payment_methods(
            api_key=api_key,
            tokens=tokens,
            token_confirmation=token_confirmation,
            payment_target=package_code,
            amount=price  # OTOMATIS SET AMOUNT SESUAI HARGA PAKET
        )
        
        if not payment_methods_
            await query.message.edit_text(
                "❌ Gagal mendapatkan metode pembayaran QRIS.\n"
                "Kemungkinan penyebab:\n"
                "• Token login sudah kadaluarsa.\n"
                "• Informasi paket tidak valid.\n"
                "• Gangguan jaringan sementara.\n\n"
                "Silakan coba login ulang atau pilih paket lain."
            )
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
        
        if not qris_
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
            f"📲 *Pembayaran QRIS*\n\n"
            f"Silakan scan QR Code di bawah ini untuk menyelesaikan pembayaran.\n\n"
            f"📦 *Paket:* {package_name}\n"
            f"💰 *Harga:* Rp {price:,}\n\n"
            f"Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )
        
        await query.message.reply_photo(photo=img_buffer, caption=caption, parse_mode='Markdown')
        
        # Edit pesan sebelumnya
        await query.message.edit_text(
            "✅ QR Code pembayaran telah dikirim!\n"
            "Silakan scan QR Code yang dikirim di atas untuk menyelesaikan pembayaran.\n\n"
            "Setelah pembayaran berhasil, paket akan otomatis masuk ke akun Anda."
        )
        
        # Reset state pembelian
        if 'selected_package' in context.user_
            del context.user_data['selected_package']
            
    except Exception as e:
        logger.error(f"Error processing QRIS payment for family package: {e}", exc_info=True)
        await query.message.edit_text(
            "❌ Terjadi kesalahan saat memproses pembayaran QRIS.\n"
            "Silakan coba lagi atau hubungi administrator jika masalah berlanjut."
        )

# === INFORMASI AKUN ===

async def show_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display account information"""
    query = update.callback_query
    await query.answer()
    
    try:
        tokens = AuthInstance.get_active_tokens()
        if not tokens:
            await query.message.edit_text("❌ Tidak ada akun aktif. Silakan login terlebih dahulu.")
            return
            
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
        if not balance_
            await query.message.edit_text("❌ Gagal mengambil data saldo.")
            return
            
        remaining = balance_data.get("remaining", 0)
        expired_at = balance_data.get("expired_at", "N/A")
        
        message = (
            f"👤 *Informasi Akun MyXL*\n\n"
            f"📱 *Nomor:* {msisdn}\n"
            f"💰 *Pulsa:* Rp {remaining:,}\n"
            f"📅 *Masa Aktif:* {expired_at}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error showing account info: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan saat mengambil informasi akun.")

# === HANDLER CALLBACK ===

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani semua callback dari tombol"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    logger.info(f"User {query.from_user.id} pressed button: {data}")
    
    try:
        # Menu Utama
        if data == 'main_menu':
            await show_main_menu(update, context)
            
        # Login & Ganti Akun
        elif data == 'login_menu':
            await show_login_menu(update, context)
        elif data == 'request_otp':
            await request_otp_step(update, context)
        elif data.startswith('switch_account_'):
            try:
                index = int(data.split('_')[2])
                await switch_account(update, context, index)
            except (ValueError, IndexError):
                await query.message.edit_text("❌ Data akun tidak valid.")
        elif data == 'delete_active_account':
            await delete_active_account(update, context)
        elif data.startswith('confirm_delete_'):
            try:
                number = int(data.split('_')[2])
                await confirm_delete_account(update, context, number)
            except (ValueError, IndexError):
                await query.message.edit_text("❌ Data akun tidak valid.")
            
        # Lihat Paket Saya
        elif data == 'view_packages':
            await view_packages(update, context)
            
        # Beli Paket XUT
        elif data == 'buy_xut':
            await buy_xut_packages(update, context)
        elif data.startswith('xut_select_'):
            await show_xut_package_details(update, context)
        elif data == 'buy_xut_pulsa':
            await buy_xut_with_pulsa(update, context)
        elif data == 'buy_xut_ewallet':
            await buy_xut_with_ewallet(update, context)
        elif data == 'buy_xut_qris':
            await buy_xut_with_qris(update, context)
            
        # Beli Paket XUT Vidio Direct
        elif data == 'buy_xut_vidio_direct_start':
            await buy_xut_vidio_direct_start(update, context)
        elif data in ['buy_xut_vidio_direct_pulsa', 'buy_xut_vidio_direct_ewallet', 'buy_xut_vidio_direct_qris']:
            await handle_xut_vidio_direct_payment_choice(update, context)
            
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
            
    except Exception as e:
        logger.error(f"Error in button handler: {e}", exc_info=True)
        await query.message.edit_text("❌ Terjadi kesalahan yang tidak terduga. Silakan coba lagi.")

# === MAIN FUNCTION ===

def main() -> None:
    """Menjalankan bot"""
    logger.info("Starting MyXL Telegram Bot...")
    
    try:
        # Buat aplikasi Telegram
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Tambahkan handler
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("menu", menu_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        # Handler untuk input nomor telepon (628...)
        application.add_handler(MessageHandler(filters.Regex(r'^628\d{8,12}$') & ~filters.COMMAND, handle_phone_number_input), group=1)
        # Handler untuk input OTP (6 digit)
        application.add_handler(MessageHandler(filters.Regex(r'^\d{6}$') & ~filters.COMMAND, handle_otp_input), group=2)
        # Handler untuk input Family Code
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_family_code_input), group=3)
        # Handler untuk input nomor tujuan XUT Vidio direct QRIS
        application.add_handler(MessageHandler(filters.Regex(r'^628\d{8,12}$') & ~filters.COMMAND, handle_target_number_for_xut_vidio_direct_input), group=4)
        # Handler untuk input nomor telepon untuk ganti akun cepat
        application.add_handler(MessageHandler(filters.Regex(r'^628\d{8,12}$') & ~filters.COMMAND, handle_switch_account_by_number), group=5)

        # Jalankan bot
        logger.info("Bot is running...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"Critical error in main(): {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()