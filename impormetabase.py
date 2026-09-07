"""
========================================================
   ROBOT PEMBUAT BANYAK TABEL BIGQUERY DARI GSHEET
   VERSION: v12.7 (Ultra Fast + Auto-Retry)
========================================================
"""

import os
import re
import json
import time
import random
import pandas as pd
import gspread
from google.oauth2 import service_account
from google.cloud import bigquery

SCRIPT_VERSION = "v12.7-anti-503"

# ============================================================
# KONFIGURASI
# ============================================================
CONFIG_SHEET_URL = "https://docs.google.com/spreadsheets/d/1y_Z8GO2nrUFVwUv-_PnTgJL3NKQwu7koNNtfh1VRaEY"
CONFIG_TAB_NAME  = "config"
BQ_PROJECT     = "backup-444202"
BQ_DATASET     = "DataLabReady"


def buat_credentials():
    scopes = [
        "https://www.googleapis.com/auth/bigquery",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]
    if "GCP_SERVICE_ACCOUNT" in os.environ:
        info = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)
    
    path_kunci_lokal = os.path.join(os.path.dirname(__file__), "kunci-bg.json")
    return service_account.Credentials.from_service_account_file(path_kunci_lokal, scopes=scopes)


def buat_satu_tabel_native(client, creds, table_name, gsheet_url, sheet_name):
    # Sanitize Nama Tabel
    clean_table_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(table_name).strip()).strip('_')
    table_id = f"{BQ_PROJECT}.{BQ_DATASET}.{clean_table_name}"

    gc = gspread.authorize(creds)

    # 1. Ambil Data (Retry Logic Exponential Backoff khusus Anti-503)
    data = None
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            sh = gc.open_by_url(gsheet_url)
            ws = sh.worksheet(sheet_name)
            data = ws.get_all_records()
            break
        except Exception as e:
            err_msg = str(e)
            if ("503" in err_msg or "429" in err_msg or "Quota" in err_msg or "unavailable" in err_msg.lower()) and attempt < max_retries:
                sleep_time = (2 ** attempt) + random.uniform(1, 2)
                print(f"   ⚠️ Google API Sibuk/503. Retry {attempt}/{max_retries} dalam {sleep_time:.1f} detik...")
                time.sleep(sleep_time)
            else:
                raise e

    if not data:
        print(f"    SKIP: Sheet '{sheet_name}' kosong!\n")
        return

    # 2. Parsing Data & Pembersihan Ringan
    df = pd.DataFrame(data)

    # A. Clean Header Kolom
    clean_cols = {}
    seen_cols = set()
    for col in df.columns:
        c_clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(col).strip()).strip('_')
        if not c_clean or c_clean[0].isdigit():
            c_clean = f"col_{c_clean}"
        
        orig = c_clean
        counter = 1
        while c_clean in seen_cols:
            c_clean = f"{orig}_{counter}"
            counter += 1
        seen_cols.add(c_clean)
        clean_cols[col] = c_clean

    df.rename(columns=clean_cols, inplace=True)

    # B. Clean Baris Kosong & Trim White space
    df.dropna(how='all', inplace=True)
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

    # 3. Direct Overwrite (WRITE_TRUNCATE) + Server-side Autodetect
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True
    )
    
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Menunggu hasil dari server BigQuery

    print(f"   BERHASIL! Table '{clean_table_name}' diperbarui!\n")
    
    # Micro-delay cegah hit rate limit beruntun
    time.sleep(1.2)


def baca_config_sheet(creds):
    gc = gspread.authorize(creds)
    semua = []
    
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            ws = gc.open_by_url(CONFIG_SHEET_URL).worksheet(CONFIG_TAB_NAME)
            semua = ws.get_all_records()
            break
        except Exception as e:
            err_msg = str(e)
            if ("503" in err_msg or "429" in err_msg or "Quota" in err_msg) and attempt < max_retries:
                sleep_time = (2 ** attempt) + random.uniform(1, 2)
                time.sleep(sleep_time)
            else:
                raise e

    bersih = []
    for baris in semua:
        t_name = str(baris.get("table_name", "")).strip()
        if t_name:
            bersih.append({
                "table_name": t_name,
                "gsheet_url": str(baris.get("gsheet_url", "")).strip(),
                "sheet_name": str(baris.get("sheet_name", "")).strip(),
            })

    print(f"Ditemukan {len(bersih)} tabel yang akan diproses.\n")
    return bersih


def jalankan_semua():
    print("=" * 60)
    print(f"     ROBOT NATIVE TABLE BIGQUERY ({SCRIPT_VERSION})")
    print("=" * 60 + "\n")

    creds  = buat_credentials()
    client = bigquery.Client(credentials=creds, project=BQ_PROJECT)
    daftar_tabel = baca_config_sheet(creds)

    berhasil, gagal = 0, 0

    for nomor, baris in enumerate(daftar_tabel, start=1):
        print(f"[{nomor}/{len(daftar_tabel)}] Memproses '{baris['table_name']}'...")
        try:
            buat_satu_tabel_native(
                client, creds, baris["table_name"],
                baris["gsheet_url"], baris["sheet_name"]
            )
            berhasil += 1
        except Exception as e:
            print(f"    GAGAL: {e}\n")
            gagal += 1

    print("=" * 60)
    print(f"     SELESAI! Berhasil: {berhasil} | Gagal: {gagal}")
    print("=" * 60)


if __name__ == "__main__":
    jalankan_semua()
