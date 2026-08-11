
import sys

from sqlalchemy import text

from app.db.database import engine, init_db
from app.models import event 


def main() -> None:
    print("1. Mencoba konek ke database...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"   OK — terkoneksi. Postgres version: {version}")
    except Exception as e:
        print(f"   GAGAL konek ke database: {e}")
        sys.exit(1)

    print("2. Membuat tabel (jika belum ada)...")
    try:
        init_db()
        print("   OK — tabel berhasil dibuat / sudah ada.")
    except Exception as e:
        print(f"   GAGAL membuat tabel: {e}")
        sys.exit(1)

    print("3. Verifikasi tabel 'network_events' ada...")
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name='network_events';"
                )
            )
            row = result.fetchone()
            if row:
                print("   OK — tabel 'network_events' ditemukan.")
            else:
                print("   WARNING — tabel tidak ditemukan setelah init_db().")
    except Exception as e:
        print(f"   GAGAL verifikasi: {e}")
        sys.exit(1)

    print("\nSemua tes koneksi & migrasi BERHASIL.")


if __name__ == "__main__":
    main()