#!/usr/bin/env python3
"""
Seed demo data untuk AGF Cargo — PT Berkah Melano Indonesia

Membuat:
  - 1 batch aktif dengan 7 kargo (berbagai status)
  - 2 batch historis dengan 3 kargo selesai masing-masing
  - QR tags: aktif, idle, rusak
  - Test users: manajer_test + gudang_test (password: Test@1234)

Usage:
    python3 scripts/seed_demo.py           # append data
    python3 scripts/seed_demo.py --fresh   # hapus semua data lama dulu
"""

import xmlrpc.client
import sys
from datetime import date, timedelta

# ── Config ───────────────────────────────────────────────────────────
URL      = 'http://localhost:8069'
DB       = 'postgres'
USERNAME = 'admin'
PASSWORD = 'admin'
# ─────────────────────────────────────────────────────────────────────


def connect():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        print('❌ Login gagal. Pastikan Odoo berjalan dan kredensial benar.')
        sys.exit(1)
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    print(f'✅ Login berhasil (uid={uid})')
    return uid, models


def call(models, uid, model, method, args, kwargs=None):
    return models.execute_kw(DB, uid, PASSWORD, model, method, args, kwargs or {})


def create(models, uid, model, vals):
    return call(models, uid, model, 'create', [vals])


def search_read(models, uid, model, domain, fields):
    return call(models, uid, model, 'search_read', [domain], {'fields': fields})


# ─────────────────────────────────────────────────────────────────────
# CLEAR
# ─────────────────────────────────────────────────────────────────────

def clear_existing(models, uid):
    print('\n🗑  Membersihkan data lama...')
    for model in ['agf.tahapan', 'agf.tanaman.item', 'agf.qr.tag', 'agf.kargo', 'agf.batch']:
        ids = call(models, uid, model, 'search', [[]])
        if ids:
            call(models, uid, model, 'unlink', [ids])
            print(f'   {model}: {len(ids)} record dihapus')
    for login in ['manajer_test', 'gudang_test']:
        ids = call(models, uid, 'res.users', 'search', [[('login', '=', login)]])
        if ids:
            call(models, uid, 'res.users', 'unlink', [ids])
            print(f'   res.users ({login}): dihapus')


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────

def get_agf_group_ids(models, uid):
    result = {}
    for xml_name, key in [
        ('group_agf_admin',   'admin'),
        ('group_agf_manajer', 'manajer'),
        ('group_agf_gudang',  'gudang'),
    ]:
        rows = call(models, uid, 'ir.model.data', 'search_read',
                    [[('module', '=', 'agf_cargo'), ('name', '=', xml_name)]],
                    {'fields': ['res_id']})
        if rows:
            result[key] = rows[0]['res_id']
    return result


def tambah_tahapan(models, uid, kargo_id, tahapan_list):
    """
    tahapan_list: list of (tahap_code, catatan, lokasi)
    """
    for tahap_code, catatan, lokasi in tahapan_list:
        create(models, uid, 'agf.tahapan', {
            'kargo_id': kargo_id,
            'tahap':    tahap_code,
            'catatan':  catatan,
            'lokasi':   lokasi,
        })


def tambah_tanaman(models, uid, kargo_id, tanaman_list):
    """
    tanaman_list: list of dict {nama_tanaman, jumlah, ukuran, kondisi}
    """
    for t in tanaman_list:
        create(models, uid, 'agf.tanaman.item', {
            'kargo_id':    kargo_id,
            'nama_tanaman': t['nama_tanaman'],
            'jumlah':      t['jumlah'],
            'ukuran':      t.get('ukuran', 'sedang'),
            'kondisi':     t.get('kondisi', 'belum_dicek'),
        })


