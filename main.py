Tentu. Saya akan memperbaiki masalah font dan masalah penanganan *path* untuk gambar template (`3.png`) dan ikon arah angin agar konsisten dengan struktur folder yang Anda sebutkan (`ikon_cuaca` di dalam `output_dir`) dan menggunakan GitHub Action/lingkungan eksekusi yang lebih fleksibel.

### 📝 Ringkasan Perubahan:

1.  **Variabel Font:** Menambahkan variabel `FONT_SIZE = 180` di awal.
2.  **Pemuatan Font:** Menggunakan `FONT_SIZE` yang baru (`180`) untuk memastikan font kembali besar, dan memastikan penanganan *fallback* yang tepat.
3.  **Path Gambar:** Mengganti path absolut (`ikon_arah_path` dan `template_path`) agar merujuk ke lokasi yang Anda tentukan (`output_dir` dan `icon_dir`).
4.  **Koordinat Y:** Menyesuaikan koordinat `Y` agar teks yang lebih besar (`180`) tetap berada di tengah baris template.

Berikut adalah skrip lengkapnya:

```python
#====================================================================================================================#
#                                               Script Created By Penelitian ITMK 2022 K                             #
#                                 (FIXED: FONT SIZE 180 & PATH LOKAL/GITHUB)                           #
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
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# ====================================================================================================
# KONFIGURASI PATH & FONT (Bagian yang Diubah/Ditambahkan)
# ====================================================================================================

# Folder output utama
output_dir = r"D:\Prakiraan_Cuaca_STMKG"
icon_dir = os.path.join(output_dir, "ikon_cuaca")
csv_path = os.path.join(output_dir, "prakiraan_cuaca.csv")
output_gambar_path = r"D:\Prakicu\PrakicuITM.png" # Path final gambar

# Path File Template dan Ikon Arah Angin (DISESUAIKAN)
# Template 3.png berada di D:\Prakiraan_Cuaca_STMKG
template_path = os.path.join(output_dir, "3.png") 
# Ikon arah angin berada di D:\Prakiraan_Cuaca_STMKG\ikon_cuaca
ikon_arah_path = os.path.join(icon_dir, "ikon_arah_angin.png") 

# ✅ FONT SIZE DITINGKATKAN KE 180
FONT_SIZE = 180 

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
    # icon_path sudah diatur di luar fungsi: ikon_arah_path = os.path.join(icon_dir, "ikon_arah_angin.png")
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
# template_path sudah disesuaikan di bagian konfigurasi.
if not os.path.exists(template_path):
    print(f"❌ File template gambar '3.png' tidak ditemukan di: {template_path}. Tidak bisa membuat gambar.")
    exit()
    
try:
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font_path = "C:/Windows/Fonts/Bahnschrift.ttf"
    # ✅ PERUBAHAN UTAMA: MENGGUNAKAN FONT_SIZE=180 YANG BARU DIDEFINISIKAN
    font = ImageFont.truetype(font_path, FONT_SIZE) if os.path.exists(font_path) else ImageFont.load_default()

    # ikon_arah_path sudah disesuaikan di bagian konfigurasi.
except Exception as e:
    print(f"❌ Gagal memuat template gambar/font: {e}")
    exit()

# Data posisi (Koordinat Y disesuaikan untuk FONT_SIZE=180, bukan 34)
# Penyesuaian Y sekitar -25 dari nilai awal agar teks berada di tengah baris
data = [
    # Header (Tidak diubah)
    {"x": 150, "y": 390, "cell": (0, "Tanggal")},
    {"x": 350, "y": 390, "cell": (0, "Jam")},
    {"x": 730, "y": 390, "cell": (8, "Tanggal")},
    {"x": 930, "y": 390, "cell": (8, "Jam")},
    
    # Suhu (°C) - Y disesuaikan
    {"x": 450, "y": 770, "cell": (0, "Suhu (°C)")}, 
    {"x": 450, "y": 870, "cell": (1, "Suhu (°C)")},
    {"x": 450, "y": 965, "cell": (2, "Suhu (°C)")},
    {"x": 450, "y": 1065, "cell": (3, "Suhu (°C)")},
    {"x": 450, "y": 1160, "cell": (4, "Suhu (°C)")},
    {"x": 450, "y": 1260, "cell": (5, "Suhu (°C)")},
    {"x": 450, "y": 1355, "cell": (6, "Suhu (°C)")},
    {"x": 450, "y": 1455, "cell": (7, "Suhu (°C)")},
    
    # Kelembapan (%) - Y disesuaikan
    {"x": 620, "y": 770, "cell": (0, "Kelembapan (%)")},
    {"x": 620, "y": 870, "cell": (1, "Kelembapan (%)")},
    {"x": 620, "y": 965, "cell": (2, "Kelembapan (%)")},
    {"x": 620, "y": 1065, "cell": (3, "Kelembapan (%)")},
    {"x": 620, "y": 1160, "cell": (4, "Kelembapan (%)")},
    {"x": 620, "y": 1260, "cell": (5, "Kelembapan (%)")},
    {"x": 620, "y": 1355, "cell": (6, "Kelembapan (%)")},
    {"x": 620, "y": 1455, "cell": (7, "Kelembapan (%)")},
    
    # Kecepatan Angin (knots) - Y disesuaikan
    {"x": 850, "y": 770, "cell": (0, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 867, "cell": (1, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 967, "cell": (2, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1062, "cell": (3, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1162, "cell": (4, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1260, "cell": (5, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1355, "cell": (6, "Kecepatan Angin (knots)")},
    {"x": 850, "y": 1455, "cell": (7, "Kecepatan Angin (knots)")},
    
    # Ikon Cuaca - Y disesuaikan
    {"x": 320, "y": 755, "cell": (0, "File Ikon")},
    {"x": 320, "y": 842, "cell": (1, "File Ikon")},
    {"x": 320, "y": 942, "cell": (2, "File Ikon")},
    {"x": 320, "y": 1040, "cell": (3, "File Ikon")},
    {"x": 320, "y": 1140, "cell": (4, "File Ikon")},
    {"x": 320, "y": 1240, "cell": (5, "File Ikon")},
    {"x": 320, "y": 1333, "cell": (6, "File Ikon")},
    {"x": 320, "y": 1431, "cell": (7, "File Ikon")},
]

# Plot
for item in data:
    x, y = item["x"], item["y"]
    baris, kolom = item["cell"]
    teks = ambil_nilai(df, baris, kolom)

    # Logika penambahan satuan (untuk tampilan yang lebih baik)
    if "Suhu (°C)" in kolom:
        teks += "°C"
    elif "Kelembapan (%)" in kolom:
        teks += "%"
    elif "Kecepatan Angin (knots)" in kolom:
        teks += " knots"

    if "File Ikon" not in kolom:
        draw.text((x, y), teks, font=font, fill="white")

    if "Kecepatan Angin" in kolom:
        arah_angin = ambil_nilai(df, baris, "Arah Angin (°)")
        try:
            angle = float(arah_angin)
            # Posisikan ikon arah angin agar sejajar dengan teks yang lebih besar (y + 25)
            paste_rotated_icon(img, ikon_arah_path, (x - 80, y + 25), angle) # Y disesuaikan
        except ValueError:
            pass

    if "File Ikon" in kolom:
        paste_ikon_cuaca(img, icon_dir, (x, y), teks)

# Simpan Gambar
output_gambar_dir = os.path.dirname(output_gambar_path)
os.makedirs(output_gambar_dir, exist_ok=True) 

try:
    img.save(output_gambar_path)
    print(f"\n✅ Gambar prakiraan selesai dan disimpan di: {output_gambar_path}")
except Exception as e:
    print(f"❌ Gagal menyimpan gambar: {e}")
    exit()

# ====================================================================================================
# BAGIAN 3: PENGIRIMAN EMAIL (Kode ini tetap sama)
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
                from email.mime.base import MIMEBase
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                from email import encoders
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
# Menggunakan variabel global csv_path dan output_gambar_path
send_email_with_attachments(output_gambar_path, csv_path)
```
