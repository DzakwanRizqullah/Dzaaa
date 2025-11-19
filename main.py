#====================================================================================================================#
#                                      Script Created By Penelitian ITMK 2022 K                                      #
#      (FIX FINAL: ABSOLUTE PATH D: DIPERTAHANKAN, FONT SIZE 34, HANYA DATA NUMERIK + IKON CUACA DENGAN SATUAN)       #
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
from email import encoders

# ====================================================================================================
# KONFIGURASI PATH GLOBAL (ABSOLUTE PATH D:)
# ====================================================================================================

# Path Absolute yang Dipertahankan (Sesuai Permintaan)
output_dir = r"D:\Prakiraan_Cuaca_STMKG" 
icon_dir = os.path.join(output_dir, "ikon_cuaca") # D:\Prakiraan_Cuaca_STMKG\ikon_cuaca
csv_path = os.path.join(output_dir, "prakiraan_cuaca.csv")
template_path = os.path.join(output_dir, "3.png") # Template 3.png diasumsikan di sini
ikon_arah_path = os.path.join(icon_dir, "ikon_arah_angin.png") # Ikon arah angin diasumsikan di folder ikon_cuaca
output_gambar_path = r"D:\Prakicu\PrakicuITM.png" # Path output gambar akhir

# ====================================================================================================
# BAGIAN 1: PENGAMBILAN DATA BMKG, PENYIMPANAN CSV, DAN DOWNLOAD IKON
# (Tidak Ada Perubahan Logika)
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
    fetch_success = True
except requests.exceptions.RequestException as e:
    print(f"❌ Gagal mengambil data dari API BMKG: {e}")
    fetch_success = False

# Buat folder output
os.makedirs(output_dir, exist_ok=True)
os.makedirs(icon_dir, exist_ok=True)
os.makedirs(os.path.dirname(output_gambar_path), exist_ok=True) # Pastikan D:\Prakicu ada

# Fungsi konversi km/j ke knots
def kmh_to_knots(kmh):
    try:
        kmh_float = float(kmh)
        knots = kmh_float * 0.539957
        return f"{knots:.1f}"
    except:
        return ""

# Siapkan file CSV
if fetch_success:
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
else:
    # Exit jika gagal fetch dan tidak ada data CSV lama (opsional)
    if not os.path.exists(csv_path):
        exit()

# ====================================================================================================
# BAGIAN 2: PEMBUATAN GAMBAR INFOGRAFIS DARI DATA CSV (KOREKSI PLOTTING)
# ====================================================================================================

print("\n--- Memulai Pembuatan Gambar Infografis ---")

file_path = csv_path
try:
    df = pd.read_csv(file_path)
except Exception as e:
    print(f"❌ Gagal membaca file CSV untuk pembuatan gambar: {e}")
    exit()

# Fungsi ambil nilai (dipertahankan)
def ambil_nilai(df, baris, kolom):
    try:
        if kolom not in df.columns: return ""
        nilai = df.iloc[baris][kolom]
        if pd.isna(nilai): return ""
        return str(nilai).strip()
    except Exception:
        return ""

# Fungsi paste ikon arah angin (centered & tidak dibulatkan) (dipertahankan)
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

# Fungsi paste ikon cuaca (dipertahankan, width disesuaikan)
def paste_ikon_cuaca(base_img, ikon_dir, position, ikon_filename, default_width=100):
    ikon_filename = os.path.splitext(ikon_filename)[0] + ".png"
    ikon_path = os.path.join(ikon_dir, ikon_filename)

    if os.path.exists(ikon_path):
        try:
            ikon_img = Image.open(ikon_path).convert("RGBA")
            # Width disesuaikan agar proporsional dengan font 34 (misal: 110px)
            target_width = 110 
            
            # Offset untuk koreksi visual (opsional)
            offset_x = -5 
            offset_y = 0 
            
            scale_ratio = target_width / ikon_img.width
            target_height = int(ikon_img.height * scale_ratio)
            ikon_img = ikon_img.resize((target_width, target_height), Image.LANCZOS)

            x, y = position
            base_img.paste(ikon_img, (x + offset_x, y + offset_y), ikon_img)
        except Exception:
            pass

# Siapkan gambar & font
if not os.path.exists(template_path):
    print(f"❌ File template gambar '3.png' tidak ditemukan di {template_path}. Tidak bisa membuat gambar.")
    exit()
    
