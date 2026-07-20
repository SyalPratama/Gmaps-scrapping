# Google Maps Scraper (Playwright)

Tools untuk mengambil data tempat (nama, alamat, telepon, rating, jumlah review) dari Google Maps berdasarkan kata kunci pencarian, lalu menyimpannya ke file Excel.

## Fitur

- Kata kunci pencarian, jumlah data, jumlah scroll, dan mode headless bisa diatur langsung lewat input saat script dijalankan.
- Progress bar (tqdm) untuk memantau proses scroll dan ekstraksi detail.
- Mode headless opsional — browser bisa disembunyikan agar proses lebih cepat dan ringan.
- Logging otomatis ke file `.txt`, sehingga riwayat proses dan error tetap tersimpan.
- Filter otomatis: tempat dengan nomor telepon rumah/kantor (bukan nomor HP) akan dilewati.
- Output rapi dalam format `.xlsx` dengan lebar kolom otomatis menyesuaikan isi.

## Alur Proses

![Alur Proses Scraping](diagram_proses.png)

1. **Input dari user** — kata kunci pencarian (contoh: `cafe di dago bandung`), jumlah data yang diinginkan, jumlah scroll, dan pilihan mode headless.
2. **Bentuk URL pencarian** — kata kunci di-encode otomatis menjadi URL pencarian Google Maps.
3. **Buka browser** — Playwright membuka Chromium, sesuai mode headless yang dipilih.
4. **Scroll otomatis** — panel daftar tempat di-scroll berulang kali agar lebih banyak tempat termuat.
5. **Kumpulkan link unik** — semua link tempat yang terdeteksi disaring agar tidak ada duplikat.
6. **Ambil detail tiap tempat** — nama, alamat, telepon, rating, dan jumlah review diambil satu per satu.
7. **Filter nomor rumah** — tempat dengan nomor telepon berformat landline (bukan diawali `08`) otomatis dilewati.
8. **Simpan ke Excel** — seluruh data yang lolos filter disimpan ke file `.xlsx`.
9. **Log tersimpan** — seluruh proses dan error dicatat ke file log agar bisa ditelusuri ulang.

## Contoh Hasil

![Contoh Hasil Output](contoh_hasil.png)

File Excel yang dihasilkan otomatis diberi nama sesuai kata kunci pencarian, misalnya:

```
Result_cafe_di_dago_bandung.xlsx
```

Kolom yang tersedia di dalam file:

| Kolom | Keterangan |
|---|---|
| No | Nomor urut data |
| Nama Tempat | Nama tempat/bisnis |
| Rating | Rating Google Maps (angka desimal) |
| Jumlah Review | Total jumlah ulasan |
| Alamat | Alamat lengkap tempat |
| Telepon | Nomor HP (nomor rumah/kantor otomatis di-skip) |

## Instalasi

1. Buat virtual environment (disarankan):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependency:
   ```bash
   pip install -r requirements.txt
   ```

3. Install browser Chromium untuk Playwright:
   ```bash
   playwright install chromium
   ```

   Kalau dijalankan di Linux/WSL dan browser gagal terbuka karena library sistem belum lengkap:
   ```bash
   playwright install-deps chromium
   ```

## Cara Menjalankan

```bash
python3 tools.py
```

Script akan menanyakan:

```
Masukkan kata kunci pencarian (contoh: cafe di Nama kota):
Berapa banyak data yang ingin diambil? (default 50):
Berapa kali scroll untuk memuat data? (default 15):
Jalankan browser tersembunyi/headless? (y/n, default n):
```

Setelah selesai, file Excel dan file log akan tersimpan di folder yang sama dengan script.

## Catatan

- Semakin besar jumlah scroll, semakin banyak tempat yang bisa terdeteksi, tapi proses juga semakin lama.
- Mode headless (`y`) direkomendasikan setelah proses sudah stabil, karena lebih cepat dan hemat resource.
- Tools ini bergantung pada struktur HTML Google Maps yang bisa berubah sewaktu-waktu. Jika ekstraksi gagal total, kemungkinan selector CSS di dalam script perlu disesuaikan ulang.
- Gunakan secara wajar dan sesuai kebijakan penggunaan Google Maps.
