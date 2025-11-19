#====================================================================================================================#
#                                      Script Created By Penelitian ITMK 2022 K                                      #
#                              (FINAL FIX: Path Portabel, FONT SIZE 34, Alignment & Ukuran Ikon)                     #
#====================================================================================================================#

import requests
import csv
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from email.mime.base import MIMEBase
from email import encoders

# Modul tambahan untuk email
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

# ====================================================================================================
# KONFIGURASI PATH GLOBAL (PORTABEL/RELATIF)
# ====================================================================================================

# Folder output utama: [Lokasi Skrip]/output
output_dir = os.path.join(os.getcwd(), "output") 

icon_dir = os.path.join(output_dir, "ikon_cuaca") 
csv_path = os.path.join(output_dir, "prakiraan_cuaca.csv")

# Path file gambar hasil akhir (di dalam folder output)
output_gambar_path = os.path.join(output_dir, "PrakicuITM.png") 

# Path untuk template (di dalam folder output)
template_path = os.path.join(output_dir, "3.png") 
ikon_arah_path = os.path.join(output_dir, "ikon_arah_angin.png") 

# **FIX FONT SIZE**
FONT_SIZE_DATA = 34 # Ukuran font untuk data utama di tabel (Kembali ke ukuran kecil)
FONT_SIZE_HEADER_SMALL = 30 # Ukuran font untuk header kecil seperti "Ikatan Taruna..."
FONT_SIZE_HEADER_DATE = 34 # Ukuran font untuk tanggal/jam di header
FONT_SIZE_TITLE = 50 # Judul agak besar, tapi tidak 60
FONT_SIZE_FOOTER = 30 # Ukuran font untuk "Sumber: BMKG"

# ====================================================================================================
# BAGIAN 1: PENGAMBILAN DATA BMKG, PENYIMPANAN CSV, DAN DOWNLOAD IKON 
# (TIDAK ADA PERUBAHAN LOGIKA)
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
# BAGIAN 2: PEMBUATAN GAMBAR INFOGRAFIS DARI DATA CSV 
# (KEMBALI KE FONT SIZE 34 DAN ALIGNMENT SESUAI UKURAN KECIL)
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
            # Tetap 60x60 agar tidak terlalu besar dibanding teks 34
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
def paste_ikon_cuaca(base_img, ikon_dir, position, ikon_filename, default_width=100): # Kembali ke default width 100
    ikon_filename = os.path.splitext(ikon_filename)[0] + ".png"
    ikon_path = os.path.join(ikon_dir, ikon_filename)

    if os.path.exists(ikon_path):
        try:
            ikon_img = Image.open(ikon_path).convert("RGBA")
            # Kembali ke ukuran kecil yang proporsional dengan font 34
            target_width = 120 if "hujan" in ikon_filename.lower() else default_width 
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
if not os.path.exists(template_path):
    print(f"❌ File template gambar '3.png' tidak ditemukan. Dicari di: {template_path}. Tidak bisa membuat gambar.")
    exit()
    
try:
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Font path
    font_path = "C:/Windows/Fonts/Bahnschrift.ttf"
    
    # Font untuk data utama (34)
    font_data = ImageFont.truetype(font_path, FONT_SIZE_DATA) if os.path.exists(font_path) else ImageFont.load_default(size=FONT_SIZE_DATA)
    # Font untuk header kecil (30)
    font_header_small = ImageFont.truetype(font_path, FONT_SIZE_HEADER_SMALL) if os.path.exists(font_path) else ImageFont.load_default(size=FONT_SIZE_HEADER_SMALL)
    # Font untuk tanggal/jam di header (34)
    font_header_date = ImageFont.truetype(font_path, FONT_SIZE_HEADER_DATE) if os.path.exists(font_path) else ImageFont.load_default(size=FONT_SIZE_HEADER_DATE)
    # Font untuk judul (50)
    font_title = ImageFont.truetype(font_path, FONT_SIZE_TITLE) if os.path.exists(font_path) else ImageFont.load_default(size=FONT_SIZE_TITLE)
    # Font untuk footer (30)
    font_footer = ImageFont.truetype(font_path, FONT_SIZE_FOOTER) if os.path.exists(font_path) else ImageFont.load_default(size=FONT_SIZE_FOOTER)

except Exception as e:
    print(f"❌ Gagal memuat template gambar/font: {e}")
    exit()

# Data posisi dan perbaikan koordinat Y
# Tinggi setiap baris sekitar 100px. FONT_SIZE=34.
# Offset vertikal untuk teks rata di tengah baris kini lebih kecil (sekitar 30px dari Y awal baris).

TEXT_VERTICAL_OFFSET = 30 # Offset Y untuk teks agar di tengah baris (untuk font 34)
ICON_VERTICAL_OFFSET = 15 # Offset Y untuk ikon agar di tengah baris (lebih kecil)

