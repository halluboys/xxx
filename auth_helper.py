# auth_helper.py
import os
import json
import time
import logging  # Tambahkan logging
from api_request import get_new_token
from util import ensure_api_key

# Konfigurasi logger untuk auth_helper
logger = logging.getLogger(__name__)

class Auth:
    _instance_ = None
    _initialized_ = False
    api_key = ""
    refresh_tokens = []
    # Format of refresh_tokens: [{"number": int, "refresh_token": str}]
    # users = []
    active_user = None
    # Format of active_user: {"number": int, "tokens": {"refresh_token": str, "access_token": str, "id_token": str}}
    last_refresh_time = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance_:
            cls._instance_ = super().__new__(cls)
        return cls._instance_

    def __init__(self):
        if not self._initialized_:
            if os.path.exists("refresh-tokens.json"):
                self.load_tokens()
            else:
                # Create empty file
                try:
                    with open("refresh-tokens.json", "w", encoding="utf-8") as f:
                        json.dump([], f, indent=4)
                    logger.info("Created new refresh-tokens.json file.")
                except Exception as e:
                    logger.error(f"Failed to create refresh-tokens.json: {e}")

            # Select the first user as active user by default
            if self.refresh_tokens: # Gunakan pengecekan idiomatic
                first_rt = self.refresh_tokens[0]
                tokens = get_new_token(first_rt["refresh_token"])
                if tokens:
                    self.active_user = {
                        "number": int(first_rt["number"]),
                        "tokens": tokens
                    }
                    logger.info(f"Set active user to {first_rt['number']} on init.")
                else:
                    logger.warning(f"Failed to get tokens for initial user {first_rt['number']}.")

            self.api_key = ensure_api_key()
            self.last_refresh_time = int(time.time())
            self._initialized_ = True

    def load_tokens(self):
        try:
            with open("refresh-tokens.json", "r", encoding="utf-8") as f:
                refresh_tokens = json.load(f)
            # Validate and load tokens
            self.refresh_tokens = [] # Reset list
            for rt in refresh_tokens:
                if "number" in rt and "refresh_token" in rt:
                    self.refresh_tokens.append(rt)
                else:
                    logger.warning(f"Invalid token entry found and skipped: {rt}")
            logger.info(f"Loaded {len(self.refresh_tokens)} tokens from file.")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from refresh-tokens.json: {e}")
            self.refresh_tokens = []
        except Exception as e:
            logger.error(f"Error loading tokens from refresh-tokens.json: {e}")
            self.refresh_tokens = []

    def add_refresh_token(self, number: int, refresh_token: str):
        try:
            # Check if number already exist, if yes, replace it, if not append
            existing = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
            if existing:
                existing["refresh_token"] = refresh_token
                logger.info(f"Updated refresh token for number: {number}")
            else:
                self.refresh_tokens.append({
                    "number": int(number),
                    "refresh_token": refresh_token
                })
                logger.info(f"Added new refresh token for number: {number}")

            # Save to file
            with open("refresh-tokens.json", "w", encoding="utf-8") as f:
                json.dump(self.refresh_tokens, f, indent=2) # indent=2 lebih umum
            logger.info("Refresh tokens saved to file.")

            # Set active user to newly added/updated
            self.set_active_user(number)
        except Exception as e:
            logger.error(f"Error adding/saving refresh token for {number}: {e}")

    def remove_refresh_token(self, number: int):
        try:
            original_count = len(self.refresh_tokens)
            self.refresh_tokens = [rt for rt in self.refresh_tokens if rt["number"] != number]
            # self.users = [user for user in self.users if user["number"] != number] # Baris ini tampaknya tidak digunakan

            # Save to file
            with open("refresh-tokens.json", "w", encoding="utf-8") as f:
                json.dump(self.refresh_tokens, f, indent=4)
            logger.info(f"Removed token for number {number}. Tokens left: {len(self.refresh_tokens)}. File saved.")

            # If the removed user was the active user, select a new active user if available
            if self.active_user and self.active_user["number"] == number:
                # Select the first user as active user by default
                if self.refresh_tokens: # Gunakan pengecekan idiomatic
                    first_rt = self.refresh_tokens[0]
                    logger.info(f"Previous active user removed. Attempting to set new active user to {first_rt['number']}.")
                    tokens = get_new_token(first_rt["refresh_token"])
                    if tokens:
                        self.active_user = {
                            "number": int(first_rt["number"]),
                            "tokens": tokens
                        }
                        logger.info(f"New active user set to {first_rt['number']}.")
                    else:
                        logger.warning(f"Failed to get tokens for new active user {first_rt['number']}. Active user is now None.")
                        self.active_user = None
                else:
                    logger.info("No users left after removal. Active user set to None.")
                    self.active_user = None
        except Exception as e:
             logger.error(f"Error removing refresh token for {number}: {e}")

    def set_active_user(self, number: int):
        try:
            # Get refresh token for the number from refresh_tokens
            rt_entry = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
            if not rt_entry:
                logger.warning(f"No refresh token found for number: {number}")
                # Jangan gunakan input()
                return False
            tokens = get_new_token(rt_entry["refresh_token"])
            if not tokens:
                logger.warning(f"Failed to get tokens for number: {number}. The refresh token might be invalid or expired.")
                # Jangan gunakan input()
                return False
            self.active_user = {
                "number": int(number),
                "tokens": tokens
            }
            logger.info(f"Successfully set active user to {number}.")
            return True # Tambahkan return True jika berhasil
        except Exception as e:
            logger.error(f"Error setting active user for {number}: {e}")
            return False # Tambahkan return False jika error

    def renew_active_user_token(self):
        if self.active_user:
            try:
                tokens = get_new_token(self.active_user["tokens"]["refresh_token"])
                if tokens:
                    self.active_user["tokens"] = tokens
                    self.last_refresh_time = int(time.time())
                    # Simpan token yang diperbarui ke file
                    self.add_refresh_token(self.active_user["number"], self.active_user["tokens"]["refresh_token"])
                    logger.info("Active user token renewed and saved successfully.")
                    return True
                else:
                    logger.warning("Failed to renew active user token.")
                    # Jangan gunakan input()
            except Exception as e:
                 logger.error(f"Exception during token renewal: {e}")
        else:
            logger.info("No active user set or missing refresh token.")
            # Jangan gunakan input()
        return False

    def get_active_user(self):
        # Coba perbarui token jika sudah 5 menit
        if self.active_user and self.last_refresh_time is not None and (int(time.time()) - self.last_refresh_time) > 300:
             logger.info("Active user token is older than 5 minutes. Attempting to renew.")
             self.renew_active_user_token()
             # self.last_refresh_time = time.time() # renew_active_user_token sudah mengaturnya

        # Jika tidak ada active_user, coba pilih yang pertama
        if not self.active_user:
            # Choose the first user if available
            if self.refresh_tokens: # Gunakan pengecekan idiomatic
                first_rt = self.refresh_tokens[0]
                logger.info(f"No active user. Attempting to set active user to first available: {first_rt['number']}.")
                tokens = get_new_token(first_rt["refresh_token"])
                if tokens:
                    self.active_user = {
                        "number": int(first_rt["number"]),
                        "tokens": tokens
                    }
                    logger.info(f"Active user automatically set to {first_rt['number']}.")
                else:
                     logger.warning(f"Failed to get tokens for auto-selected user {first_rt['number']}.")
            else:
                 logger.info("No refresh tokens available to set as active user.")

        return self.active_user

    def get_active_tokens(self):
        active_user = self.get_active_user()
        tokens = active_user["tokens"] if active_user else None
        if not tokens:
            logger.info("get_active_tokens: No active tokens available.")
        return tokens

# Buat instance singleton
AuthInstance = Auth()

# Pastikan logger di auth_helper juga aktif
# Ini bisa dilakukan di __init__.py proyek Anda atau di awal bot_telegram.py
# logging.basicConfig(level=logging.INFO) # Contoh konfigurasi dasar