try:
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font_path = "C:/Windows/Fonts/Bahnschrift.ttf"
    # FONT SIZE DIPERTAHANKAN 34 UNTUK SEMUA DATA, SESUAI PERMINTAAN AWAL
    font_data = ImageFont.truetype(font_path, 34) if os.path.exists(font_path) else ImageFont.load_default(size=34)

    # Path ikon arah angin dikoreksi ke folder ikon_cuaca
    # ikon_arah_path = os.path.join(icon_dir, "ikon_arah_angin.png") 
    # ^ Diubah untuk konsistensi dengan variabel global di atas:
    # ikon_arah_path = os.path.join(output_dir, "ikon_arah_angin.png") # ASUMSI: ikon_arah_angin.png ada di folder D:\Prakiraan_Cuaca_STMKG\ikon_cuaca
except Exception as e:
    print(f"❌ Gagal memuat template gambar/font: {e}")
    exit()


# *** KOREKSI POSISI DATA INFOGRAFIS ***
# OFFSET Y diperkirakan untuk font 34 agar rapi di tengah baris
TEXT_VERTICAL_OFFSET = 30 
ICON_VERTICAL_OFFSET = 15 

# Data posisi BARU (hanya data yang diminta + satuan)
data_positions_revised = [
    # Header TANGGAL/JAM (diasumsikan menggunakan font 34 juga)
    # Catatan: Posisi Y di sini (390) adalah dari skrip Anda, dan teksnya rapi.
    {"x": 150, "y": 390, "cell": (0, "Tanggal"), "font": font_data},
    {"x": 350, "y": 390, "cell": (0, "Jam"), "font": font_data},
    {"x": 730, "y": 390, "cell": (8, "Tanggal"), "font": font_data},
    {"x": 930, "y": 390, "cell": (8, "Jam"), "font": font_data},
    
    # Waktu (Jam) - Kolom 1
    {"x": 150, "y": 795 + TEXT_VERTICAL_OFFSET, "cell": (0, "Jam"), "font": font_data},
    {"x": 150, "y": 895 + TEXT_VERTICAL_OFFSET, "cell": (1, "Jam"), "font": font_data},
    {"x": 150, "y": 990 + TEXT_VERTICAL_OFFSET, "cell": (2, "Jam"), "font": font_data},
    {"x": 150, "y": 1090 + TEXT_VERTICAL_OFFSET, "cell": (3, "Jam"), "font": font_data},
    {"x": 150, "y": 1185 + TEXT_VERTICAL_OFFSET, "cell": (4, "Jam"), "font": font_data},
    {"x": 150, "y": 1285 + TEXT_VERTICAL_OFFSET, "cell": (5, "Jam"), "font": font_data},
    {"x": 150, "y": 1380 + TEXT_VERTICAL_OFFSET, "cell": (6, "Jam"), "font": font_data},
    {"x": 150, "y": 1480 + TEXT_VERTICAL_OFFSET, "cell": (7, "Jam"), "font": font_data},

    # Ikon Cuaca - Kolom 2 (Kiri)
    # X dikoreksi ke 305 agar ikon lebih sentral
    {"x": 305, "y": 795 + ICON_VERTICAL_OFFSET, "cell": (0, "File Ikon"), "is_icon": True}, 
    {"x": 305, "y": 895 + ICON_VERTICAL_OFFSET, "cell": (1, "File Ikon"), "is_icon": True},
    {"x": 305, "y": 990 + ICON_VERTICAL_OFFSET, "cell": (2, "File Ikon"), "is_icon": True},
    {"x": 305, "y": 1090 + ICON_VERTICAL_OFFSET, "cell": (3, "File Ikon"), "is_icon": True},
    {"x": 305, "y": 1185 + ICON_VERTICAL_OFFSET, "cell": (4, "File Ikon"), "is_icon": True},
    {"x": 305, "y": 1285 + ICON_VERTICAL_OFFSET, "cell": (5, "File Ikon"), "is_icon": True},
    {"x": 305, "y": 1380 + ICON_VERTICAL_OFFSET, "cell": (6, "File Ikon"), "is_icon": True},
    {"x": 305, "y": 1480 + ICON_VERTICAL_OFFSET, "cell": (7, "File Ikon"), "is_icon": True},

    # Suhu (°C) - Kolom 3
    {"x": 450, "y": 795 + TEXT_VERTICAL_OFFSET, "cell": (0, "Suhu (°C)"), "font": font_data, "suffix": "°C"}, 
    {"x": 450, "y": 895 + TEXT_VERTICAL_OFFSET, "cell": (1, "Suhu (°C)"), "font": font_data, "suffix": "°C"},
    {"x": 450, "y": 990 + TEXT_VERTICAL_OFFSET, "cell": (2, "Suhu (°C)"), "font": font_data, "suffix": "°C"},
    {"x": 450, "y": 1090 + TEXT_VERTICAL_OFFSET, "cell": (3, "Suhu (°C)"), "font": font_data, "suffix": "°C"},
    {"x": 450, "y": 1185 + TEXT_VERTICAL_OFFSET, "cell": (4, "Suhu (°C)"), "font": font_data, "suffix": "°C"},
    {"x": 450, "y": 1285 + TEXT_VERTICAL_OFFSET, "cell": (5, "Suhu (°C)"), "font": font_data, "suffix": "°C"},
    {"x": 450, "y": 1380 + TEXT_VERTICAL_OFFSET, "cell": (6, "Suhu (°C)"), "font": font_data, "suffix": "°C"},
    {"x": 450, "y": 1480 + TEXT_VERTICAL_OFFSET, "cell": (7, "Suhu (°C)"), "font": font_data, "suffix": "°C"},
    
    # Kelembapan (%) - Kolom 4
    {"x": 620, "y": 795 + TEXT_VERTICAL_OFFSET, "cell": (0, "Kelembapan (%)"), "font": font_data, "suffix": "%"},
    {"x": 620, "y": 895 + TEXT_VERTICAL_OFFSET, "cell": (1, "Kelembapan (%)"), "font": font_data, "suffix": "%"},
    {"x": 620, "y": 990 + TEXT_VERTICAL_OFFSET, "cell": (2, "Kelembapan (%)"), "font": font_data, "suffix": "%"},
    {"x": 620, "y": 1090 + TEXT_VERTICAL_OFFSET, "cell": (3, "Kelembapan (%)"), "font": font_data, "suffix": "%"},
    {"x": 620, "y": 1185 + TEXT_VERTICAL_OFFSET, "cell": (4, "Kelembapan (%)"), "font": font_data, "suffix": "%"},
    {"x": 620, "y": 1285 + TEXT_VERTICAL_OFFSET, "cell": (5, "Kelembapan (%)"), "font": font_data, "suffix": "%"},
    {"x": 620, "y": 1380 + TEXT_VERTICAL_OFFSET, "cell": (6, "Kelembapan (%)"), "font": font_data, "suffix": "%"},
    {"x": 620, "y": 1480 + TEXT_VERTICAL_OFFSET, "cell": (7, "Kelembapan (%)"), "font": font_data, "suffix": "%"},
    
    # Kecepatan Angin (knots) - Kolom 5
    # Angka knots di plot lebih ke kanan (X=870) untuk memberi ruang pada ikon arah angin
    {"x": 870, "y": 795 + TEXT_VERTICAL_OFFSET, "cell": (0, "Kecepatan Angin (knots)"), "font": font_data, "suffix": " knots", "is_wind": True}, 
    {"x": 870, "y": 895 + TEXT_VERTICAL_OFFSET, "cell": (1, "Kecepatan Angin (knots)"), "font": font_data, "suffix": " knots", "is_wind": True},
    {"x": 870, "y": 990 + TEXT_VERTICAL_OFFSET, "cell": (2, "Kecepatan Angin (knots)"), "font": font_data, "suffix": " knots", "is_wind": True},
    {"x": 870, "y": 1090 + TEXT_VERTICAL_OFFSET, "cell": (3, "Kecepatan Angin (knots)"), "font": font_data, "suffix": " knots", "is_wind": True},
    {"x": 870, "y": 1185 + TEXT_VERTICAL_OFFSET, "cell": (4, "Kecepatan Angin (knots)"), "font": font_data, "suffix": " knots", "is_wind": True},
    {"x": 870, "y": 1285 + TEXT_VERTICAL_OFFSET, "cell": (5, "Kecepatan Angin (knots)"), "font": font_data, "suffix": " knots", "is_wind": True},
    {"x": 870, "y": 1380 + TEXT_VERTICAL_OFFSET, "cell": (6, "Kecepatan Angin (knots)"), "font": font_data, "suffix": " knots", "is_wind": True},
    {"x": 870, "y": 1480 + TEXT_VERTICAL_OFFSET, "cell": (7, "Kecepatan Angin (knots)"), "font": font_data, "suffix": " knots", "is_wind": True},
]

