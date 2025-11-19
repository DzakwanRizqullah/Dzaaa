#====================================================================================================================#
#                 Script Created By Penelitian ITMK 2022 K (GitHub Friendly + Email)                               #
#====================================================================================================================#

import requests, csv, os, pandas as pd
from PIL import Image, ImageDraw, ImageFont
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

# ====================================================================================================
# BAGIAN 0: SET PATH RELATIF REPOSITORY
# ====================================================================================================
repo_root = os.getcwd()  # Root folder repository
output_dir = os.path.join(repo_root, "output")
icon_dir = os.path.join(output_dir, "ikon_cuaca")
csv_path = os.path.join(output_dir, "prakiraan_cuaca.csv")
template_path = os.path.join(output_dir, "3.png")
output_gambar_path = os.path.join(output_dir, "PrakicuITM.png")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(icon_dir, exist_ok=True)

# ====================================================================================================
# BAGIAN 1: PENGAMBILAN DATA BMKG, PENYIMPANAN CSV, DAN DOWNLOAD IKON
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
    try: return f"{float(kmh)*0.539957:.1f}"
    except: return ""

with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Tanggal","Jam","Cuaca","Suhu (°C)","Kelembapan (%)",
                     "Kecepatan Angin (km/j)","Kecepatan Angin (knots)","Arah Angin (°)","File Ikon"])
    try: weather_data_groups = data["data"][0]["cuaca"]
    except: weather_data_groups = []

    for group in weather_data_groups:
        for item in group:
            datetime_str = item.get("local_datetime","")
            Tanggal = datetime_str[0:10] if len(datetime_str)>=16 else ""
            jam = datetime_str[11:16] if len(datetime_str)>=16 else ""
            cuaca = item.get("weather_desc","")
            suhu = item.get("t","")
            kelembapan = item.get("hu","")
            angin = item.get("ws","")
            arah_angin = item.get("wd_deg","")
            angin_knots = kmh_to_knots(angin)

            ikon_url = item.get("image","")
            ikon_filename = ""
            if ikon_url:
                ikon_filename = ikon_url.split("/")[-1]
                ikon_path = os.path.join(icon_dir, ikon_filename)
                if not os.path.exists(ikon_path):
                    try:
                        r = requests.get(ikon_url, timeout=10)
                        if r.status_code==200: open(ikon_path,"wb").write(r.content)
                    except: pass
            writer.writerow([Tanggal,jam,cuaca,suhu,kelembapan,angin,angin_knots,arah_angin,ikon_filename])

print(f"✅ CSV tersimpan di: {csv_path}")

# ====================================================================================================
# BAGIAN 2: PEMBUATAN GAMBAR INFOGRAFIS
# ====================================================================================================
print("\n--- Membuat Gambar Infografis ---")
try: df = pd.read_csv(csv_path)
except: exit("❌ Gagal membaca CSV")

def ambil_nilai(df, baris, kolom):
    try: return str(df.iloc[baris][kolom]).strip() if kolom in df.columns else ""
    except: return ""

