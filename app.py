import os
import json
import gspread
import re
from flask import Flask, request, jsonify, render_template
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Подключение к Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not CREDENTIALS_JSON:
    raise ValueError("❌ Ошибка: GOOGLE_CREDENTIALS_JSON не найдено!")

creds_dict = json.loads(CREDENTIALS_JSON)
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/check-in", methods=["POST"])
def check_in():
    try:
        data = request.json
        qr_data = data.get("qr_data")

        if not qr_data:
            return jsonify({"message": "❌ Ошибка: пустые данные QR-кода!"}), 400

        # Извлекаем данные из QR-кода (ищем строки с Name, Phone, Email)
        name_match = re.search(r"Name:\s*(.+)", qr_data)
        phone_match = re.search(r"Phone:\s*(\d+)", qr_data)
        email_match = re.search(r"Email:\s*([\w\.\-]+@[\w\.\-]+)", qr_data)

        if not (name_match and phone_match and email_match):
            return jsonify({"message": "❌ Ошибка: Неверный формат QR-кода!"}), 400

        name = name_match.group(1).strip()
        phone = phone_match.group(1).strip()
        email = email_match.group(1).strip().lower()

        # Читаем все строки из Google Sheets
        all_values = sheet.get_all_values()
        found = False

        for i, row in enumerate(all_values):
            if len(row) >= 3:
                sheet_email = row[0].strip().lower()  # Колонка A (Email)
                sheet_name = row[1].strip()  # Колонка B (Name)
                sheet_phone = row[2].strip()  # Колонка C (Phone)

                # Проверяем совпадение Email, Name и Phone
                if sheet_email == email and sheet_name == name and sheet_phone == phone:
                    sheet.update_cell(i + 1, 10, "Пришёл")  # Колонка J (CheckIn)
                    found = True
                    break

        if found:
            return jsonify({"message": f"✅ Гость {name} ({email}) отмечен как 'Пришёл'"}), 200
        else:
            return jsonify({"message": "❌ Гость не найден в системе!"}), 404

    except Exception as e:
        return jsonify({"message": f"❌ Ошибка обработки: {e}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
