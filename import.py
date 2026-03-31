import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def import_paling_ringan():
    try:
        # 1. Setup Izin Akses (Jalur Aman untuk GitHub)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # MENGAMBIL RAHASIA DARI GITHUB SECRETS
        secret_data = os.getenv('GCP_SERVICE_ACCOUNT')
        
        if secret_data:
            # Jika jalan di GitHub
            creds_json = json.loads(secret_data)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        else:
            # Jika jalan di laptop kamu (buat ngetes lokal)
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            
        client = gspread.authorize(creds)
        
        # --- LANJUTAN KODE SUMBER ---
        id_sumber = "1capqvkCLr0RdS-mXsCDZVzVBvtULZqM22isFIT6fWtE"
        print("Membuka sheet sumber...")
        sh_sumber = client.open_by_key(id_sumber).worksheet("Pengiriman")
        
        print("Menarik data mentah...")
        data = sh_sumber.get_all_values(value_render_option='UNFORMATTED_VALUE')
        
        if not data:
            print("Data sumber kosong!")
            return

        # --- TUJUAN ---
        id_tujuan = "1UrKPAcelPp8_b1M-RPd6v-s7rTemr4gKm3KbK1l2MyA"
        print("Membuka sheet tujuan...")
        sh_tujuan = client.open_by_key(id_tujuan).worksheet("pengirman new")
        
        print("Membersihkan & Mengirim data...")
        sh_tujuan.clear()
        sh_tujuan.update(values=data, range_name='A1')
        
        print("--- SELESAI! Data berhasil dipindahkan ---")

    except Exception as e:
        print(f"Gagal karena: {e}")

if __name__ == "__main__":
    import_paling_ringan()
