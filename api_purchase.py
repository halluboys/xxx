import os, json, uuid, requests, time
from datetime import datetime, timezone, timedelta

from crypto_helper import encryptsign_xdata, java_like_timestamp, ts_gmt7_without_colon, ax_api_signature, decrypt_xdata, API_KEY, get_x_signature_payment, build_encrypted_field, load_ax_fp

BASE_API_URL = os.getenv("BASE_API_URL")
BASE_CIAM_URL = os.getenv("BASE_CIAM_URL")
if not BASE_API_URL or not BASE_CIAM_URL:
    raise ValueError("BASE_API_URL or BASE_CIAM_URL environment variable not set")

GET_OTP_URL = BASE_CIAM_URL + "/realms/xl-ciam/auth/otp"
BASIC_AUTH = os.getenv("BASIC_AUTH")
AX_DEVICE_ID = os.getenv("AX_DEVICE_ID")
AX_FP = load_ax_fp()
SUBMIT_OTP_URL = BASE_CIAM_URL + "/realms/xl-ciam/protocol/openid-connect/token"
UA = os.getenv("UA")

def validate_contact(contact: str) -> bool:
    if not contact.startswith("628") or len(contact) > 14:
        print("Invalid number")
        return False
    return True

def get_otp(contact: str) -> str:
    # Contact example: "6287896089467"
    if not validate_contact(contact):
        return None
    
    url = GET_OTP_URL

    querystring = {
        "contact": contact,
        "contactType": "SMS",
        "alternateContact": "false"
    }
    
    now = datetime.now(timezone(timedelta(hours=7)))
    ax_request_at = java_like_timestamp(now)  # format: "2023-10-20T12:34:56.78+07:00"
    ax_request_id = str(uuid.uuid4())

    payload = ""
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": f"Basic {BASIC_AUTH}",
        "Ax-Device-Id": AX_DEVICE_ID,
        "Ax-Fingerprint": AX_FP,
        "Ax-Request-At": ax_request_at,
        "Ax-Request-Device": "samsung",
        "Ax-Request-Device-Model": "SM-N935F",
        "Ax-Request-Id": ax_request_id,
        "Ax-Substype": "PREPAID",
        "Content-Type": "application/json",
        "Host": BASE_CIAM_URL.replace("https://", ""),
        "User-Agent": UA,
    }

    print("Requesting OTP...")
    try:
        response = requests.request("GET", url, data=payload, headers=headers, params=querystring, timeout=30)
        print("response body", response.text)
        json_body = json.loads(response.text)
    
        if "subscriber_id" not in json_body:
            print(json_body.get("error", "No error message in response"))
            raise ValueError("Subscriber ID not found in response")
        
        return json_body["subscriber_id"]
    except Exception as e:
        print(f"Error requesting OTP: {e}")
        return None
    
def submit_otp(api_key: str, contact: str, code: str):
    if not validate_contact(contact):
        print("Invalid number")
        return None
    
    if not code or len(code) != 6:
        print("Invalid OTP code format")
        return None
    
    url = SUBMIT_OTP_URL

    now_gmt7 = datetime.now(timezone(timedelta(hours=7)))
    ts_for_sign = ts_gmt7_without_colon(now_gmt7)
    ts_header = ts_gmt7_without_colon(now_gmt7 - timedelta(minutes=5))
    signature = ax_api_signature(api_key, ts_for_sign, contact, code, "SMS")

    payload = f"contactType=SMS&code={code}&grant_type=password&contact={contact}&scope=openid"

    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": f"Basic {BASIC_AUTH}",
        "Ax-Api-Signature": signature,
        "Ax-Device-Id": AX_DEVICE_ID,
        "Ax-Fingerprint": AX_FP,
        "Ax-Request-At": ts_header,
        "Ax-Request-Device": "samsung",
        "Ax-Request-Device-Model": "SM-N935F",
        "Ax-Request-Id": str(uuid.uuid4()),
        "Ax-Substype": "PREPAID",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": UA,
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        json_body = json.loads(response.text)
        
        if "error" in json_body:
            print(f"[Error submit_otp]: {json_body['error_description']}")
            return None
        
        print("Login successful.")
        return json_body
    except requests.RequestException as e:
        print(f"[Error submit_otp]: {e}")
        return None

def save_tokens(tokens: dict, filename: str = "tokens.json"):
    with open(filename, 'w') as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)
        
