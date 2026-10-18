import os
import sys
import time
import httpx
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("HF_TOKEN")
if not token:
    print("ERROR: HF_TOKEN not found in environment!")
    sys.exit(1)

target_dir = r"C:\Users\HP\.cache\huggingface\hub\models--ai4bharat--indictrans2-indic-indic-dist-320M\snapshots\ffb7582b6d43791f1fb26b2153fc065f2e9ea575"
os.makedirs(target_dir, exist_ok=True)
target_file = os.path.join(target_dir, "model.safetensors")
part_file = target_file + ".part"

url = "https://huggingface.co/ai4bharat/indictrans2-indic-indic-dist-320M/resolve/main/model.safetensors"
TOTAL_EXPECTED_BYTES = 1283526976  # ~1224.07 MB

if os.path.exists(target_file):
    sz = os.path.getsize(target_file)
    print(f"Target file already exists: {sz / (1024*1024):.2f} MB")
    if sz >= 1200 * 1024 * 1024:
        print("Model file is already fully downloaded!")
        sys.exit(0)

print(f"Starting resilient download of IndicTrans2 (target: {TOTAL_EXPECTED_BYTES / (1024*1024):.2f} MB)...")
sys.stdout.flush()

max_retries = 50
retry_count = 0

client = httpx.Client(follow_redirects=True, timeout=httpx.Timeout(connect=60.0, read=60.0, write=60.0, pool=60.0))

while retry_count < max_retries:
    existing_bytes = 0
    if os.path.exists(part_file):
        existing_bytes = os.path.getsize(part_file)
        if existing_bytes >= TOTAL_EXPECTED_BYTES:
            print("Part file is complete, finalizing...")
            if os.path.exists(target_file):
                os.remove(target_file)
            os.rename(part_file, target_file)
            print(f"SUCCESS: Model downloaded completely to {target_file}!")
            sys.exit(0)

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "BhashaBridgeResilientDownloader/1.0"
    }
    if existing_bytes > 0:
        headers["Range"] = f"bytes={existing_bytes}-"
        print(f"Resuming download from byte {existing_bytes} ({existing_bytes / (1024*1024):.2f} MB)...")
    else:
        print("Connecting to Hugging Face...")
    sys.stdout.flush()

    try:
        with client.stream("GET", url, headers=headers) as r:
            if r.status_code not in (200, 206):
                print(f"HTTP error {r.status_code}")
                retry_count += 1
                time.sleep(3)
                continue

            mode = "ab" if existing_bytes > 0 and r.status_code == 206 else "wb"
            if mode == "wb":
                existing_bytes = 0

            downloaded = existing_bytes
            last_log_time = time.time()
            last_bytes = downloaded

            with open(part_file, mode) as f:
                for chunk in r.iter_bytes(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_log_time >= 5.0:
                            speed = (downloaded - last_bytes) / (now - last_log_time) / (1024 * 1024)
                            pct = (downloaded / TOTAL_EXPECTED_BYTES) * 100
                            print(f"Progress: {downloaded / (1024*1024):.1f} / {TOTAL_EXPECTED_BYTES / (1024*1024):.1f} MB ({pct:.1f}%) | Speed: {speed:.2f} MB/s")
                            sys.stdout.flush()
                            last_log_time = now
                            last_bytes = downloaded

            if downloaded >= TOTAL_EXPECTED_BYTES - (1024 * 1024):
                if os.path.exists(target_file):
                    os.remove(target_file)
                os.rename(part_file, target_file)
                print(f"SUCCESS: Model downloaded completely to {target_file}!")
                sys.exit(0)

    except Exception as e:
        retry_count += 1
        print(f"Network interruption ({e}). Retrying ({retry_count}/{max_retries}) in 3s...")
        sys.stdout.flush()
        time.sleep(3)

print("Exceeded maximum retries.")
sys.exit(1)
