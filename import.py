import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Setup Izin Akses
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

def import_paling_ringan():
    try:
        # --- SUMBER ---
        id_sumber = "1capqvkCLr0RdS-mXsCDZVzVBvtULZqM22isFIT6fWtE"
        print("Membuka sheet sumber...")
        sh_sumber = client.open_by_key(id_sumber).worksheet("Pengiriman")
        
        # JURUS RINGAN: Ambil nilai mentah (Unformatted)
        # Ini akan mengabaikan rumus/format yang bikin berat
        print("Menarik data mentah (Value Only)...")
        data = sh_sumber.get_all_values(value_render_option='UNFORMATTED_VALUE')
        
        if not data:
            print("Data sumber kosong!")
            return
            
        print(f"Berhasil mengambil {len(data)} baris data.")

        # --- TUJUAN ---
        id_tujuan = "1UrKPAcelPp8_b1M-RPd6v-s7rTemr4gKm3KbK1l2MyA"
        print("Membuka sheet tujuan...")
        sh_tujuan = client.open_by_key(id_tujuan).worksheet("pengirman new")
        
        # Bersihkan tujuan dulu
        print("Membersihkan sheet tujuan...")
        sh_tujuan.clear()
        
        # Kirim data sekaligus
        print("Mengirim data ke tujuan...")
        sh_tujuan.update(values=data, range_name='A1')
        
        print("--- SELESAI! Data berhasil dipindahkan ---")

    except Exception as e:
        print(f"Gagal lagi karena: {e}")

if __name__ == "__main__":
    import_paling_ringan()