def load_tokens(filename: str = "tokens.json") -> dict:
    try:
        with open(filename, 'r') as f:
            tokens = json.load(f)
            if not isinstance(tokens, dict) or "refresh_token" not in tokens or "id_token" not in tokens:
                raise ValueError("Invalid token format in file")
            return tokens
            
    except FileNotFoundError:
        print(f"File {filename} not found. Returning empty tokens.")
        return {}

def get_new_token(refresh_token: str) -> str:
    url = SUBMIT_OTP_URL

    now = datetime.now(timezone(timedelta(hours=7)))  # GMT+7
    ax_request_at = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0700"
    ax_request_id = str(uuid.uuid4())

    headers = {
        "Host": BASE_CIAM_URL.replace("https://", ""),
        "ax-request-at": ax_request_at,
        "ax-device-id": AX_DEVICE_ID,
        "ax-request-id": ax_request_id,
        "ax-request-device": "samsung",
        "ax-request-device-model": "SM-N935F",
        "ax-fingerprint": AX_FP,
        "authorization": f"Basic {BASIC_AUTH}",
        "user-agent": UA,
        "ax-substype": "PREPAID",
        "content-type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    resp = requests.post(url, headers=headers, data=data, timeout=30)
    if resp.status_code == 400:
        if resp.json().get("error_description") == "Session not active":
            print("Refresh token expired. Pleas remove and re-add the account.")
            return None
        
    resp.raise_for_status()

    body = resp.json()
    
    if "id_token" not in body:
        raise ValueError("ID token not found in response")
    if "error" in body:
        raise ValueError(f"Error in response: {body['error']} - {body.get('error_description', '')}")
    
    return body

def send_api_request(
    api_key: str,
    path: str,
    payload_dict: dict,
    id_token: str,
    method: str = "POST",
):
    encrypted_payload = encryptsign_xdata(
        api_key=api_key,
        method=method,
        path=path,
        id_token=id_token,
        payload=payload_dict
    )
    
    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    
    now = datetime.now(timezone.utc).astimezone()
    sig_time_sec = (xtime // 1000)

    body = encrypted_payload["encrypted_body"]
    x_sig = encrypted_payload["x_signature"]
    
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {id_token}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(now),
        "x-version-app": "8.6.0",
    }

    url = f"{BASE_API_URL}/{path}"
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)

    try:
        decrypted_body = decrypt_xdata(api_key, json.loads(resp.text))
        return decrypted_body
    except Exception as e:
        print("[decrypt err]", e)
        return resp.text

def get_profile(api_key: str, access_token: str, id_token: str) -> dict:
    path = "api/v8/profile"

    raw_payload = {
        "access_token": access_token,
        "app_version": "8.6.0",
        "is_enterprise": False,
        "lang": "en"
    }

    print("Fetching profile...")
    res = send_api_request(api_key, path, raw_payload, id_token, "POST")

    return res.get("data")

def get_balance(api_key: str, id_token: str) -> dict:
    path = "api/v8/packages/balance-and-credit"
    
    raw_payload = {
        "is_enterprise": False,
        "lang": "en"
    }
    
    print("Fetching balance...")
    res = send_api_request(api_key, path, raw_payload, id_token, "POST")
    
    if "data" in res:
        if "balance" in res["data"]:
            return res["data"]["balance"]
    else:
        print("Error getting balance:", res.get("error", "Unknown error"))
        return None
    
def get_family(api_key: str, tokens: dict, family_code: str, is_enterprise: bool = False) -> dict:
    print("Fetching package family...")
    path = "api/v8/xl-stores/options/list"
    id_token = tokens.get("id_token")
    payload_dict = {
        "is_show_tagging_tab": True,
        "is_dedicated_event": True,
        "is_transaction_routine": False,
        "migration_type": "NONE",
        "package_family_code": family_code,
        "is_autobuy": False,
        "is_enterprise": is_enterprise,
        "is_pdlp": True,
        "referral_code": "",
        "is_migration": False,
        "lang": "en"
    }
    
    res = send_api_request(api_key, path, payload_dict, id_token, "POST")
    if res.get("status") != "SUCCESS":
        print(f"Failed to get family {family_code}")
        print(json.dumps(res, indent=2))
        input("Press Enter to continue...")
        return None
    
    return res["data"]

def get_families(api_key: str, tokens: dict, package_category_code: str) -> dict:
    print("Fetching families...")
    path = "api/v8/xl-stores/families"
    payload_dict = {
        "migration_type": "",
        "is_enterprise": False,
        "is_shareable": False,
        "package_category_code": package_category_code,
        "with_icon_url": True,
        "is_migration": False,
        "lang": "en"
    }
    
    res = send_api_request(api_key, path, payload_dict, tokens["id_token"], "POST")
    if res.get("status") != "SUCCESS":
        print(f"Failed to get families for category {package_category_code}")
        print(f"Res:{res}")
        print(json.dumps(res, indent=2))
        input("Press Enter to continue...")
        return None
    return res["data"]