# Plot
for item in data_positions_revised:
    x, y = item["x"], item["y"]
    
    # Untuk Teks Statis (Header/Footer - TIDAK ADA DALAM LIST INI, ASUMSI SUDAH DI TEMPLATE)
    # Anda bisa tambahkan jika perlu, contoh:
    # draw.text((800, 1650), "Sumber : BMKG", font=font_data, fill="white")
    
    # Untuk Teks dari Data CSV
    if "cell" in item:
        baris, kolom = item["cell"]
        teks = ambil_nilai(df, baris, kolom)
        current_font = item.get("font", font_data) 

        # Plot Angka + Suffix (Suhu, Kelembaban, Kecepatan Angin)
        if "File Ikon" not in kolom:
            suffix = item.get("suffix", "")
            if teks:
                # Plot Teks dan Satuan
                draw.text((x, y), teks + suffix, font=current_font, fill="white")

            # Plot Ikon Arah Angin (Hanya jika ini kolom Kecepatan Angin)
            if item.get("is_wind", False):
                arah_angin = ambil_nilai(df, baris, "Arah Angin (°)")
                try:
                    angle = float(arah_angin)
                    # Ikon arah angin diposisikan di sebelah kiri angka knots
                    paste_rotated_icon(img, ikon_arah_path, (x - 100, y + 17), angle) # X dikurangi 100 dari angka knots
                except ValueError:
                    pass

        # Plot Ikon Cuaca
        elif "File Ikon" in kolom:
            paste_ikon_cuaca(img, icon_dir, (x, y), teks)