def buat_kargo(models, uid, batch_id, data):
    """Buat kargo + tanaman + tahapan sekaligus."""
    tanaman_list = data.pop('_tanaman', [])
    tahapan_list = data.pop('_tahapan', [])
    data['batch_id'] = batch_id

    kargo_id = create(models, uid, 'agf.kargo', data)
    kinfo = search_read(models, uid, 'agf.kargo',
                        [('id', '=', kargo_id)],
                        ['nomor_penitip', 'nomor_penerima'])
    nomor_p  = kinfo[0]['nomor_penitip']
    nomor_r  = kinfo[0]['nomor_penerima']

    tambah_tanaman(models, uid, kargo_id, tanaman_list)
    tambah_tahapan(models, uid, kargo_id, tahapan_list)

    # Kembalikan data supaya fixture bisa dipakai ulang
    data['_tanaman'] = tanaman_list
    data['_tahapan'] = tahapan_list

    return kargo_id, nomor_p, nomor_r


# ─────────────────────────────────────────────────────────────────────
# FIXTURES — Batch Aktif
# ─────────────────────────────────────────────────────────────────────

AKTIF_KARGO = [
    # K1 — baru daftar, belum bayar (untuk demo customer portal)
    {
        'nama_penitip':    'Budi Santoso',
        'hp_penitip':      '+62 812-3456-7890',
        'email_penitip':   'budi@example.com',
        'alamat_penitip':  'Jl. Merdeka No. 10, Bandung 40111',
        'nama_penerima':   'John Smith',
        'hp_penerima':     '+1 555-234-5678',
        'email_penerima':  'john.smith@email.com',
        'alamat_penerima': '123 Main St, Los Angeles, CA 90001',
        'kota_tujuan':     'Los Angeles',
        'negara_tujuan':   'United States',
        'layanan_lokal':   'reguler',
        'additional_packaging': 'dakron',
        'winter_packaging': 'none',
        '_tanaman': [
            {'nama_tanaman': 'Monstera deliciosa',     'jumlah': 2, 'ukuran': 'sedang', 'kondisi': 'belum_dicek'},
            {'nama_tanaman': 'Philodendron gloriosum', 'jumlah': 3, 'ukuran': 'kecil',  'kondisi': 'belum_dicek'},
        ],
        '_tahapan': [
            ('01_registrasi', 'Pendaftaran kargo berhasil masuk ke sistem.', 'Bandung'),
        ],
    },
    # K2 — menunggu verifikasi pembayaran
    {
        'nama_penitip':    'Siti Rahayu',
        'hp_penitip':      '+62 821-9876-5432',
        'email_penitip':   'siti@example.com',
        'alamat_penitip':  'Jl. Sudirman No. 5, Jakarta 10220',
        'nama_penerima':   'Maria Garcia',
        'hp_penerima':     '+1 555-876-5432',
        'email_penerima':  'maria.garcia@email.com',
        'alamat_penerima': '456 Oak Ave, Miami, FL 33101',
        'kota_tujuan':     'Miami',
        'negara_tujuan':   'United States',
        'layanan_lokal':   'next_day',
        'additional_packaging': 'tissue',
        'winter_packaging': 'heat_pack',
        '_tanaman': [
            {'nama_tanaman': 'Anthurium crystallinum', 'jumlah': 2,  'ukuran': 'besar',  'kondisi': 'belum_dicek'},
            {'nama_tanaman': 'Hoya kerrii',            'jumlah': 10, 'ukuran': 'kecil',  'kondisi': 'belum_dicek'},
        ],
        '_tahapan': [
            ('01_registrasi',     'Pendaftaran kargo berhasil.', 'Jakarta'),
            ('02_menunggu_bayar', 'Invoice telah dikirim ke customer.', 'Jakarta'),
        ],
    },
    # K3 — pembayaran terverifikasi, menunggu penjemputan
    {
        'nama_penitip':    'Andi Wijaya',
        'hp_penitip':      '+62 813-1111-2222',
        'email_penitip':   'andi@example.com',
        'alamat_penitip':  'Jl. Diponegoro No. 20, Bandung 40171',
        'nama_penerima':   'David Lee',
        'hp_penerima':     '+1 555-111-2222',
        'email_penerima':  'david.lee@email.com',
        'alamat_penerima': '789 Pine Rd, Seattle, WA 98101',
        'kota_tujuan':     'Seattle',
        'negara_tujuan':   'United States',
        'layanan_lokal':   'reguler',
        'additional_packaging': 'none',
        'winter_packaging': 'heat_insulation',
        'konfirmasi_penjemputan': True,
        '_tanaman': [
            {'nama_tanaman': 'Alocasia zebrina',       'jumlah': 2, 'ukuran': 'sedang', 'kondisi': 'sehat'},
            {'nama_tanaman': 'Calathea orbifolia',     'jumlah': 3, 'ukuran': 'kecil',  'kondisi': 'sehat'},
        ],
        '_tahapan': [
            ('01_registrasi',     'Pendaftaran kargo berhasil.', 'Bandung'),
            ('02_menunggu_bayar', 'Invoice dikirim.', 'Bandung'),
            ('03_bayar_verified', 'Pembayaran terverifikasi oleh admin.', 'Lembang, Bandung'),
            ('04_penjemputan',    'Tanaman dijemput oleh kurir AGF Cargo.', 'Jl. Diponegoro No. 20, Bandung'),
        ],
    },
    # K4 — sedang di gudang (cocok untuk demo warehouse)
    {
        'nama_penitip':    'Dewi Permata',
        'hp_penitip':      '+62 878-5555-6666',
        'email_penitip':   'dewi@example.com',
        'alamat_penitip':  'Jl. Gatot Subroto No. 99, Bandung 40262',
        'nama_penerima':   'Sarah Davis',
        'hp_penerima':     '+1 555-444-3333',
        'email_penerima':  'sarah.davis@email.com',
        'alamat_penerima': '321 Elm St, Houston, TX 77001',
        'kota_tujuan':     'Houston',
        'negara_tujuan':   'United States',
        'layanan_lokal':   'reguler',
        'additional_packaging': 'tissue',
        'winter_packaging': 'none',
        'konfirmasi_penjemputan': True,
        '_tanaman': [
            {'nama_tanaman': 'Monstera Thai Constellation', 'jumlah': 1, 'ukuran': 'sedang', 'kondisi': 'sehat'},
            {'nama_tanaman': 'Ficus lyrata',                'jumlah': 1, 'ukuran': 'besar',  'kondisi': 'sehat'},
            {'nama_tanaman': 'Pothos golden',               'jumlah': 4, 'ukuran': 'kecil',  'kondisi': 'sehat'},
        ],
        '_tahapan': [
            ('01_registrasi',     'Pendaftaran kargo berhasil.', 'Bandung'),
            ('02_menunggu_bayar', 'Invoice dikirim.', 'Bandung'),
            ('03_bayar_verified', 'Pembayaran terverifikasi.', 'Lembang, Bandung'),
            ('04_penjemputan',    'Tanaman dijemput.', 'Jl. Gatot Subroto No. 99, Bandung'),
            ('05_gudang_asal',    'Tanaman tiba di gudang dalam kondisi baik. Proses pengecekan dimulai.', 'Gudang AGF Cargo, Lembang'),
        ],
    },
    # K5 — dalam perjalanan (cocok untuk demo tracking penerima RCV-)
    {
        'nama_penitip':    'Rudi Hermawan',
        'hp_penitip':      '+62 856-7777-8888',
        'email_penitip':   'rudi@example.com',
        'alamat_penitip':  'Jl. Kenanga No. 7, Cimahi 40522',
        'nama_penerima':   'Michael Brown',
        'hp_penerima':     '+1 555-999-0000',
        'email_penerima':  'michael.brown@email.com',
        'alamat_penerima': '654 Maple Ave, Chicago, IL 60601',
        'kota_tujuan':     'Chicago',
        'negara_tujuan':   'United States',
        'layanan_lokal':   'next_day',
        'additional_packaging': 'dakron',
        'winter_packaging': 'heat_insulation',
        'konfirmasi_penjemputan': True,
        '_tanaman': [
            {'nama_tanaman': 'Begonia maculata',        'jumlah': 3, 'ukuran': 'kecil',  'kondisi': 'sehat'},
            {'nama_tanaman': 'Syngonium albo',          'jumlah': 2, 'ukuran': 'sedang', 'kondisi': 'sehat'},
        ],
        '_tahapan': [
            ('01_registrasi',     'Pendaftaran kargo berhasil.', 'Cimahi'),
            ('02_menunggu_bayar', 'Invoice dikirim.', 'Cimahi'),
            ('03_bayar_verified', 'Pembayaran terverifikasi.', 'Lembang, Bandung'),
            ('04_penjemputan',    'Tanaman dijemput.', 'Jl. Kenanga No. 7, Cimahi'),
            ('05_gudang_asal',    'Tanaman tiba dan dicek kondisinya.', 'Gudang AGF Cargo, Lembang'),
            ('06_terminal_asal',  'Dokumen ekspor lengkap. Siap diberangkatkan.', 'Terminal Kargo Soekarno-Hatta, Jakarta'),
            ('07_transit',        'Paket sedang dalam perjalanan ke negara tujuan.', 'In-flight — Jakarta → Chicago'),
        ],
    },
    # K6 — siap dicek gudang (untuk demo warehouse update status)
    {
        'nama_penitip':    'Fajar Nugroho',
        'hp_penitip':      '+62 877-2222-3333',
        'email_penitip':   'fajar@example.com',
        'alamat_penitip':  'Jl. Bougenville No. 8, Bandung 40152',
        'nama_penerima':   'Robert Taylor',
        'hp_penerima':     '+1 555-222-3333',
        'email_penerima':  'robert.taylor@email.com',
        'alamat_penerima': '147 Cedar Ln, Miami, FL 33101',
        'kota_tujuan':     'Miami',
        'negara_tujuan':   'United States',
        'layanan_lokal':   'reguler',
        'additional_packaging': 'none',
        'winter_packaging': 'none',
        'konfirmasi_penjemputan': True,
        '_tanaman': [
            {'nama_tanaman': 'Philodendron Pink Princess', 'jumlah': 1, 'ukuran': 'sedang', 'kondisi': 'sehat'},
            {'nama_tanaman': 'Alocasia reginula',          'jumlah': 2, 'ukuran': 'kecil',  'kondisi': 'kurang_sehat'},
        ],
        '_tahapan': [
            ('01_registrasi',     'Pendaftaran kargo berhasil.', 'Bandung'),
            ('02_menunggu_bayar', 'Invoice dikirim.', 'Bandung'),
            ('03_bayar_verified', 'Pembayaran terverifikasi.', 'Lembang, Bandung'),
            ('04_penjemputan',    'Tanaman dijemput.', 'Jl. Bougenville No. 8, Bandung'),
        ],
    },
    # K7 — hold/bermasalah (untuk demo admin dashboard alert)
    {
        'nama_penitip':    'Ahmad Fauzi',
        'hp_penitip':      '+62 813-4444-5555',
        'email_penitip':   'ahmad@example.com',
        'alamat_penitip':  'Jl. Pahlawan No. 15, Surabaya 60241',
        'nama_penerima':   'Lisa Anderson',
        'hp_penerima':     '+1 555-888-7777',
        'email_penerima':  'lisa.anderson@email.com',
        'alamat_penerima': '963 Birch Rd, Phoenix, AZ 85001',
        'kota_tujuan':     'Phoenix',
        'negara_tujuan':   'United States',
        'layanan_lokal':   'reguler',
        'additional_packaging': 'none',
        'winter_packaging': 'none',
        '_tanaman': [
            {'nama_tanaman': 'Anthurium warocqueanum', 'jumlah': 1, 'ukuran': 'besar',  'kondisi': 'bermasalah'},
        ],
        '_tahapan': [
            ('01_registrasi', 'Pendaftaran kargo berhasil. Menunggu konfirmasi dokumen.', 'Surabaya'),
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────
# FIXTURES — Batch Historis
# ─────────────────────────────────────────────────────────────────────

def get_hist_kargo(offset_days):
    """Generate 3 kargo selesai untuk batch historis."""
    today = date.today()
    return [
        {
            'nama_penitip':    'Hana Putri',
            'hp_penitip':      '+62 812-9999-0001',
            'email_penitip':   'hana@example.com',
            'alamat_penitip':  'Jl. Flamboyan No. 2, Bandung',
            'nama_penerima':   'Emily Johnson',
            'hp_penerima':     '+1 555-001-0001',
            'email_penerima':  'emily@example.com',
            'alamat_penerima': '101 Willow St, New York, NY 10001',
            'kota_tujuan':     'New York',
            'negara_tujuan':   'United States',
            'layanan_lokal':   'reguler',
            'additional_packaging': 'dakron',
            'winter_packaging': 'none',
            'konfirmasi_penjemputan': True,
            '_tanaman': [
                {'nama_tanaman': 'Monstera adansonii', 'jumlah': 3, 'ukuran': 'kecil', 'kondisi': 'sehat'},
            ],
            '_tahapan': [
                ('01_registrasi',      'Pendaftaran kargo berhasil.', 'Bandung'),
                ('02_menunggu_bayar',  'Invoice dikirim.', 'Bandung'),
                ('03_bayar_verified',  'Pembayaran terverifikasi.', 'Lembang, Bandung'),
                ('04_penjemputan',     'Tanaman dijemput.', 'Bandung'),
                ('05_gudang_asal',     'Tanaman tiba di gudang.', 'Gudang AGF Cargo, Lembang'),
                ('06_terminal_asal',   'Siap diberangkatkan.', 'Terminal Soekarno-Hatta'),
                ('07_transit',         'Dalam perjalanan.', 'In-flight'),
                ('08_terminal_tujuan', 'Tiba di terminal tujuan.', 'JFK International Cargo'),
                ('09_bea_cukai',       'Lolos pemeriksaan bea cukai.', 'US Customs — JFK'),
                ('10_pengiriman_lokal','Diserahkan ke UPS lokal.', 'UPS New York Hub'),
                ('11_tiba',            'Paket tiba di alamat penerima.', '101 Willow St, New York'),
                ('12_selesai',         'Penerima mengonfirmasi penerimaan tanaman.', 'New York'),
            ],
        },
        {
            'nama_penitip':    'Bagas Prayoga',
            'hp_penitip':      '+62 812-9999-0002',
            'email_penitip':   'bagas@example.com',
            'alamat_penitip':  'Jl. Cempaka No. 11, Bandung',
            'nama_penerima':   'James Wilson',
            'hp_penerima':     '+1 555-002-0002',
            'email_penerima':  'james@example.com',
            'alamat_penerima': '202 Birch Ave, Dallas, TX 75201',
            'kota_tujuan':     'Dallas',
            'negara_tujuan':   'United States',
            'layanan_lokal':   'next_day',
            'additional_packaging': 'tissue',
            'winter_packaging': 'heat_pack',
            'konfirmasi_penjemputan': True,
            '_tanaman': [
                {'nama_tanaman': 'Hoya kerrii',        'jumlah': 5, 'ukuran': 'kecil',  'kondisi': 'sehat'},
                {'nama_tanaman': 'Calathea makoyana',  'jumlah': 2, 'ukuran': 'sedang', 'kondisi': 'sehat'},
            ],
            '_tahapan': [
                ('01_registrasi',      'Pendaftaran kargo berhasil.', 'Bandung'),
                ('02_menunggu_bayar',  'Invoice dikirim.', 'Bandung'),
                ('03_bayar_verified',  'Pembayaran terverifikasi.', 'Lembang, Bandung'),
                ('04_penjemputan',     'Tanaman dijemput.', 'Bandung'),
                ('05_gudang_asal',     'Tanaman tiba di gudang.', 'Gudang AGF Cargo, Lembang'),
                ('06_terminal_asal',   'Siap diberangkatkan.', 'Terminal Soekarno-Hatta'),
                ('07_transit',         'Dalam perjalanan.', 'In-flight'),
                ('08_terminal_tujuan', 'Tiba di terminal tujuan.', 'DFW International Cargo'),
                ('09_bea_cukai',       'Lolos bea cukai.', 'US Customs — DFW'),
                ('10_pengiriman_lokal','Diserahkan ke UPS lokal.', 'UPS Dallas Hub'),
                ('11_tiba',            'Paket tiba di alamat penerima.', '202 Birch Ave, Dallas'),
                ('12_selesai',         'Penerima mengonfirmasi penerimaan.', 'Dallas'),
            ],
        },
        {
            'nama_penitip':    'Citra Dewi',
            'hp_penitip':      '+62 812-9999-0003',
            'email_penitip':   'citra@example.com',
            'alamat_penitip':  'Jl. Dahlia No. 33, Cimahi',
            'nama_penerima':   'Olivia Martinez',
            'hp_penerima':     '+1 555-003-0003',
            'email_penerima':  'olivia@example.com',
            'alamat_penerima': '303 Oak Blvd, Denver, CO 80201',
            'kota_tujuan':     'Denver',
            'negara_tujuan':   'United States',
            'layanan_lokal':   'reguler',
            'additional_packaging': 'none',
            'winter_packaging': 'heat_insulation',
            'konfirmasi_penjemputan': True,
            '_tanaman': [
                {'nama_tanaman': 'Philodendron gloriosum', 'jumlah': 1, 'ukuran': 'besar', 'kondisi': 'sehat'},
            ],
            '_tahapan': [
                ('01_registrasi',      'Pendaftaran kargo berhasil.', 'Cimahi'),
                ('02_menunggu_bayar',  'Invoice dikirim.', 'Cimahi'),
                ('03_bayar_verified',  'Pembayaran terverifikasi.', 'Lembang, Bandung'),
                ('04_penjemputan',     'Tanaman dijemput.', 'Cimahi'),
                ('05_gudang_asal',     'Tanaman tiba di gudang.', 'Gudang AGF Cargo, Lembang'),
                ('06_terminal_asal',   'Siap diberangkatkan.', 'Terminal Soekarno-Hatta'),
                ('07_transit',         'Dalam perjalanan.', 'In-flight'),
                ('08_terminal_tujuan', 'Tiba di terminal tujuan.', 'DEN International Cargo'),
                ('09_bea_cukai',       'Lolos bea cukai.', 'US Customs — DEN'),
                ('10_pengiriman_lokal','Diserahkan ke UPS lokal.', 'UPS Denver Hub'),
                ('11_tiba',            'Paket tiba di alamat penerima.', '303 Oak Blvd, Denver'),
                ('12_selesai',         'Penerima mengonfirmasi penerimaan.', 'Denver'),
            ],
        },
    ]


# ─────────────────────────────────────────────────────────────────────
# SEED FUNCTIONS
# ─────────────────────────────────────────────────────────────────────

def ensure_admin_group(models, uid):
    rows = call(models, uid, 'ir.model.data', 'search_read',
                [[('module', '=', 'agf_cargo'),
                  ('name',   '=', 'group_agf_admin')]],
                {'fields': ['res_id']})
    if not rows:
        print('⚠  group_agf_admin tidak ditemukan — pastikan modul terinstall.')
        return
    group_id = rows[0]['res_id']
    call(models, uid, 'res.users', 'write',
        [[uid], {'groups_id': [(4, group_id)]}])
    print(f'✅ Admin ditambahkan ke group Admin AGF (id={group_id})')

def seed_active_batch(models, uid):
    today = date.today()
    departure = (today + timedelta(days=14)).isoformat()

    print('\n📦 Membuat batch aktif...')
    batch_id = create(models, uid, 'agf.batch', {
        'name':                  'BATCH-2026-001',
        'batch_id':              'BATCH-2026-001',
        'status':                'aktif',
        'tanggal_mulai':         today.isoformat(),
        'tanggal_keberangkatan': departure,
        'negara_tujuan':         'United States',
        'catatan':               'Batch aktif untuk demo presentasi.',
    })
    print(f'   BATCH-2026-001 (berangkat {departure})')

    print('\n🌿 Membuat kargo batch aktif (7 pesanan)...')
    kargo_ids = []
    for fixture in AKTIF_KARGO:
        kargo_id, nomor_p, nomor_r = buat_kargo(models, uid, batch_id, fixture)
        kargo_ids.append(kargo_id)
        print(f'   {nomor_p} / {nomor_r}')

    return batch_id, kargo_ids


def seed_historical_batches(models, uid):
    today = date.today()
    print('\n📋 Membuat batch historis...')
    hist_specs = [
        {
            'name':           'BATCH-2026-000',
            'batch_id':       'BATCH-2026-000',
            'status':         'terkirim',
            'offset_days':    60,
            'catatan':        'Batch terkirim — 2 bulan lalu.',
        },
        {
            'name':           'BATCH-2025-012',
            'batch_id':       'BATCH-2025-012',
            'status':         'selesai',
            'offset_days':    120,
            'catatan':        'Batch selesai — 4 bulan lalu.',
        },
    ]

    hist_batch_ids = []
    for spec in hist_specs:
        departure     = (today - timedelta(days=spec['offset_days'])).isoformat()
        tanggal_mulai = (today - timedelta(days=spec['offset_days'] + 14)).isoformat()
        tanggal_selesai = (today - timedelta(days=spec['offset_days'] - 7)).isoformat()

        batch_id = create(models, uid, 'agf.batch', {
            'name':                  spec['name'],
            'batch_id':              spec['batch_id'],
            'status':                spec['status'],
            'tanggal_mulai':         tanggal_mulai,
            'tanggal_keberangkatan': departure,
            'tanggal_selesai':       tanggal_selesai,
            'negara_tujuan':         'United States',
            'catatan':               spec['catatan'],
        })
        print(f'   {spec["name"]}  (status={spec["status"]}, berangkat={departure})')

        for fixture in get_hist_kargo(spec['offset_days']):
            kargo_id, nomor_p, nomor_r = buat_kargo(models, uid, batch_id, fixture)
            print(f'      {nomor_p} / {nomor_r}  (selesai)')

        hist_batch_ids.append(batch_id)

    return hist_batch_ids


def seed_qr_tags(models, uid, active_batch_id, active_kargo_ids, hist_batch_ids):
    print('\n🏷  Membuat QR Tags...')
    fixtures = [
        {'status': 'aktif',  'kargo_id': active_kargo_ids[0], 'batch_id': active_batch_id},
        {'status': 'aktif',  'kargo_id': active_kargo_ids[1], 'batch_id': active_batch_id},
        {'status': 'aktif',  'kargo_id': active_kargo_ids[2], 'batch_id': active_batch_id},
        {'status': 'idle',   'kargo_id': False,               'batch_id': active_batch_id},
        {'status': 'idle',   'kargo_id': False,               'batch_id': active_batch_id},
        {'status': 'idle',   'kargo_id': False,               'batch_id': active_batch_id},
        {'status': 'rusak',  'kargo_id': False,               'batch_id': active_batch_id},
        {'status': 'rusak',  'kargo_id': False,               'batch_id': hist_batch_ids[0] if hist_batch_ids else active_batch_id},
    ]
    for i, qr in enumerate(fixtures, 1):
        tag_id = f'QR-BATCH-2026-001-{i:04d}'
        vals = {
            'tag_id':   tag_id,
            'status':   qr['status'],
            'batch_id': qr['batch_id'],
        }
        if qr['kargo_id']:
            vals['kargo_id'] = qr['kargo_id']
        create(models, uid, 'agf.qr.tag', vals)
        print(f'   {tag_id}  ({qr["status"]})')


def seed_test_users(models, uid, group_ids):
    print('\n👥 Membuat test users...')
    specs = [
        {'name': 'Operator Manajer', 'login': 'manajer_test', 'password': 'Test@1234', 'group': 'manajer'},
        {'name': 'Petugas Gudang',   'login': 'gudang_test',  'password': 'Test@1234', 'group': 'gudang'},
    ]
    for spec in specs:
        existing = call(models, uid, 'res.users', 'search', [[('login', '=', spec['login'])]])
        if existing:
            user_id = existing[0]
            print(f"   '{spec['login']}' sudah ada (id={user_id}), update role...")
        else:
            user_id = create(models, uid, 'res.users', {
                'name':     spec['name'],
                'login':    spec['login'],
                'password': spec['password'],
            })
            print(f"   '{spec['name']}' dibuat (id={user_id})")

        target_gid = group_ids.get(spec['group'])
        if target_gid:
            all_agf_gids = [gid for gid in group_ids.values() if gid]
            ops = [(3, gid) for gid in all_agf_gids] + [(4, target_gid)]
            call(models, uid, 'res.users', 'write',
                 [[user_id], {'groups_id': ops}])
            print(f'   → role: {spec["group"]}')


def print_summary(active_batch_id, models, uid):
    today      = date.today()
    departure  = (today + timedelta(days=14)).isoformat()
    binfo = search_read(models, uid, 'agf.batch',
                        [('id', '=', active_batch_id)],
                        ['name', 'total_pesanan', 'total_tanaman'])
    b = binfo[0]

    total_kargo = call(models, uid, 'agf.kargo', 'search_count', [[]])
    total_batch = call(models, uid, 'agf.batch', 'search_count', [[]])
    total_qr    = call(models, uid, 'agf.qr.tag', 'search_count', [[]])

    print(f"""
✅ Seeding selesai!

Batch Aktif   : {b['name']}  (berangkat {departure})
  Pesanan     : {b['total_pesanan']} kargo
  Tanaman     : {b['total_tanaman']} pcs

Total         : {total_kargo} kargo, {total_batch} batch, {total_qr} QR tag
Test Users    : manajer_test / gudang_test  (pw: Test@1234)

── Skenario Demo ─────────────────────────────────────────
Customer Portal  : http://localhost:8069/agf/customer
  AGF-xxxx  → view penitip (upload bukti, konfirmasi jemput)
  RCV-xxxx  → view penerima (tracking simpel)

Warehouse App    : http://localhost:8069/agf/warehouse
  Login          : gudang_test / Test@1234
  Kargo K4 & K6  → siap di-update status via scan QR

Admin Dashboard  : http://localhost:8069/agf/admin
  Login          : admin / admin  atau  manajer_test / Test@1234
  Riwayat Batch  → 2 batch historis tersedia
──────────────────────────────────────────────────────────
""")


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

def seed(models, uid):
    ensure_admin_group(models, uid)
    group_ids = get_agf_group_ids(models, uid)

    active_batch_id, active_kargo_ids = seed_active_batch(models, uid)
    hist_batch_ids = seed_historical_batches(models, uid)
    seed_qr_tags(models, uid, active_batch_id, active_kargo_ids, hist_batch_ids)
    seed_test_users(models, uid, group_ids)
    print_summary(active_batch_id, models, uid)


if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    uid, models = connect()

    if '--fresh' in sys.argv:
        clear_existing(models, uid)

    seed(models, uid)