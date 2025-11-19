#====================================================================================================================#
#                                               Script Created By Penelitian ITMK 2022 K                             #
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

# ====================================================================================================
# BAGIAN 1: PENGAMBILAN DATA BMKG, PENYIMPANAN CSV, DAN DOWNLOAD IKON
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
                            # print(f"✅ Ikon disimpan: {ikon_path}")
                    except requests.exceptions.RequestException:
                        pass # Abaikan error download ikon
            
            writer.writerow([
                Tanggal, jam, cuaca, suhu, kelembapan, 
                angin, angin_knots, arah_angin, ikon_filename
            ])

print(f"\n✅ File prakiraan_cuaca.csv berhasil dibuat di: {csv_path}")


# ====================================================================================================
# BAGIAN 2: PEMBUATAN GAMBAR INFOGRAFIS DARI DATA CSV
# ====================================================================================================

print("\n--- Memulai Pembuatan Gambar Infografis ---")

file_path = csv_path
try:
    df = pd.read_csv(file_path)
except Exception as e:
    print(f"❌ Gagal membaca file CSV untuk pembuatan gambar: {e}")
    exit()

# Fungsi ambil nilai
def ambil_nilai(df, baris, kolom):
    try:
        if kolom not in df.columns: return ""
        nilai = df.iloc[baris][kolom]
        if pd.isna(nilai): return ""
        return str(nilai).strip()
    except Exception:
        return ""

# Fungsi paste ikon arah angin (centered & tidak dibulatkan)
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

# Fungsi paste ikon cuaca
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

# Siapkan gambar & font
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

# Data posisi (tetap sama)
data = [
    {"x": 150, "y": 390, "cell": (0, "Tanggal")},
    {"x": 350, "y": 390, "cell": (0, "Jam")},
    {"x": 730, "y": 390, "cell": (8, "Tanggal")},
    {"x": 930, "y": 390, "cell": (8, "Jam")},
    {"x": 450, "y": 795, "cell": (0, "Suhu (°C)")},
    {"x": 450, "y": 895, "cell": (1, "Suhu (°C)")},
    {"x": 450, "y": 990, "cell": (2, "Suhu (°C)")},
    {"x": 450, "y": 1090, "cell": (3, "Suhu (°C)")},
    {"x": 450, "y": 1185, "cell": (4, "Suhu (°C)")},
    {"x": 450, "y": 1285, "cell": (5, "Suhu (°C)")},
    {"x": 450, "y": 1380, "cell": (6, "Suhu (°C)")},
    {"x": 450, "y": 1480, "cell": (7, "Suhu (°C)")},
    {"x": 620, "y": 795, "cell": (0, "Kelembapan (%)")},
    {"x": 620, "y": 895, "cell": (1, "Kelembapan (%)")},
    {"x": 620, "y": 990, "cell": (2, "Kelembapan (%)")},
    {"x": 620, "y": 1090, "cell": (3, "Kelembapan (%)")},
    {"x": 620, "y": 1185, "cell": (4, "Kelembapan (%)")},
    {"x": 620, "y": 1285, "cell": (5, "Kelembapan (%)")},
    {"x": 620, "y": 1380, "cell": (6, "Kelembapan (%)")},
    {"x": 620, "y": 1480, "cell": (7, "Kelembapan (%)")},
    {"x": 850, "y": 795, "cell": (0, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 892, "cell": (1, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 992, "cell": (2, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1087, "cell": (3, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1187, "cell": (4, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1285, "cell": (5, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1380, "cell": (6, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1480, "cell": (7, "Kecepatan Angin (knots)")},
    {"x": 320, "y": 780, "cell": (0, "File Ikon")},
    {"x": 320, "y": 867, "cell": (1, "File Ikon")},
    {"x": 320, "y": 967, "cell": (2, "File Ikon")},
    {"x": 320, "y": 1065, "cell": (3, "File Ikon")},
    {"x": 320, "y": 1165, "cell": (4, "File Ikon")},
    {"x": 320, "y": 1265, "cell": (5, "File Ikon")},
    {"x": 320, "y": 1358, "cell": (6, "File Ikon")},
    {"x": 320, "y": 1456, "cell": (7, "File Ikon")},
]

# Plot
for item in data:
    x, y = item["x"], item["y"]
    baris, kolom = item["cell"]
    teks = ambil_nilai(df, baris, kolom)

    if "File Ikon" not in kolom:
        draw.text((x, y), teks, font=font, fill="white")

    if "Kecepatan Angin" in kolom:
        arah_angin = ambil_nilai(df, baris, "Arah Angin (°)")
        try:
            angle = float(arah_angin)
            paste_rotated_icon(img, ikon_arah_path, (x - 80, y + 10), angle) 
        except ValueError:
            pass

    if "File Ikon" in kolom:
        paste_ikon_cuaca(img, icon_dir, (x, y), teks)

# Simpan Gambar
output_gambar_path = r"D:\Prakicu\PrakicuITM.png"
output_gambar_dir = os.path.dirname(output_gambar_path)
os.makedirs(output_gambar_dir, exist_ok=True) 

try:
    img.save(output_gambar_path)
    print(f"\n✅ Gambar prakiraan selesai dan disimpan di: {output_gambar_path}")
except Exception as e:
    print(f"❌ Gagal menyimpan gambar: {e}")
    exit()

# ====================================================================================================
# BAGIAN 3: PENGIRIMAN EMAIL
# ====================================================================================================

def send_email_with_attachment(image_path):
    
    # ===========================================================================
    # KONFIGURASI EMAIL - HARAP GANTI DENGAN DATA ANDA
    # ===========================================================================
    smtp_server = "smtp.gmail.com"  # Ganti jika tidak pakai Gmail
    port = 587                      # Port untuk StartTLS (Gmail)
    sender_email = "dzaa5th@gmail.com"  # 👈 GANTI DENGAN EMAIL PENGIRIM ANDA
    password = "necb noft kvfg dxei"         # 👈 GANTI DENGAN APP PASSWORD/KATA SANDI AKUN
    recipient_email = "dzakwanrisqullah12@gmail.com" # 👈 GANTI DENGAN EMAIL PENERIMA
    
    # Pastikan file ada sebelum dikirim
    if not os.path.exists(image_path):
        print(f"❌ Gagal mengirim email: File gambar tidak ditemukan di {image_path}")
        return

    # Membuat pesan email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Prakiraan Cuaca Harian STMKG - {datetime.now().strftime('%Y-%m-%d')}"

    # Isi body email (teks)
    body = "Terlampir adalah infografis prakiraan cuaca terbaru yang dihasilkan oleh skrip otomatis."
    msg.attach(MIMEText(body, 'plain'))

    # Melampirkan gambar
    try:
        with open(image_path, "rb") as attachment:
            img_part = MIMEImage(attachment.read(), name=os.path.basename(image_path))
            img_part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(image_path))
            msg.attach(img_part)
    except Exception as e:
        print(f"❌ Gagal melampirkan gambar: {e}")
        return

    # Mengirim email menggunakan smtplib
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls(context=context)
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"✅ Email berhasil dikirim ke: {recipient_email}")
    except smtplib.SMTPAuthenticationError:
        print("❌ Gagal mengirim email: Autentikasi SMTP gagal.")
        print("Pastikan Anda menggunakan APP PASSWORD (Kata Sandi Aplikasi) jika memakai Gmail.")
    except Exception as e:
        print(f"❌ Gagal mengirim email: Terjadi kesalahan. Cek koneksi internet atau pengaturan server SMTP.")
        print(f"Error detail: {e}")

# Panggil fungsi pengiriman email
send_email_with_attachment(output_gambar_path)