def paste_rotated_icon(base_img, icon_path, center_position, angle):
    if os.path.exists(icon_path):
        try:
            ikon_img = Image.open(icon_path).convert("RGBA").resize((60,60))
            ikon_img_rotated = ikon_img.rotate(-angle,expand=True,resample=Image.BICUBIC)
            w,h=center_position
            cx,cy=center_position
            base_img.paste(ikon_img_rotated,(cx-w//2,cy-h//2),ikon_img_rotated)
        except: pass

def paste_ikon_cuaca(base_img, ikon_dir, position, ikon_filename, default_width=100):
    ikon_filename = os.path.splitext(ikon_filename)[0]+".png"
    ikon_path = os.path.join(ikon_dir, ikon_filename)
    if os.path.exists(ikon_path):
        try:
            ikon_img = Image.open(ikon_path).convert("RGBA")
            target_width = 130 if "hujan" in ikon_filename.lower() else default_width
            scale_ratio = target_width / ikon_img.width
            ikon_img = ikon_img.resize((target_width,int(ikon_img.height*scale_ratio)),Image.LANCZOS)
            x,y=position
            base_img.paste(ikon_img,(x,y),ikon_img)
        except: pass

if not os.path.exists(template_path): exit(f"❌ Template 3.png tidak ditemukan di {template_path}")
img = Image.open(template_path).convert("RGBA")
draw = ImageDraw.Draw(img)
font_path = "C:/Windows/Fonts/Bahnschrift.ttf"
font = ImageFont.truetype(font_path,34) if os.path.exists(font_path) else ImageFont.load_default()
ikon_arah_path = os.path.join(icon_dir,"ikon_arah_angin.png")

data_pos = [
    {"x":150,"y":390,"cell":(0,"Tanggal")},
    {"x":350,"y":390,"cell":(0,"Jam")},
    {"x":450,"y":795,"cell":(0,"Suhu (°C)")},
    {"x":620,"y":795,"cell":(0,"Kelembapan (%)")},
    {"x":850,"y":795,"cell":(0,"Kecepatan Angin (knots)")},
    {"x":320,"y":780,"cell":(0,"File Ikon")},
]

for item in data_pos:
    x,y=item["x"],item["y"]
    baris,kolom=item["cell"]
    teks=ambil_nilai(df,baris,kolom)
    if "File Ikon" not in kolom: draw.text((x,y),teks,font=font,fill="white")
    if "Kecepatan Angin" in kolom:
        try: paste_rotated_icon(img,ikon_arah_path,(x-80,y+10),float(ambil_nilai(df,baris,"Arah Angin (°)")))
        except: pass
    if "File Ikon" in kolom: paste_ikon_cuaca(img,icon_dir,(x,y),teks)

img.save(output_gambar_path)
print(f"✅ Infografis tersimpan di: {output_gambar_path}")

# ====================================================================================================
# BAGIAN 3: PENGIRIMAN EMAIL DENGAN LAMPIRAN
# ====================================================================================================
def attach_file_to_email(msg,file_path,file_type='image'):
    if not os.path.exists(file_path): return
    with open(file_path,"rb") as f:
        filename=os.path.basename(file_path)
        if file_type=='image': part=MIMEImage(f.read(),name=filename)
        elif file_type=='csv':
            from email.mime.base import MIMEBase
            part=MIMEBase('application','octet-stream')
            part.set_payload(f.read())
            from email import encoders
            encoders.encode_base64(part)
        else: return
        part.add_header('Content-Disposition',f'attachment; filename="{filename}"')
        msg.attach(part)

def send_email_with_attachments(image_path,csv_path):
    smtp_server="smtp.gmail.com"
    port=587
    sender_email="dzaa5th@gmail.com"
    password="necb noft kvfg dxei"  # Ganti dengan App Password Gmail
    recipient_email="mulmeditmstmkg@gmail.com"

    msg=MIMEMultipart()
    msg['From']=sender_email
    msg['To']=recipient_email
    msg['Subject']=f"Prakiraan Cuaca STMKG - {datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText("Terlampir infografis dan CSV prakiraan cuaca terbaru.","plain"))

    attach_file_to_email(msg,image_path,'image')
    attach_file_to_email(msg,csv_path,'csv')

    context=ssl.create_default_context()
    try:
        print("\n--- Mengirim Email ---")
        with smtplib.SMTP(smtp_server,port) as server:
            server.starttls(context=context)
            server.login(sender_email,password)
            server.sendmail(sender_email,recipient_email,msg.as_string())
        print(f"✅ Email berhasil dikirim ke: {recipient_email}")
    except Exception as e:
        print(f"❌ Gagal mengirim email: {e}")

# Kirim email
send_email_with_attachments(output_gambar_path,csv_path)