def get_package(api_key: str, tokens: dict, package_option_code: str) -> dict:
    path = "api/v8/xl-stores/options/detail"
    
    raw_payload = {
        "is_transaction_routine": False,
        "migration_type": "NONE",
        "package_family_code": "",
        "family_role_hub": "",
        "is_autobuy": False,
        "is_enterprise": False,
        "is_shareable": False,
        "is_migration": False,
        "lang": "en",
        "package_option_code": package_option_code,
        "is_upsell_pdp": False,
        "package_variant_code": ""
    }
    
    print("Fetching package...")
    res = send_api_request(api_key, path, raw_payload, tokens["id_token"], "POST")
    
    if "data" not in res:
        print("Error getting package:", res.get("error", "Unknown error"))
        return None
        
    return res["data"]

def get_addons(api_key: str, tokens: dict, package_option_code: str) -> dict:
    path = "api/v8/xl-stores/options/addons-pinky-box"
    
    raw_payload = {
        "is_enterprise": False,
        "lang": "en",
        "package_option_code": package_option_code
    }
    
    print("Fetching addons...")
    res = send_api_request(api_key, path, raw_payload, tokens["id_token"], "POST")
    
    if "data" not in res:
        print("Error getting addons:", res.get("error", "Unknown error"))
        return None
        
    return res["data"]

def send_payment_request(
    api_key: str,
    payload_dict: dict,
    access_token: str,
    id_token: str,
    token_payment: str,
    ts_to_sign: int,
):
    path = "payments/api/v8/settlement-balance"
    package_code = payload_dict["items"][0]["item_code"]
    
    encrypted_payload = encryptsign_xdata(
        api_key=api_key,
        method="POST",
        path=path,
        id_token=id_token,
        payload=payload_dict
    )
    
    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = (xtime // 1000)
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
    payload_dict["timestamp"] = ts_to_sign
    
    body = encrypted_payload["encrypted_body"]
    
    x_sig = get_x_signature_payment(
        api_key,
        access_token,
        ts_to_sign,
        package_code,
        token_payment,
        "BALANCE"
    )
    
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {id_token}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }
    
    url = f"{BASE_API_URL}/{path}"
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    
    try:
        decrypted_body = decrypt_xdata(api_key, json.loads(resp.text))
        return decrypted_body
    except Exception as e:
        print("[decrypt err]", e)
        return resp.text
        
