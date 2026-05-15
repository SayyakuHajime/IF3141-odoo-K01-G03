#!/usr/bin/env python3
"""
Generate QR code images untuk demo warehouse.

Install dulu: pip install qrcode[pil]

Usage:
    python3 scripts/generate_qr_demo.py

Output: folder scripts/qr_images/ berisi PNG untuk tiap tag.
"""
import os
import sys

try:
    import qrcode
except ImportError:
    print('Install dulu: pip install qrcode[pil]')
    sys.exit(1)

OUT_DIR = os.path.join(os.path.dirname(__file__), 'qr_images')
os.makedirs(OUT_DIR, exist_ok=True)

# Tag yang di-assign ke kargo warehouse-relevant (sesuai seed_test_data_2.py)
TAGS = [
    ('QR-BATCH-2026-001-0001', 'K4 — Dewi Permata (di gudang, siap Pencucian)'),
    ('QR-BATCH-2026-001-0002', 'K6 — Fajar Nugroho (baru dijemput, siap Arrival)'),
    ('QR-BATCH-2026-001-0003', 'K5 — Rudi Hermawan (dalam perjalanan)'),
    ('QR-BATCH-2026-001-0004', 'idle — belum ada kargo'),
    ('QR-BATCH-2026-001-0005', 'idle — belum ada kargo'),
]

for tag_id, label in TAGS:
    fname = f'{tag_id}.png'
    fpath = os.path.join(OUT_DIR, fname)
    img = qrcode.make(tag_id)
    with open(fpath, 'wb') as f:
        img.save(f)
    print(f'✅ {fname}  ({label})')

print(f'\nFile tersimpan di: {OUT_DIR}')
print('\nCara demo:')
print('  1. Buka file QR-BATCH-2026-001-0001.png di layar/HP lain')
print('  2. Di warehouse app, masuk ke tab Scan QR')
print('  3. Arahkan kamera ke gambar QR tersebut')
print('  4. Sistem otomatis mendeteksi → redirect ke update status K4')
