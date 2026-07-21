import asyncio
import sys
import re
import logging
from datetime import datetime
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
import pandas as pd
from tqdm import tqdm

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# =========================
# SETUP LOGGING
# =========================
nama_file_log = f"scraping_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

logger = logging.getLogger("masukmaps")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

file_handler = logging.FileHandler(nama_file_log, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)


def buat_url_pencarian(keyword: str) -> str:
    """
    Membentuk URL pencarian Google Maps dari keyword bebas,
    misalnya: "cafe di semarang", "bengkel motor bandung", dll.
    """
    keyword_encoded = quote_plus(keyword.strip())
    url = f"https://www.google.com/maps/search/{keyword_encoded}"
    return url


def buat_nama_file(keyword: str) -> str:
    """
    Membuat nama file excel yang aman dari keyword pencarian.
    Contoh: "cafe di semarang" -> Result_cafe_di_semarang.xlsx
    """
    keyword_bersih = re.sub(r'[^a-zA-Z0-9]+', '_', keyword.strip()).strip('_')
    if not keyword_bersih:
        keyword_bersih = "hasil_pencarian"
    return f"Result_{keyword_bersih}.xlsx"


def is_nomor_hp(telepon: str) -> bool:
    """
    Mengecek apakah nomor telepon adalah nomor HP (mobile),
    bukan nomor rumah/kantor (landline).

    Nomor HP Indonesia selalu diawali 08 (setelah dibersihkan),
    atau +628 / 628 dalam format internasional.
    Nomor rumah/kantor diawali kode area seperti 021, 022, 024, 031, dll.
    """
    if not telepon or telepon == "tidak ada telepon":
        return False

    bersih = re.sub(r"[\s\-\(\)]", "", telepon)

    if bersih.startswith("+62"):
        bersih = "0" + bersih[3:]
    elif bersih.startswith("62"):
        bersih = "0" + bersih[2:]

    return bool(re.match(r"^08\d{7,12}$", bersih))