def settlement_qris(
    api_key: str,
    tokens: dict,
    token_payment: str,
    ts_to_sign: int,
    payment_target: str,
    price: int,
    item_name: str = "",
    force_amount: bool = False   # << tambahan untuk overwrite khusus
):  
    """
    Membuat settlement QRIS untuk pembayaran paket.
    - price: harga asli dari API
    - force_amount=True -> pakai price sebagai nominal overwrite (contoh: Aniv 500)
    """

    # Default: harga dari API
    amount_int = price

    # Kalau force_amount=True, pakai harga yang dikirim caller (misalnya 500)
    if force_amount:
        amount_int = price

    # Payload settlement
    path = "payments/api/v8/settlement-multipayment/qris"
    settlement_payload = {
        "akrab": {
            "akrab_members": [],
            "akrab_parent_alias": "",
            "members": []
        },
        "can_trigger_rating": False,
        "total_discount": 0,
        "coupon": "",
        "payment_for": "BUY_PACKAGE",
        "topup_number": "",
        "is_enterprise": False,
        "autobuy": {
            "is_using_autobuy": False,
            "activated_autobuy_code": "",
            "autobuy_threshold_setting": {
                "label": "",
                "type": "",
                "value": 0
            }
        },
        "access_token": tokens["access_token"],
        "is_myxl_wallet": False,
        "additional_data": {
            "original_price": amount_int if force_amount else price,  # fix
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
        "total_amount": amount_int,
        "total_fee": 0,
        "is_use_point": False,
        "lang": "en",
        "items": [{
            "item_code": payment_target,
            "product_type": "",
            "item_price": amount_int if force_amount else price,  # fix
            "item_name": item_name,
            "tax": 0
        }],
        "verification_token": token_payment,
        "payment_method": "QRIS",
        "timestamp": int(time.time())
    }

    # === sisanya biarkan sama (encryptsign_xdata, header, request, decrypt) ===
    encrypted_payload = encryptsign_xdata(
        api_key=api_key,
        method="POST",
        path=path,
        id_token=tokens["id_token"],
        payload=settlement_payload
    )
    
    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = (xtime // 1000)
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
    settlement_payload["timestamp"] = ts_to_sign
    
    body = encrypted_payload["encrypted_body"]
    x_sig = get_x_signature_payment(
            api_key,
            tokens["access_token"],
            ts_to_sign,
            payment_target,
            token_payment,
            "QRIS"
        )
    
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }
    
    url = f"{BASE_API_URL}/{path}"
    print("Sending settlement request...")
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    
    try:
        decrypted_body = decrypt_xdata(api_key, json.loads(resp.text))
        if decrypted_body["status"] != "SUCCESS":
            print("Failed to initiate settlement.")
            print(f"Error: {decrypted_body}")
            return None
        
        transaction_id = decrypted_body["data"]["transaction_code"]
        return transaction_id
    except Exception as e:
        print("[decrypt err]", e)
        return resp.text

def purchase_package(api_key: str, tokens: dict, package_option_code: str) -> dict:
    package_details_data = get_package(api_key, tokens, package_option_code)
    if not package_details_data:
        print("Failed to get package details for purchase.")
        return None
    
    token_confirmation = package_details_data["token_confirmation"]
    payment_target = package_details_data["package_option"]["package_option_code"]
    
    variant_name = package_details_data["package_detail_variant"].get("name", "")
    option_name = package_details_data["package_option"].get("name", "")
    item_name = f"{variant_name} {option_name}".strip()
    
    price = package_details_data["package_option"]["price"]
    amount_str = input(f"Total amount is {price}.\nEnter value if you need to overwrite, press enter to ignore & use default amount: ")
    amount_int = price
    
    if amount_str != "":
        try:
            amount_int = int(amount_str)
        except ValueError:
            print("Invalid overwrite input, using original price.")
            return None
    
    payment_path = "payments/api/v8/payment-methods-option"
    payment_payload = {
        "payment_type": "PURCHASE",
        "is_enterprise": False,
        "payment_target": payment_target,
        "lang": "en",
        "is_referral": False,
        "token_confirmation": token_confirmation
    }
    
    print("Initiating payment...")
    payment_res = send_api_request(api_key, payment_path, payment_payload, tokens["id_token"], "POST")
    if payment_res.get("status") != "SUCCESS":
        print("Failed to initiate payment")
        print(json.dumps(payment_res, indent=2))
        input("Press Enter to continue...")
        return None
    
    token_payment = payment_res["data"]["token_payment"]
    ts_to_sign = payment_res["data"]["timestamp"]
    
    # Settlement request
    settlement_payload = {
        "total_discount": 0,
        "is_enterprise": False,
        "payment_token": "",
        "token_payment": token_payment,
        "activated_autobuy_code": "",
        "cc_payment_type": "",
        "is_myxl_wallet": False,
        "pin": "",
        "ewallet_promo_id": "",
        "members": [],
        "total_fee": 0,
        "fingerprint": "",
        "autobuy_threshold_setting": {
            "label": "",
            "type": "",
            "value": 0
        },
        "is_use_point": False,
        "lang": "en",
        "payment_method": "BALANCE",
        "timestamp": int(time.time()),
        "points_gained": 0,
        "can_trigger_rating": False,
        "akrab_members": [],
        "akrab_parent_alias": "",
        "referral_unique_code": "",
        "coupon": "",
        "payment_for": "BUY_PACKAGE",
        "with_upsell": False,
        "topup_number": "",
        "stage_token": "",
        "authentication_id": "",
        "encrypted_payment_token": build_encrypted_field(urlsafe_b64=True),
        "token": "",
        "token_confirmation": "",
        "access_token": tokens["access_token"],
        "wallet_number": "",
        "encrypted_authentication_id": build_encrypted_field(urlsafe_b64=True),
        "additional_data": {},
        "total_amount": amount_int,
        "is_using_autobuy": False,
        "items": [{
            "item_code": payment_target,
            "product_type": "",
            "item_price": price,
            "item_name": item_name,
            "tax": 0
        }]
    }
    
    print("Processing purchase...")
    # print(f"settlement payload:\n{json.dumps(settlement_payload, indent=2)}")
    purchase_result = send_payment_request(api_key, settlement_payload, tokens["access_token"], tokens["id_token"], token_payment, ts_to_sign)
    
    print(f"Purchase result:\n{json.dumps(purchase_result, indent=2)}")
    
    input("Press Enter to continue...")