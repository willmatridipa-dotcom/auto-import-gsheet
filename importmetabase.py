import os
import json
import gspread
import requests
import pandas as pd
import io
from oauth2client.service_account import ServiceAccountCredentials

def get_metabase_data():
    # --- CONFIG METABASE ---
    # Ganti dengan URL Metabase kamu (jangan ada slash / di ujung)
    METABASE_URL = "https://mb-dynamic.rata.id" # Hapus slash di ujung agar konsisten
    USERNAME = "willma.tridipa@rata.id"
    PASSWORD = "metabasedynamic12"
  
    
    # ID Question/Card yang mau ditarik
    CARD_ID = "39" 

    print("--- STEP 1: Login ke Metabase ---")
    try:
        auth_res = requests.post(f"{METABASE_URL}/api/session", json={
            "username": USERNAME, 
            "password": PASSWORD
        }, timeout=15)
        
        if auth_res.status_code != 200:
            print(f"Login Gagal! Status: {auth_res.status_code}")
            return None
            
        session_id = auth_res.json()["id"]
        headers = {"X-Metabase-Session": session_id}
        print("Login Berhasil!")

        print(f"--- STEP 2: Menarik Data Card {CARD_ID} ---")
        # Kita pakai format CSV karena paling enteng buat data ribuan row
        export_res = requests.post(f"{METABASE_URL}/api/card/{CARD_ID}/query/csv", headers=headers, timeout=60)
        
        if export_res.status_code == 200:
            df = pd.read_csv(io.StringIO(export_res.text))
            df = df.fillna("") # Hilangkan NaN agar GSheet gak error
            
            # Konvert ke list of lists (Format yang dimengerti GSheet)
            data_final = [df.columns.values.tolist()] + df.values.tolist()
            print(f"Berhasil menarik {len(data_final)} baris data.")
            return data_final
        else:
            print(f"Gagal tarik data! Status: {export_res.status_code}")
            return None
            
    except Exception as e:
        print(f"Error di Metabase: {e}")
        return None

def upload_to_gsheet(data):
    print("--- STEP 3: Upload ke Google Sheets ---")
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Pastikan file credentials.json ada di folder yang sama
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        
        # ID GSheet Baru yang kamu kasih
        ID_GSHEET = "1OTLX_utgRO_iUNeESw5K83fI8p9sLjWvdXZy7-iuSoQ"
        sh = client.open_by_key(ID_GSHEET)
        ws = sh.worksheet("order_payment")
        
        print("Membersihkan sheet lama...")
        ws.batch_clear(["A2:L"])
        
        print("Mengirim data baru...")
        ws.update(values=data, range_name='A1')
        print("--- SEMUA SELESAI! Cek Google Sheet kamu ---")
        
    except Exception as e:
        print(f"Error di GSheet: {e}")

if __name__ == "__main__":
    hasil_data = get_metabase_data()
    if hasil_data:
        upload_to_gsheet(hasil_data)