async def run_masukmaps():

    # === INPUT DARI USER ===
    keyword = input("Masukkan kata kunci pencarian (contoh: cafe di Nama kota): ").strip()
    if not keyword:
        print("[X] Kata kunci tidak boleh kosong.")
        return

    input_jumlah = input("Berapa banyak data yang ingin diambil? (default 50): ").strip()
    try:
        target_maksimal = int(input_jumlah) if input_jumlah else 50
    except ValueError:
        print("[!] Input jumlah tidak valid, menggunakan default 50.")
        target_maksimal = 50

    input_scroll = input("Berapa kali scroll untuk memuat data? (default 15): ").strip()
    try:
        jumlah_scroll = int(input_scroll) if input_scroll else 15
    except ValueError:
        print("[!] Input jumlah scroll tidak valid, menggunakan default 15.")
        jumlah_scroll = 15

    input_headless = input("Jalankan browser tersembunyi/headless? (y/n, default n): ").strip().lower()
    mode_headless = input_headless == "y"

    # --- Opsi filter nomor rumah/kantor (landline) ---
    input_skip_landline = input(
        "Lewati tempat dengan nomor rumah/kantor (bukan HP)? (y/n, default y): "
    ).strip().lower()
    skip_landline = (input_skip_landline != "n")  # default y

    # --- Opsi filter tempat tanpa nomor telepon sama sekali ---
    input_skip_kosong = input(
        "Lewati tempat yang tidak memiliki nomor telepon sama sekali? (y/n, default n): "
    ).strip().lower()
    skip_tanpa_telepon = (input_skip_kosong == "y")  # default n

    url = buat_url_pencarian(keyword)
    nama_file = buat_nama_file(keyword)

    user_agent_asli = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    logger.info(f"[*] Kata kunci pencarian : {keyword}")
    logger.info(f"[*] URL yang digunakan   : {url}")
    logger.info(f"[*] Mode headless        : {mode_headless}")
    logger.info(f"[*] Lewati nomor rumah   : {skip_landline}")
    logger.info(f"[*] Lewati tanpa telepon : {skip_tanpa_telepon}")
    logger.info(f"[*] File log disimpan di : {nama_file_log}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=mode_headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(user_agent=user_agent_asli, viewport={"width": 1280, "height": 720})

        page = await context.new_page()
        # Trik Pro: Blokir semua gambar dan font agar tidak di-download oleh bot
        # await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf}", lambda route: route.abort())

        try:
            logger.info("[*] Mengunjungi google maps dengan kata kunci yang dimasukkan...")
            await page.goto(url, wait_until="commit", timeout=60000)

            logger.info("[*] Menunggu daftar tempat muncul...")
            await page.wait_for_selector('div[role="feed"]', timeout=30000)

            await page.wait_for_timeout(5000)

            panel_kiri = page.locator('div[role="feed"]')

            logger.info("[*] Memulai scroll otomatis pada panel kiri...")
            for i in tqdm(range(jumlah_scroll), desc="Scroll", unit="scroll"):
                await panel_kiri.evaluate("el => el.scrollBy(0, 3000)")
                logger.debug(f"   scroll ke-{i+1} selesai, menunggu data baru dimuat...")
                await asyncio.sleep(4.5)

            kartu_tempat = page.locator("a[href*='/maps/place/']")
            jumlah_terdeteksi = await kartu_tempat.count()

            logger.info(f"[!] Berhasil! total tempat yang terdeteksi setelah scroll: {jumlah_terdeteksi}")

            logger.info("[*] Menyaring link agar tidak duplikat...")
            link_unik = []
            for i in range(jumlah_terdeteksi):
                link = await kartu_tempat.nth(i).get_attribute("href")
                if link and link not in link_unik:
                    link_unik.append(link)

            logger.info(f"[!] Ditemukan {len(link_unik)} tempat unik setelah disaring.")

            logger.info("[*] Memulai proses klik dan ekstraksi data detail...")
            daftar_data = []
            jumlah_dilewati_nomor_rumah = 0
            jumlah_dilewati_tanpa_telepon = 0

            target_ambil = min(len(link_unik), target_maksimal)

            for i in tqdm(range(target_ambil), desc="Ekstraksi detail", unit="tempat"):
                try:
                    url_tempat = link_unik[i]
                    logger.debug(f"[*] Memproses tempat ke-{i+1} dari {target_ambil}...")

                    await page.goto(url_tempat, wait_until="commit", timeout=60000)

                    await asyncio.sleep(3)

                    try:
                        nama = await page.locator("h1.DUwDvf").inner_text()
                    except:
                        nama = "tidak ada nama"
                    try:
                        alamat = await page.locator('button[data-item-id="address"]').inner_text()
                        alamat = alamat.replace("", "").strip()
                    except:
                        alamat = "tidak ada alamat"
                    try:
                        telepon = await page.locator('button[data-item-id^="phone:tel:"]').inner_text()
                    except:
                        telepon = "tidak ada telepon"
                    try:
                        website = await page.locator('a[data-item-id="authority"]').inner_text()
                        website = website.strip()
                        if not website:
                            website = "tidak ada website"
                    except:
                        website = "tidak ada website"
                    try:
                        rating_element = page.locator("div.F7nice span").first
                        rating = await rating_element.inner_text()

                        review_element = page.locator("div.F7nice").first
                        review_raw = await review_element.inner_text()

                        review = review_raw.split("(")[-1].replace(")", "").strip()
                    except Exception:
                        rating = "0.0"
                        review = "0"

                    try:
                        rating_bersih = float(rating.replace(",", "."))
                    except:
                        rating_bersih = 0.0

                    # === FILTER TEMPAT TANPA NOMOR TELEPON SAMA SEKALI ===
                    if skip_tanpa_telepon and telepon == "tidak ada telepon":
                        jumlah_dilewati_tanpa_telepon += 1
                        logger.info(f"[SKIP] {nama} dilewati karena tidak memiliki nomor telepon.")
                        continue

                    # === FILTER NOMOR RUMAH/KANTOR (LANDLINE) ===
                    if skip_landline and telepon != "tidak ada telepon" and not is_nomor_hp(telepon):
                        jumlah_dilewati_nomor_rumah += 1
                        logger.info(f"[SKIP] {nama} dilewati karena nomor terdeteksi nomor rumah/kantor: {telepon}")
                        continue

                    daftar_data.append({
                        "No": len(daftar_data) + 1,
                        "Nama Tempat": nama,
                        "Rating": rating_bersih,
                        "Jumlah Review": review,
                        "Alamat": alamat,
                        "Telepon": telepon,
                        "Website": website
                    })
                    logger.debug(f"[V] Berhasil menyalin {nama}")
                except Exception as e:
                    logger.error(f"[X] Gagal mengambil detail ke-{i+1}: {e}")
                    continue

            if jumlah_dilewati_nomor_rumah > 0:
                logger.info(f"[i] Total {jumlah_dilewati_nomor_rumah} tempat dilewati karena nomor rumah/kantor.")
            if jumlah_dilewati_tanpa_telepon > 0:
                logger.info(f"[i] Total {jumlah_dilewati_tanpa_telepon} tempat dilewati karena tidak ada nomor telepon.")

            if daftar_data:
                df = pd.DataFrame(daftar_data)

                writer = pd.ExcelWriter(nama_file, engine='xlsxwriter')
                df.to_excel(writer, index=False, sheet_name='Data')

                workbook = writer.book
                worksheet = writer.sheets['Data']

                for idx, col in enumerate(df.columns):
                    max_len = df[col].astype(str).str.len().max()
                    worksheet.set_column(idx, idx, max_len + 5)

                writer.close()
                logger.info(f"[V] SUKSES BESAR! file '{nama_file}' berhasil dibuat dengan {len(daftar_data)} data.")
            else:
                logger.warning("[X] Data kosong! gagal menyimpan ke excel.")

        except Exception as e:
            logger.error(f"error: {e}")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(run_masukmaps())
