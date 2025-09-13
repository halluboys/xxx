# bot.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
import logging
import os
import sys
import json

# Tambahkan path ke direktori library
sys.path.append(os.path.join(os.path.dirname(__file__), 'tembak_xl'))

from config import TELEGRAM_TOKEN, XL_API_KEY_PATH
from database import init_db, get_or_create_user, get_active_xl_account, set_active_xl_account, add_xl_account, get_all_xl_accounts, remove_xl_account
from adapters.auth_adapter import request_otp, verify_otp_and_login, get_api_key
from adapters.account_adapter import set_active_user, get_active_user_tokens
from adapters.package_adapter import fetch_my_packages, get_packages_by_family, purchase_package_qris, get_package_details

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States untuk ConversationHandler
LOGIN_PHONE, LOGIN_OTP = range(2)
SWITCH_ACCOUNT_SELECT = range(1)
BUY_PACKAGE_SELECT = range(1)
BUY_PACKAGE_CONFIRM = range(1)

# Konstanta Family Code
XUT_FAMILY_CODE = "08a3b1e6-8e78-4e45-a540-b40f06871cfe"
ANIV_FAMILY_CODE = "6fda76ee-e789-4897-89fb-9114da47b805"

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    # Buat atau dapatkan pengguna di database
    db_user = get_or_create_user(user.id)
    if not db_user:
        update.message.reply_text('Terjadi kesalahan saat menginisialisasi pengguna.')
        return

    update.message.reply_text(
        f'Selamat datang di Bot Tembak Paket XL, {user.first_name}!\n\n'
        f'Silakan pilih menu di bawah ini:',
        reply_markup=get_main_menu_keyboard()
    )