# Simpan Gambar
try:
    img.save(output_gambar_path)
    print(f"\n✅ Gambar prakiraan selesai dan disimpan di: {output_gambar_path}")
except Exception as e:
    print(f"❌ Gagal menyimpan gambar: {e}")
    exit()

# ====================================================================================================
# BAGIAN 3: PENGIRIMAN EMAIL (TIDAK ADA PERUBAHAN LOGIKA, HANYA PATH VARIABEL)
# ====================================================================================================

def attach_file_to_email(msg, file_path, file_type='image'):
    """Fungsi bantuan untuk melampirkan file ke objek MIMEMultipart."""
    if not os.path.exists(file_path):
        print(f"⚠️ Peringatan: File lampiran tidak ditemukan: {file_path}")
        return

    try:
        with open(file_path, "rb") as attachment:
            filename = os.path.basename(file_path)
            
            if file_type == 'image':
                part = MIMEImage(attachment.read(), name=filename)
                content_type = 'attachment'
            elif file_type == 'csv':
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                content_type = 'attachment'
            else:
                return

            part.add_header('Content-Disposition', f'{content_type}; filename="{filename}"')
            msg.attach(part)
            print(f"✅ File dilampirkan: {filename}")
            
    except Exception as e:
        print(f"❌ Gagal melampirkan file {file_path}: {e}")

def send_email_with_attachments(image_path, csv_path):
    
    # ===========================================================================
    # KONFIGURASI EMAIL
    # ===========================================================================
    smtp_server = "smtp.gmail.com"
    port = 587
    sender_email = "dzaa5th@gmail.com"
    # KATA SANDI APLIKASI
    password = "necb noft kvfg dxei" 
    recipient_email = "mulmeditmstmkg@gmail.com"
    
    # Membuat pesan email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Prakiraan Cuaca STMKG (Infografis & Data CSV) - {datetime.now().strftime('%Y-%m-%d')}"

    # Isi body email (teks)
    body = "Terlampir adalah infografis prakiraan cuaca terbaru (PNG) dan data mentah dalam format spreadsheet (CSV)."
    msg.attach(MIMEText(body, 'plain'))

    # --- MELAMPIRKAN FILE ---
    attach_file_to_email(msg, image_path, file_type='image')
    attach_file_to_email(msg, csv_path, file_type='csv')
    
    # --- MENGIRIM EMAIL ---
    context = ssl.create_default_context()
    try:
        print("\n--- Memulai Pengiriman Email ---")
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls(context=context)
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"✅ Email berhasil dikirim ke: {recipient_email}")
    except smtplib.SMTPAuthenticationError:
        print("❌ Gagal mengirim email: Autentikasi SMTP gagal.")
        print("Pastikan Anda menggunakan **APP PASSWORD (Kata Sandi Aplikasi)** jika memakai Gmail.")
    except Exception as e:
        print(f"❌ Gagal mengirim email: Terjadi kesalahan. Cek koneksi internet atau pengaturan server SMTP.")
        print(f"Error detail: {e}")

# Panggil fungsi pengiriman email baru
send_email_with_attachments(output_gambar_path, csv_path)