data_positions = [
    # Teks header statis
    {"x": 150, "y": 145, "text": "Ikatan Taruna Meteorologi", "font": font_header_small},
    {"x": 150, "y": 185, "text": "Sekolah Tinggi Meteorologi Klimatologi dan Geofisika", "font": font_header_small},
    {"x": 150, "y": 240, "text": "Prakiraan Cuaca STMKG", "font": font_title}, 
    {"x": 480, "y": 300, "text": "Berlaku", "font": font_header_small}, 

    # Tanggal dan Jam di bagian "Dari" dan "Sampai"
    {"x": 150, "y": 360, "text_prefix": "Dari : ", "cell": (0, "Tanggal"), "cell_jam": (0, "Jam"), "font": font_header_date},
    {"x": 650, "y": 360, "text_prefix": "Sampai : ", "cell": (8, "Tanggal"), "cell_jam": (8, "Jam"), "font": font_header_date},

    # === DATA UTAMA DALAM TABEL (Y disesuaikan ke offset 30) ===
    # Waktu
    {"x": 150, "y": 795 + TEXT_VERTICAL_OFFSET, "cell": (0, "Jam"), "font": font_data},
    {"x": 150, "y": 895 + TEXT_VERTICAL_OFFSET, "cell": (1, "Jam"), "font": font_data},
    {"x": 150, "y": 990 + TEXT_VERTICAL_OFFSET, "cell": (2, "Jam"), "font": font_data},
    {"x": 150, "y": 1090 + TEXT_VERTICAL_OFFSET, "cell": (3, "Jam"), "font": font_data},
    {"x": 150, "y": 1185 + TEXT_VERTICAL_OFFSET, "cell": (4, "Jam"), "font": font_data},
    {"x": 150, "y": 1285 + TEXT_VERTICAL_OFFSET, "cell": (5, "Jam"), "font": font_data},
    {"x": 150, "y": 1380 + TEXT_VERTICAL_OFFSET, "cell": (6, "Jam"), "font": font_data},
    {"x": 150, "y": 1480 + TEXT_VERTICAL_OFFSET, "cell": (7, "Jam"), "font": font_data},

    # Suhu (°C)
    {"x": 450, "y": 795 + TEXT_VERTICAL_OFFSET, "cell": (0, "Suhu (°C)"), "font": font_data}, 
    {"x": 450, "y": 895 + TEXT_VERTICAL_OFFSET, "cell": (1, "Suhu (°C)"), "font": font_data},
    {"x": 450, "y": 990 + TEXT_VERTICAL_OFFSET, "cell": (2, "Suhu (°C)"), "font": font_data},
    {"x": 450, "y": 1090 + TEXT_VERTICAL_OFFSET, "cell": (3, "Suhu (°C)"), "font": font_data},
    {"x": 450, "y": 1185 + TEXT_VERTICAL_OFFSET, "cell": (4, "Suhu (°C)"), "font": font_data},
    {"x": 450, "y": 1285 + TEXT_VERTICAL_OFFSET, "cell": (5, "Suhu (°C)"), "font": font_data},
    {"x": 450, "y": 1380 + TEXT_VERTICAL_OFFSET, "cell": (6, "Suhu (°C)"), "font": font_data},
    {"x": 450, "y": 1480 + TEXT_VERTICAL_OFFSET, "cell": (7, "Suhu (°C)"), "font": font_data},
    
    # Kelembapan (%)
    {"x": 620, "y": 795 + TEXT_VERTICAL_OFFSET, "cell": (0, "Kelembapan (%)"), "font": font_data},
    {"x": 620, "y": 895 + TEXT_VERTICAL_OFFSET, "cell": (1, "Kelembapan (%)"), "font": font_data},
    {"x": 620, "y": 990 + TEXT_VERTICAL_OFFSET, "cell": (2, "Kelembapan (%)"), "font": font_data},
    {"x": 620, "y": 1090 + TEXT_VERTICAL_OFFSET, "cell": (3, "Kelembapan (%)"), "font": font_data},
    {"x": 620, "y": 1185 + TEXT_VERTICAL_OFFSET, "cell": (4, "Kelembapan (%)"), "font": font_data},
    {"x": 620, "y": 1285 + TEXT_VERTICAL_OFFSET, "cell": (5, "Kelembapan (%)"), "font": font_data},
    {"x": 620, "y": 1380 + TEXT_VERTICAL_OFFSET, "cell": (6, "Kelembapan (%)"), "font": font_data},
    {"x": 620, "y": 1480 + TEXT_VERTICAL_OFFSET, "cell": (7, "Kelembapan (%)"), "font": font_data},
    
    # Kecepatan Angin (knots)
    # X dikembalikan ke 850 dan ikon arah angin digeser ke kiri.
    {"x": 850, "y": 795 + TEXT_VERTICAL_OFFSET, "cell": (0, "Kecepatan Angin (knots)"), "font": font_data}, 
    {"x": 850, "y": 895 + TEXT_VERTICAL_OFFSET, "cell": (1, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 990 + TEXT_VERTICAL_OFFSET, "cell": (2, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1090 + TEXT_VERTICAL_OFFSET, "cell": (3, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1185 + TEXT_VERTICAL_OFFSET, "cell": (4, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1285 + TEXT_VERTICAL_OFFSET, "cell": (5, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1380 + TEXT_VERTICAL_OFFSET, "cell": (6, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1480 + TEXT_VERTICAL_OFFSET, "cell": (7, "Kecepatan Angin (knots)")},
    
    # Ikon Cuaca
    {"x": 300, "y": 795 + ICON_VERTICAL_OFFSET, "cell": (0, "File Ikon"), "is_icon": True}, 
    {"x": 300, "y": 895 + ICON_VERTICAL_OFFSET, "cell": (1, "File Ikon"), "is_icon": True},
    {"x": 300, "y": 990 + ICON_VERTICAL_OFFSET, "cell": (2, "File Ikon"), "is_icon": True},
    {"x": 300, "y": 1090 + ICON_VERTICAL_OFFSET, "cell": (3, "File Ikon"), "is_icon": True},
    {"x": 300, "y": 1185 + ICON_VERTICAL_OFFSET, "cell": (4, "File Ikon"), "is_icon": True},
    {"x": 300, "y": 1285 + ICON_VERTICAL_OFFSET, "cell": (5, "File Ikon"), "is_icon": True},
    {"x": 300, "y": 1380 + ICON_VERTICAL_OFFSET, "cell": (6, "File Ikon"), "is_icon": True},
    {"x": 300, "y": 1480 + ICON_VERTICAL_OFFSET, "cell": (7, "File Ikon"), "is_icon": True},

    # Teks Footer
    {"x": 800, "y": 1650, "text": "Sumber : BMKG", "font": font_footer},
    {"x": 780, "y": 1780, "text": "@itm_stmkg", "font": font_footer}, 
]

# Plot
for item in data_positions:
    x, y = item["x"], item["y"]
    
    # Untuk Teks Statis (Header/Footer)
    if "text" in item:
        text_content = item["text"]
        current_font = item.get("font", font_data) 
        draw.text((x, y), text_content, font=current_font, fill="white")
    
    # Untuk Teks dari Data CSV
    elif "cell" in item:
        baris, kolom = item["cell"]
        teks = ambil_nilai(df, baris, kolom)
        current_font = item.get("font", font_data) 

        if "text_prefix" in item: # Untuk "Dari" dan "Sampai" di header
            teks_tanggal = ambil_nilai(df, item["cell"][0], "Tanggal")
            teks_jam = ambil_nilai(df, item["cell_jam"][0], "Jam")
            full_text = f"{item['text_prefix']} {teks_tanggal} {teks_jam}"
            draw.text((x, y), full_text, font=current_font, fill="white")
        
        elif "File Ikon" not in kolom:
            # Logika Penambahan Satuan 
            if "Suhu (°C)" in kolom:
                teks += "°C"
            elif "Kelembapan (%)" in kolom:
                teks += "%"
            elif "Kecepatan Angin (knots)" in kolom:
                teks += " knots"
            draw.text((x, y), teks, font=current_font, fill="white")

            if "Kecepatan Angin" in kolom:
                arah_angin = ambil_nilai(df, baris, "Arah Angin (°)")
                try:
                    angle = float(arah_angin)
                    # X disesuaikan lebih jauh ke kiri agar tidak menimpa angka
                    paste_rotated_icon(img, ikon_arah_path, (x - 80, y + 17), angle) # Y juga disesuaikan lebih kecil (17)
                except ValueError:
                    pass

        elif "File Ikon" in kolom:
            # Ikon cuaca dipanggil menggunakan posisi yang sudah disesuaikan
            paste_ikon_cuaca(img, icon_dir, (x, y), teks)


# Simpan Gambar
os.makedirs(os.path.dirname(output_gambar_path), exist_ok=True) 
try:
    img.save(output_gambar_path)
    print(f"\n✅ Gambar prakiraan selesai dan disimpan di: {output_gambar_path}")
except Exception as e:
    print(f"❌ Gagal menyimpan gambar: {e}")
    exit()

# ====================================================================================================
# BAGIAN 3: PENGIRIMAN EMAIL (TIDAK ADA PERUBAHAN)
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
    # KONFIGURASI EMAIL - PASTIKAN MENGGUNAKAN APP PASSWORD
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
