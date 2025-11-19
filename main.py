#====================================================================================================================#
#                                      Script Created By Penelitian ITMK 2022 K                                      #
#      (MODIFIKASI: POSISI ICON CUACA DAN ARAH ANGIN DIPINDAH, STRUKTUR/PATH/FONT LAIN DIPERTAHANKAN ASLI)           #
#====================================================================================================================#

import requests
import csv
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

# Modul tambahan untuk email
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from email.mime.base import MIMEBase
from email import encoders # Perlu diimport untuk MIMEBase dan encoders

# ====================================================================================================
# BAGIAN 1: PENGAMBILAN DATA BMKG, PENYIMPANAN CSV, DAN DOWNLOAD IKON (TIDAK BERUBAH)
# ====================================================================================================

print("--- Memulai Pengambilan Data BMKG ---")

# URL API BMKG
url = "https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4=36.71.01.1003"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Ambil data
try:
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status() 
    data = response.json()
except requests.exceptions.RequestException as e:
    print(f"❌ Gagal mengambil data dari API BMKG: {e}")
    exit() 

# Buat folder output
output_dir = r"D:\Prakiraan_Cuaca_STMKG"
icon_dir = os.path.join(output_dir, "ikon_cuaca")
csv_path = os.path.join(output_dir, "prakiraan_cuaca.csv")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(icon_dir, exist_ok=True)

# Fungsi konversi km/j ke knots
def kmh_to_knots(kmh):
    try:
        kmh_float = float(kmh)
        knots = kmh_float * 0.539957
        return f"{knots:.1f}"
    except:
        return ""

# Siapkan file CSV
with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "Tanggal", "Jam", "Cuaca",
        "Suhu (°C)", "Kelembapan (%)",
        "Kecepatan Angin (km/j)", "Kecepatan Angin (knots)", 
        "Arah Angin (°)", "File Ikon"
    ])
    
    try:
        weather_data_groups = data["data"][0]["cuaca"]
    except (IndexError, KeyError):
        print("⚠️ Struktur data BMKG tidak sesuai. Tidak ada data cuaca untuk diproses.")
        weather_data_groups = []

    for group in weather_data_groups:
        for item in group:
            datetime_str = item.get("local_datetime", "")
            Tanggal = datetime_str[0:10] if len(datetime_str) >= 16 else ""
            jam = datetime_str[11:16] if len(datetime_str) >= 16 else ""

            cuaca = item.get("weather_desc", "")
            suhu = item.get("t", "")
            kelembapan = item.get("hu", "")
            angin = item.get("ws", "")
            arah_angin = item.get("wd_deg", "")
            angin_knots = kmh_to_knots(angin)

            ikon_url = item.get("image", "")
            ikon_filename = ""
            if ikon_url:
                ikon_filename = ikon_url.split("/")[-1]
                ikon_path = os.path.join(icon_dir, ikon_filename)

                if not os.path.exists(ikon_path):
                    try:
                        ikon_response = requests.get(ikon_url, timeout=10)
                        if ikon_response.status_code == 200:
                            with open(ikon_path, "wb") as f:
                                f.write(ikon_response.content)
                    except requests.exceptions.RequestException:
                        pass
            
            writer.writerow([
                Tanggal, jam, cuaca, suhu, kelembapan, 
                angin, angin_knots, arah_angin, ikon_filename
            ])

print(f"\n✅ File prakiraan_cuaca.csv berhasil dibuat di: {csv_path}")


# ====================================================================================================
# BAGIAN 2: PEMBUATAN GAMBAR INFOGRAFIS DARI DATA CSV (MODIFIKASI POSISI PLOTTING)
# ====================================================================================================

print("\n--- Memulai Pembuatan Gambar Infografis ---")

file_path = csv_path
try:
    df = pd.read_csv(file_path)
except Exception as e:
    print(f"❌ Gagal membaca file CSV untuk pembuatan gambar: {e}")
    exit()

# Fungsi ambil nilai (TIDAK BERUBAH)
def ambil_nilai(df, baris, kolom):
    try:
        if kolom not in df.columns: return ""
        nilai = df.iloc[baris][kolom]
        if pd.isna(nilai): return ""
        return str(nilai).strip()
    except Exception:
        return ""

# Fungsi paste ikon arah angin (TIDAK BERUBAH)
def paste_rotated_icon(base_img, icon_path, center_position, angle):
    if os.path.exists(icon_path):
        try:
            ikon_img = Image.open(icon_path).convert("RGBA").resize((60, 60)) 
            ikon_img_rotated = ikon_img.rotate(-angle, expand=True, resample=Image.BICUBIC) 
            icon_w, icon_h = ikon_img_rotated.size
            center_x, center_y = center_position
            paste_x = center_x - icon_w // 2
            paste_y = center_y - icon_h // 2
            base_img.paste(ikon_img_rotated, (paste_x, paste_y), ikon_img_rotated)
        except Exception:
            pass

# Fungsi paste ikon cuaca (TIDAK BERUBAH)
def paste_ikon_cuaca(base_img, ikon_dir, position, ikon_filename, default_width=100):
    ikon_filename = os.path.splitext(ikon_filename)[0] + ".png"
    ikon_path = os.path.join(ikon_dir, ikon_filename)

    if os.path.exists(ikon_path):
        try:
            ikon_img = Image.open(ikon_path).convert("RGBA")
            target_width = 130 if "hujan" in ikon_filename.lower() else default_width
            offset_x = -15 if "hujan" in ikon_filename.lower() else 0
            offset_y = -10 if "hujan" in ikon_filename.lower() else 0
            
            scale_ratio = target_width / ikon_img.width
            target_height = int(ikon_img.height * scale_ratio)
            ikon_img = ikon_img.resize((target_width, target_height), Image.LANCZOS)

            x, y = position
            base_img.paste(ikon_img, (x + offset_x, y + offset_y), ikon_img)
        except Exception:
            pass

# Siapkan gambar & font (TIDAK BERUBAH)
template_path = os.path.join(output_dir, "3.png")
if not os.path.exists(template_path):
    print(f"❌ File template gambar '3.png' tidak ditemukan. Tidak bisa membuat gambar.")
    exit()
    
try:
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font_path = "C:/Windows/Fonts/Bahnschrift.ttf"
    font = ImageFont.truetype(font_path, 34) if os.path.exists(font_path) else ImageFont.load_default()

    ikon_arah_path = os.path.join(icon_dir, "ikon_arah_angin.png")
except Exception as e:
    print(f"❌ Gagal memuat template gambar/font: {e}")
    exit()


# ----------------------------------------------------------------------------------------------------
# *** MODIFIKASI POSISI PLOTTING DATA ***
# ----------------------------------------------------------------------------------------------------

# Definisi posisi baru
# Saya akan mempertahankan data asli Anda, tetapi menggunakan posisi x & y baru untuk ikon cuaca dan arah angin.
# Posisi kolom (dari kiri ke kanan): Tanggal | Jam | SUHU | KELEMBAPAN | IKON CUACA | ARAH ANGIN/KECEPATAN

# Posisi lama Anda: 
# Tanggal/Jam: 150/390, 350/390, 730/390, 930/390 (Dipertahankan)
# Suhu: 450 (Dipertahankan)
# Kelembapan: 620 (Dipertahankan)
# Kecepatan Angin: 850 (Dipertahankan)
# Ikon Cuaca: 320 (Diubah)
# Ikon Arah Angin: x - 80 dari Kecepatan Angin (Diubah)
