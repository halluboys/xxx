#!/bin/bash

# --- KONFIGURASI ---
BOT_TOKEN="8486193618:AAHf-bNLvZG_iqtnGq79TS4Q13bRMXdxJEU"
CHAT_ID="876081450"
# -------------------

# Cek apakah path file diberikan sebagai argumen
if [ -z "$1" ]; then
  echo "Error: Anda harus menyertakan path ke file."
  echo "Contoh penggunaan: ./kirim_file.sh /path/ke/file.zip"
  exit 1
fi

FILE_PATH="$1"
CAPTION="File dikirim dari VPS: $(basename "$FILE_PATH")"

echo "Mengirim file: $FILE_PATH"

curl -s -X POST \
     -F document=@"$FILE_PATH" \
     -F caption="$CAPTION" \
     "https://api.telegram.org/bot$BOT_TOKEN/sendDocument?chat_id=$CHAT_ID"

echo -e "\nSelesai."
