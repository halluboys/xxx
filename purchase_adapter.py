# adapters/purchase_adapter.py
import sys
import os
import qrcode
import base64
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tembak_xl'))

from app.client.engsel import get_package, get_family
from app.client.purchase import get_payment_methods, settlement_qris, get_qris_code
from app.service.auth import AuthInstance

def get_package_details(api_key, tokens, package_option_code):
    """dapatkan detail paket (wrapper untuk fungsi asli)"""
    try:
        return get_package(api_key, tokens, package_option_code)
    except Exception as e:
        print(f"[get_package_details] error: {e}")
        return None

def get_family_packages(family_code: str, is_enterprise: bool = false):
    """dapatkan daftar paket berdasarkan family code (wrapper untuk fungsi asli)"""
    try:
        api_key = authinstance.api_key
        tokens = authinstance.get_active_tokens()
        if not tokens:
            return none, "tidak ada pengguna aktif."
        data = get_family(api_key, tokens, family_code, is_enterprise)
        return data, none
    except exception as e:
        print(f"[get_family_packages] error: {e}")
        return none, str(e)

def purchase_package_qris_auto(package_option_code: str, fixed_price: int = none):
    """
    pembelian paket otomatis dengan qris
    - package_option_code: kode paket yang akan dibeli
    - fixed_price: harga tetap (jika none, gunakan harga default dari paket)
    """
    try:
        # 1. dapatkan token pengguna aktif
        api_key = authinstance.api_key
        tokens = authinstance.get_active_tokens()
        if not tokens:
            return false, "tidak ada pengguna aktif."

        # 2. dapatkan detail paket untuk informasi harga default
        package_details = get_package_details(api_key, tokens, package_option_code)
        if not package_details:
            return false, "gagal mengambil detail paket."

        # 3. tentukan harga yang akan digunakan
        default_price = package_details["package_option"]["price"]
        price_to_use = fixed_price if fixed_price is not none else default_price
        item_name = f"{package_details.get('package_detail_variant', {}).get('name', '')} {package_details.get('package_option', {}).get('name', '')}".strip()

        print(f"[purchase_adapter] membeli paket '{item_name}' (kode: {package_option_code}) dengan harga {price_to_use}")

        # 4. dapatkan metode pembayaran (token_payment & timestamp)
        payment_methods_data = get_payment_methods(
            api_key=api_key,
            tokens=tokens,
            token_confirmation=package_details["token_confirmation"],
            payment_target=package_option_code
        )
        token_payment = payment_methods_data["token_payment"]
        ts_to_sign = payment_methods_data["timestamp"]

        # 5. buat transaksi qris
        transaction_id = settlement_qris(
            api_key=api_key,
            tokens=tokens,
            token_payment=token_payment,
            ts_to_sign=ts_to_sign,
            payment_target=package_option_code,
            price=price_to_use,  # <-- harga yang digunakan
            item_name=item_name
        )
        if not transaction_id:
            return false, "gagal membuat transaksi qris."

        # 6. dapatkan kode qris
        qris_code = get_qris_code(api_key, tokens, transaction_id)
        if not qris_code:
            return false, "gagal mendapatkan kode qris."

        # 7. buat url qris untuk ditampilkan di telegram
        qris_b64 = base64.urlsafe_b64encode(qris_code.encode()).decode()
        qris_url = f"https://ki-ar-kod.netlify.app/?data={qris_b64}"

        return true, {
            "item_name": item_name,
            "price": price_to_use,
            "qris_code": qris_code,
            "qris_url": qris_url,
            "transaction_id": transaction_id
        }

    except exception as e:
        print(f"[purchase_package_qris_auto] error: {e}")
        return false, f"terjadi kesalahan saat pembelian: {str(e)}"