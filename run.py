import argparse
import uvicorn
import os
from dotenv import load_dotenv

# Memuat variabel lingkungan dari file .env
load_dotenv()

def run_app():
    """
    Menjalankan aplikasi FastAPI dengan Uvicorn berdasarkan argumen command line.
    Gunakan:
        python run.py                  - Jalankan dengan pengaturan default
        python run.py --port 8001      - Ganti port
        python run.py --host 0.0.0.0   - Buat dapat diakses dari jaringan
        python run.py --reload         - Mode development dengan auto-reload
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Jalankan FastAPI CRUD Demo')
    
    # Tambahkan argumen
    parser.add_argument('--host', type=str, default='127.0.0.1', 
                        help='Host untuk menjalankan aplikasi (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8000, 
                        help='Port untuk menjalankan aplikasi (default: 8000)')
    parser.add_argument('--reload', action='store_true',
                        help='Aktifkan auto-reload saat file berubah')
    parser.add_argument('--prod', action='store_true',
                        help='Jalankan dalam mode produksi (workers=4, tanpa reload)')
    
    # Parse argumen
    args = parser.parse_args()
    
    # Set default log level
    log_level = "info"
    
    # Set workers
    workers = 4 if args.prod else 1
    
    # Cek DB connection
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        print("PERINGATAN: DATABASE_URL tidak ditemukan di .env")
        print("Pastikan file .env ada dan berisi DATABASE_URL yang valid")
    
    # Tampilkan informasi startup
    print(f"Menjalankan FastAPI CRUD Demo di http://{args.host}:{args.port}")
    print(f"Mode: {'Production' if args.prod else 'Development'}")
    if args.reload:
        print("Auto-reload diaktifkan")
    
    # Konfigurasi Uvicorn dan jalankan
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload and not args.prod,
        workers=workers,
        log_level=log_level
    )

if __name__ == "__main__":
    run_app()