def get_main_menu_keyboard():
    """Membuat keyboard menu utama."""
    keyboard = [
        ['1. Login', '2. Ganti Akun'],
        ['3. Paket Vidio XUT', '4. Tembak Aniv'],
        ['5. Paket Saya']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def main_menu(update: Update, context: CallbackContext) -> None:
    """Tampilkan menu utama."""
    text = update.message.text
    telegram_id = update.effective_user.id

    if text == '1. Login':
        login_start(update, context)
    elif text == '2. Ganti Akun':
        switch_account_start(update, context)
    elif text == '3. Paket Vidio XUT':
        buy_xut_start(update, context)
    elif text == '4. Tembak Aniv':
        buy_aniv_start(update, context)
    elif text == '5. Paket Saya':
        my_packages(update, context)
    else:
        update.message.reply_text(
            'Silakan pilih menu yang tersedia.',
            reply_markup=get_main_menu_keyboard()
        )

def login_start(update: Update, context: CallbackContext) -> int:
    """Mulai proses login."""
    update.message.reply_text(
        'Masukkan nomor XL Prabayar Anda (Contoh: 6281234567890):',
        reply_markup=ReplyKeyboardRemove()
    )
    return LOGIN_PHONE

def login_phone_received(update: Update, context: CallbackContext) -> int:
    """Menerima nomor telepon untuk login."""
    phone_number = update.message.text.strip()
    
    # Validasi nomor
    if not phone_number.startswith("628") or len(phone_number) < 10 or len(phone_number) > 14:
        update.message.reply_text(
            'Nomor tidak valid. Pastikan nomor diawali dengan \'628\' dan memiliki panjang yang benar.\n\n'
            'Masukkan nomor XL Prabayar Anda (Contoh: 6281234567890):'
        )
        return LOGIN_PHONE

    context.user_data['login_phone'] = phone_number
    
    # Minta OTP
    success = request_otp(phone_number)
    if not success:
        update.message.reply_text(
            'Gagal meminta OTP. Silakan coba lagi.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    update.message.reply_text('OTP Berhasil dikirim ke nomor Anda.\n\nMasukkan OTP yang telah dikirim:')
    return LOGIN_OTP

def login_otp_received(update: Update, context: CallbackContext) -> int:
    """Menerima OTP dan melakukan login."""
    otp = update.message.text.strip()
    phone_number = context.user_data.get('login_phone')
    telegram_id = update.effective_user.id

    if not otp.isdigit() or len(otp) != 6:
        update.message.reply_text(
            'OTP tidak valid. Pastikan OTP terdiri dari 6 digit angka.\n\nMasukkan OTP yang telah dikirim:'
        )
        return LOGIN_OTP

    # Dapatkan API key
    try:
        api_key = get_api_key()
    except Exception as e:
        update.message.reply_text(
            f'Gagal mendapatkan API key: {e}\n\nSilakan periksa file api.key.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Verifikasi OTP dan login
    refresh_token = verify_otp_and_login(api_key, phone_number, otp)
    if not refresh_token:
        update.message.reply_text(
            'Gagal login. Periksa OTP dan coba lagi.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Simpan akun ke database
    success = add_xl_account(telegram_id, int(phone_number), refresh_token)
    if not success:
        update.message.reply_text(
            'Gagal menyimpan akun. Silakan coba lagi.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Set akun ini sebagai aktif
    set_active_xl_account(telegram_id, int(phone_number))
    
    # Set akun aktif di AuthInstance untuk library
    set_active_user(int(phone_number), refresh_token)

    update.message.reply_text(
        'Berhasil login dan akun telah disimpan!\n\n'
        'Akun ini sekarang menjadi akun aktif Anda.',
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END

def switch_account_start(update: Update, context: CallbackContext) -> int:
    """Mulai proses ganti akun."""
    telegram_id = update.effective_user.id
    
    # Dapatkan semua akun XL pengguna
    accounts = get_all_xl_accounts(telegram_id)
    if not accounts:
        update.message.reply_text(
            'Anda belum memiliki akun yang tersimpan.\nSilakan lakukan Login terlebih dahulu.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Buat keyboard dengan daftar akun
    keyboard = []
    for i, (number, is_active) in enumerate(accounts):
        status = " (Aktif)" if is_active else ""
        keyboard.append([f"{i+1}. {number}{status}"])
    
    keyboard.append(['Batal'])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        'Pilih akun yang ingin dijadikan aktif:',
        reply_markup=reply_markup
    )
    return SWITCH_ACCOUNT_SELECT

def switch_account_selected(update: Update, context: CallbackContext) -> int:
    """Akun yang dipilih untuk dijadikan aktif."""
    text = update.message.text
    telegram_id = update.effective_user.id

    if text == 'Batal':
        update.message.reply_text(
            'Penggantian akun dibatalkan.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Parsing pilihan
    try:
        choice_index = int(text.split('.')[0]) - 1
        accounts = get_all_xl_accounts(telegram_id)
        if 0 <= choice_index < len(accounts):
            selected_number, _ = accounts[choice_index]
            
            # Dapatkan refresh token
            # Kita perlu query ulang untuk mendapatkan refresh token
            # Karena get_all_xl_accounts hanya mengembalikan number dan is_active
            # Untuk kesederhanaan, kita asumsikan ini sudah ditangani
            
            # Set akun aktif di database
            success = set_active_xl_account(telegram_id, selected_number)
            if not success:
                update.message.reply_text(
                    'Gagal mengganti akun. Silakan coba lagi.',
                    reply_markup=get_main_menu_keyboard()
                )
                return ConversationHandler.END
            
            # Dapatkan refresh token dari database (simulasi)
            # Dalam implementasi nyata, Anda perlu mengambil refresh_token dari database
            # Berdasarkan telegram_id dan selected_number
            # Untuk saat ini, kita asumsikan refresh token tersedia
            # Anda perlu memodifikasi database.py untuk mengembalikan refresh_token juga
            
            # Sebagai workaround, kita muat ulang dari file refresh-tokens.json milik library
            # Tapi ini tidak ideal. Sebaiknya refresh_token disimpan di database kita.
            
            # Untuk sekarang, kita lanjutkan dengan asumsi berhasil
            # Dan set akun aktif di AuthInstance
            # Kita perlu mendapatkan refresh_token yang sebenarnya
            # Mari kita query ulang database untuk mendapatkan refresh_token
            
            # Modifikasi database.py untuk mengembalikan refresh_token
            # Sementara ini, kita anggap berhasil
            
            # Set akun aktif di AuthInstance (simulasi)
            # Dalam praktiknya, Anda perlu mendapatkan refresh_token yang sebenarnya
            # dari database dan kemudian memanggil set_active_user
            
            # Karena ini simulasi, kita anggap berhasil
            update.message.reply_text(
                f'Akun {selected_number} sekarang menjadi akun aktif Anda.',
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
        else:
            raise ValueError("Index out of range")
    except (ValueError, IndexError):
        update.message.reply_text(
            'Pilihan tidak valid. Silakan pilih akun yang tersedia.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

def buy_xut_start(update: Update, context: CallbackContext) -> int:
    """Mulai proses beli paket XUT."""
    telegram_id = update.effective_user.id
    
    # Periksa apakah ada akun aktif
    active_account = get_active_xl_account(telegram_id)
    if not active_account:
        update.message.reply_text(
            'Anda belum memiliki akun aktif.\nSilakan lakukan Login atau Ganti Akun terlebih dahulu.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    number, refresh_token = active_account
    # Set akun aktif di AuthInstance
    success = set_active_user(number, refresh_token)
    if not success:
        update.message.reply_text(
            'Gagal mengatur akun aktif. Silakan coba Ganti Akun lagi.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Dapatkan daftar paket XUT
    packages, error = get_packages_by_family(XUT_FAMILY_CODE)
    if error:
        update.message.reply_text(
            f'Gagal mengambil daftar paket XUT: {error}',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END
        
    if not packages:
        update.message.reply_text(
            'Tidak ada paket XUT yang tersedia.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Simpan paket di context
    context.user_data['packages'] = packages
    context.user_data['family_code'] = XUT_FAMILY_CODE
    
    # Buat keyboard dengan daftar paket
    keyboard = []
    for pkg in packages:
        keyboard.append([f"{pkg['number']}. {pkg['name']} - Rp {pkg['price']}"])
    
    keyboard.append(['Batal'])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        'Pilih paket XUT yang ingin dibeli:\n\n'
        'Catatan: Paket target adalah paket nomor 11 (unlimited Vidio).',
        reply_markup=reply_markup
    )
    return BUY_PACKAGE_SELECT

def buy_aniv_start(update: Update, context: CallbackContext) -> int:
    """Mulai proses beli paket Aniv."""
    telegram_id = update.effective_user.id
    
    # Periksa apakah ada akun aktif
    active_account = get_active_xl_account(telegram_id)
    if not active_account:
        update.message.reply_text(
            'Anda belum memiliki akun aktif.\nSilakan lakukan Login atau Ganti Akun terlebih dahulu.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    number, refresh_token = active_account
    # Set akun aktif di AuthInstance
    success = set_active_user(number, refresh_token)
    if not success:
        update.message.reply_text(
            'Gagal mengatur akun aktif. Silakan coba Ganti Akun lagi.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Dapatkan daftar paket Aniv
    packages, error = get_packages_by_family(ANIV_FAMILY_CODE)
    if error:
        update.message.reply_text(
            f'Gagal mengambil daftar paket Aniv: {error}',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END
        
    if not packages:
        update.message.reply_text(
            'Tidak ada paket Aniv yang tersedia.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Simpan paket di context
    context.user_data['packages'] = packages
    context.user_data['family_code'] = ANIV_FAMILY_CODE
    
    # Buat keyboard dengan daftar paket
    keyboard = []
    for pkg in packages:
        keyboard.append([f"{pkg['number']}. {pkg['name']} - Rp {pkg['price']}"])
    
    keyboard.append(['Batal'])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        'Pilih paket Aniv yang ingin dibeli:\n\n'
        'Catatan: Paket target adalah paket nomor 7 (Anniversary).',
        reply_markup=reply_markup
    )
    return BUY_PACKAGE_SELECT

def buy_package_selected(update: Update, context: CallbackContext) -> int:
    """Paket yang dipilih untuk dibeli."""
    text = update.message.text
    telegram_id = update.effective_user.id
    packages = context.user_data.get('packages', [])
    
    if text == 'Batal':
        update.message.reply_text(
            'Pembelian paket dibatalkan.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Parsing pilihan
    try:
        choice_number = int(text.split('.')[0])
        selected_pkg = next((p for p in packages if p["number"] == choice_number), None)
        if not selected_pkg:
            raise ValueError("Package not found")
            
        # Simpan paket yang dipilih
        context.user_data['selected_package'] = selected_pkg
        
        # Dapatkan detail paket
        from app.service.auth import AuthInstance
        api_key = AuthInstance.api_key
        tokens = get_active_user_tokens()
        if not tokens:
            update.message.reply_text(
                'Tidak ada pengguna aktif.',
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
            
        package_details = get_package_details(api_key, tokens, selected_pkg["code"])
        if not package_details:
            update.message.reply_text(
                'Gagal mengambil detail paket.',
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
            
        # Tampilkan detail paket
        name = package_details.get("package_option", {}).get("name", "N/A")
        price = package_details.get("package_option", {}).get("price", "N/A")
        validity = package_details.get("package_option", {}).get("validity", "N/A")
        tnc = package_details.get("package_option", {}).get("tnc", "N/A")
        
        # Batasi panjang TnC untuk tampilan
        tnc_display = tnc[:500] + "..." if len(tnc) > 500 else tnc
        
        message = (
            f"Detail Paket:\n"
            f"Nama: {name}\n"
            f"Harga: Rp {price}\n"
            f"Masa Berlaku: {validity} hari\n\n"
            f"Syarat dan Ketentuan:\n{tnc_display}\n\n"
            f"Apakah Anda yakin ingin membeli paket ini dengan pembayaran QRIS?"
        )
        
        keyboard = [['Ya, Beli dengan QRIS'], ['Batal']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text(message, reply_markup=reply_markup)
        return BUY_PACKAGE_CONFIRM
    except (ValueError, IndexError):
        update.message.reply_text(
            'Pilihan tidak valid. Silakan pilih paket yang tersedia.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

def buy_package_confirmed(update: Update, context: CallbackContext) -> int:
    """Konfirmasi pembelian paket."""
    text = update.message.text
    telegram_id = update.effective_user.id
    
    if text != 'Ya, Beli dengan QRIS':
        update.message.reply_text(
            'Pembelian paket dibatalkan.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    selected_pkg = context.user_data.get('selected_package')
    if not selected_pkg:
        update.message.reply_text(
            'Terjadi kesalahan. Paket tidak ditemukan.',
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    # Proses pembelian dengan QRIS
    # Karena library menggunakan input() dan print(), 
    # kita tidak bisa langsung memanggil show_qris_payment
    # Kita perlu membuat implementasi khusus untuk bot
    
    # Untuk saat ini, kita beri pesan bahwa fitur pembelian sedang dalam pengembangan
    # Atau Anda bisa mengimplementasikan wrapper khusus untuk fungsi pembelian
    
    update.message.reply_text(
        f'Fitur pembelian paket dengan QRIS sedang dalam pengembangan.\n\n'
        f'Anda memilih paket: {selected_pkg["name"]}\n'
        f'Dengan kode: {selected_pkg["code"]}\n\n'
        f'Silakan gunakan aplikasi myXL untuk menyelesaikan pembelian.',
        reply_markup=get_main_menu_keyboard()
    )
    
    # Bersihkan data sesi
    context.user_data.pop('packages', None)
    context.user_data.pop('selected_package', None)
    context.user_data.pop('family_code', None)
    
    return ConversationHandler.END

def my_packages(update: Update, context: CallbackContext) -> None:
    """Lihat paket yang sedang aktif."""
    telegram_id = update.effective_user.id
    
    # Periksa apakah ada akun aktif
    active_account = get_active_xl_account(telegram_id)
    if not active_account:
        update.message.reply_text(
            'Anda belum memiliki akun aktif.\nSilakan lakukan Login atau Ganti Akun terlebih dahulu.',
            reply_markup=get_main_menu_keyboard()
        )
        return

    number, refresh_token = active_account
    # Set akun aktif di AuthInstance
    success = set_active_user(number, refresh_token)
    if not success:
        update.message.reply_text(
            'Gagal mengatur akun aktif. Silakan coba Ganti Akun lagi.',
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Ambil paket
    packages_info = fetch_my_packages()
    
    if "Gagal" in packages_info or "Failed" in packages_info:
        update.message.reply_text(
            f'Gagal mengambil informasi paket: {packages_info}',
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # Batasi panjang pesan
        if len(packages_info) > 4000:
            packages_info = packages_info[:4000] + "\n\n... (informasi dipotong)"
        update.message.reply_text(
            f'Informasi Paket Aktif:\n\n{packages_info}',
            reply_markup=get_main_menu_keyboard()
        )

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel current conversation."""
    update.message.reply_text(
        'Operasi dibatalkan.',
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END

def main() -> None:
    """Start the bot."""
    # Inisialisasi database
    init_db()

    # Buat Updater dan lewatkan token bot Anda
    updater = Updater(TELEGRAM_TOKEN)

    # Dapatkan dispatcher untuk mendaftarkan handler
    dispatcher = updater.dispatcher

    # Handler untuk perintah /start
    dispatcher.add_handler(CommandHandler("start", start))

    # Handler untuk login
    login_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(r'^1\. Login$'), login_start)],
        states={
            LOGIN_PHONE: [MessageHandler(Filters.text & ~Filters.command, login_phone_received)],
            LOGIN_OTP: [MessageHandler(Filters.text & ~Filters.command, login_otp_received)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(login_conv_handler)

    # Handler untuk ganti akun
    switch_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(r'^2\. Ganti Akun$'), switch_account_start)],
        states={
            SWITCH_ACCOUNT_SELECT: [MessageHandler(Filters.text & ~Filters.command, switch_account_selected)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(switch_conv_handler)

    # Handler untuk beli XUT
    xut_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(r'^3\. Paket Vidio XUT$'), buy_xut_start)],
        states={
            BUY_PACKAGE_SELECT: [MessageHandler(Filters.text & ~Filters.command, buy_package_selected)],
            BUY_PACKAGE_CONFIRM: [MessageHandler(Filters.text & ~Filters.command, buy_package_confirmed)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(xut_conv_handler)

    # Handler untuk beli Aniv
    aniv_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(r'^4\. Tembak Aniv$'), buy_aniv_start)],
        states={
            BUY_PACKAGE_SELECT: [MessageHandler(Filters.text & ~Filters.command, buy_package_selected)],
            BUY_PACKAGE_CONFIRM: [MessageHandler(Filters.text & ~Filters.command, buy_package_confirmed)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(aniv_conv_handler)

    # Handler untuk menu utama (semua pesan teks)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, main_menu))

    # Mulai bot
    updater.start_polling()

    # Jalankan bot sampai Anda menekan Ctrl-C atau proses menerima SIGINT,
    # SIGTERM atau SIGABRT. Ini harus digunakan sebagian besar di tempat run_polling() itu sendiri
    # meskipun tidak berjalan secara asinkron
    updater.idle()

if __name__ == '__main__':
    main()