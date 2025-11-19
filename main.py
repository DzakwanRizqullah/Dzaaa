#====================================================================================================================#
#               Script Created By Penelitian ITMK 2022 K (GitHub Version)                                          #
#====================================================================================================================#

import requests
import csv
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# ====================================================================================================
# SETUP PATH RELATIVE UNTUK GITHUB
# ====================================================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ICON_DIR = os.path.join(OUTPUT_DIR, "ikon_cuaca")
CSV_PATH = os.path.join(OUTPUT_DIR, "prakiraan_cuaca.csv")
TEMPLATE_PATH = os.path.join(OUTPUT_DIR, "3.png")
GAMBAR_PATH = os.path.join(OUTPUT_DIR, "PrakicuITM.png")
os.makedirs(ICON_DIR, exist_ok=True)

# ====================================================================================================
# BAGIAN 1: PENGAMBILAN DATA BMKG DAN SIMPAN CSV
# ====================================================================================================
print("--- Memulai Pengambilan Data BMKG ---")

url = "https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4=36.71.01.1003"
headers = {'User-Agent': 'Mozilla/5.0'}

try:
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.RequestException as e:
    print(f"❌ Gagal mengambil data: {e}")
    exit()

def kmh_to_knots(kmh):
    try:
        return f"{float(kmh)*0.539957:.1f}"
    except:
        return ""

with open(CSV_PATH, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Tanggal","Jam","Cuaca","Suhu (°C)","Kelembapan (%)",
                     "Kecepatan Angin (km/j)","Kecepatan Angin (knots)","Arah Angin (°)","File Ikon"])
    try:
        weather_data_groups = data["data"][0]["cuaca"]
    except (IndexError, KeyError):
        print("⚠️ Data BMKG tidak sesuai.")
        weather_data_groups = []

    for group in weather_data_groups:
        for item in group:
            datetime_str = item.get("local_datetime","")
            tanggal = datetime_str[:10] if len(datetime_str)>=16 else ""
            jam = datetime_str[11:16] if len(datetime_str)>=16 else ""
            cuaca = item.get("weather_desc","")
            suhu = item.get("t","")
            kelembapan = item.get("hu","")
            angin = item.get("ws","")
            arah = item.get("wd_deg","")
            angin_knots = kmh_to_knots(angin)
            ikon_url = item.get("image","")
            ikon_file = ""
            if ikon_url:
                ikon_file = os.path.basename(ikon_url)
                ikon_path = os.path.join(ICON_DIR, ikon_file)
                if not os.path.exists(ikon_path):
                    try:
                        r = requests.get(ikon_url, timeout=10)
                        if r.status_code==200:
                            with open(ikon_path,"wb") as f: f.write(r.content)
                    except: pass
            writer.writerow([tanggal,jam,cuaca,suhu,kelembapan,angin,angin_knots,arah,ikon_file])
print(f"✅ CSV dibuat: {CSV_PATH}")

# ====================================================================================================
# BAGIAN 2: BUAT GAMBAR INFOGRAFIS
# ====================================================================================================
print("\n--- Membuat gambar infografis ---")
try:
    df = pd.read_csv(CSV_PATH)
except:
    print("❌ Gagal membaca CSV")
    exit()

def ambil(df,row,col):
    try:
        val = df.iloc[row][col]
        return "" if pd.isna(val) else str(val)
    except:
        return ""

def paste_icon(base_img, path, pos, angle=0, resize=(60,60)):
    if os.path.exists(path):
        img = Image.open(path).convert("RGBA").resize(resize)
        img = img.rotate(-angle, expand=True, resample=Image.BICUBIC)
        w,h = img.size
        x,y = pos
        base_img.paste(img,(x-w//2,y-h//2),img)

if not os.path.exists(TEMPLATE_PATH):
    print(f"❌ Template {TEMPLATE_PATH} tidak ditemukan")
    exit()
img = Image.open(TEMPLATE_PATH).convert("RGBA")
draw = ImageDraw.Draw(img)
font_path = "C:/Windows/Fonts/Bahnschrift.ttf"
font = ImageFont.truetype(font_path,34) if os.path.exists(font_path) else ImageFont.load_default()
ikon_angin_path = os.path.join(ICON_DIR,"ikon_arah_angin.png")

# Posisi (bisa disesuaikan)
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

]

for item in data_pos:
    x,y = item["x"], item["y"]
    r,c = item["cell"]
    val = ambil(df,r,c)
    if "File Ikon" not in c:
        draw.text((x,y),val,font=font,fill="white")
    if "Kecepatan Angin" in c:
        try:
            angle = float(ambil(df,r,"Arah Angin (°)"))
            paste_icon(img,ikon_angin_path,(x-80,y+10),angle)
        except: pass
    if "File Ikon" in c:
        paste_icon(img,os.path.join(ICON_DIR,val),(x,y),resize=(100,100))

img.save(GAMBAR_PATH)
print(f"✅ Infografis disimpan: {GAMBAR_PATH}")

# ====================================================================================================
# BAGIAN 3: KIRIM EMAIL (GMAIL APP PASSWORD)
# ====================================================================================================
def attach_file(msg,path,type_='image'):
    if not os.path.exists(path): return
    with open(path,"rb") as f:
        fname = os.path.basename(path)
        if type_=='image':
            part = MIMEImage(f.read(),name=fname)
        elif type_=='csv':
            part = MIMEBase('application','octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
        else: return
        part.add_header('Content-Disposition',f'attachment; filename="{fname}"')
        msg.attach(part)

def send_email(img_path,csv_path):
    sender = "dzaa5th@gmail.com"
    password = "necb noft kvfg dxei" # app password
    receiver = "mulmeditmstmkg@gmail.com"
    msg = MIMEMultipart()
    msg['From']=sender
    msg['To']=receiver
    msg['Subject']=f"Prakiraan Cuaca STMKG - {datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText("Terlampir infografis & CSV prakiraan cuaca.","plain"))
    attach_file(msg,img_path,'image')
    attach_file(msg,csv_path,'csv')
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com",587) as server:
            server.starttls(context=context)
            server.login(sender,password)
            server.sendmail(sender,receiver,msg.as_string())
        print(f"✅ Email terkirim ke {receiver}")
    except Exception as e:
        print(f"❌ Gagal kirim email: {e}")

send_email(GAMBAR_PATH,CSV_PATH)
