#!/usr/bin/env python3
"""
Seed test data for agf_cargo module.

Creates:
  - 1 active batch: 5 kargo (arrival / processing / hold / shipped / done)
  - 2 historical batches (terkirim + selesai) with 3 done-kargo each
  - Test users: manajer_test + gudang_test  (password: Test@1234)
  - QR tags: 2 aktif, 2 idle, 3 rusak
  - Prints SQL to spread chart data & trigger hold-alert for full feature coverage

Usage:
    python3 scripts/seed_test_data.py          # append data
    python3 scripts/seed_test_data.py --fresh  # clear all first
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

def clear_existing(models, uid):
    """Hapus data test sebelumnya supaya bisa re-run."""
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


def ensure_admin_group(models, uid):
    groups = call(models, uid, 'res.groups', 'search_read',
                  [[('name', '=', 'Admin AGF')]], {'fields': ['id', 'full_name']})
    if not groups:
        print("⚠  Group 'Admin AGF' tidak ditemukan — pastikan agf_cargo terinstall.")
        sys.exit(1)
    group_id = groups[0]['id']
    call(models, uid, 'res.users', 'write', [[uid], {'groups_id': [(4, group_id)]}])
    print(f"✅ Admin → group '{groups[0]['full_name']}'")
    return group_id


def get_agf_group_ids(models, uid):
    """Lookup semua 3 AGF group via ir.model.data (lebih reliable daripada search by name)."""
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


def add_tahapan(models, uid, kargo_id, tahapan_data):
    for tahap_code, catatan, lokasi in tahapan_data:
        create(models, uid, 'agf.tahapan', {
            'kargo_id':   kargo_id,
            'tahap':      tahap_code,
            'catatan':    catatan,
            'lokasi':     lokasi,
            'status_baru': 'done' if tahap_code == '12_selesai' else False,
            'cek_daun':   tahap_code in ('03_gudang_asal', '10_pengiriman'),
            'cek_akar':   tahap_code in ('03_gudang_asal',),
            'cek_hama':   tahap_code in ('03_gudang_asal', '04_cek_dokumen'),
        })


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────

ACTIVE_KARGO = [
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
        'negara_tujuan':   'USA',
        'layanan_lokal':   'reguler',
        'additional_packaging': 'dakron',
        'winter_packaging': 'none',
        'status':          'arrival',
        '_tanaman': [
            {'nama_tanaman': 'Monstera deliciosa',     'jumlah': 5, 'ukuran': 'sedang', 'kondisi': 'sehat'},
            {'nama_tanaman': 'Philodendron gloriosum', 'jumlah': 3, 'ukuran': 'kecil',  'kondisi': 'sehat'},
        ],
        '_tahapan': [
            ('01_registrasi',  'Pendaftaran kargo berhasil.',           'Bandung'),
            ('02_penjemputan', 'Tanaman dijemput dari lokasi pengirim.', 'Bandung'),
            ('03_gudang_asal', 'Tanaman diterima di gudang AGF.',        'Parongpong'),
        ],
    },
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
        'negara_tujuan':   'USA',
        'layanan_lokal':   'next_day',
        'additional_packaging': 'tissue',
        'winter_packaging': 'heat_pack',
        'status':          'processing',
        '_tanaman': [
            {'nama_tanaman': 'Anthurium crystallinum', 'jumlah': 2,  'ukuran': 'besar',  'kondisi': 'sehat'},
            {'nama_tanaman': 'Hoya kerrii',            'jumlah': 10, 'ukuran': 'kecil',  'kondisi': 'kurang_sehat'},
            {'nama_tanaman': 'Calathea orbifolia',     'jumlah': 4,  'ukuran': 'sedang', 'kondisi': 'sehat'},
        ],
        '_tahapan': [
            ('01_registrasi',  'Pendaftaran kargo berhasil.', 'Jakarta'),
            ('03_gudang_asal', 'Diterima di gudang.',         'Parongpong'),
            ('04_cek_dokumen', 'Dokumen lengkap dan valid.',  'Parongpong'),
        ],
    },
    {
        'nama_penitip':    'Ahmad Fauzi',
        'hp_penitip':      '+62 813-1111-2222',
        'email_penitip':   'ahmad@example.com',
        'alamat_penitip':  'Jl. Diponegoro No. 20, Surabaya 60241',
        'nama_penerima':   'David Lee',
        'hp_penerima':     '+1 555-111-2222',
        'email_penerima':  'david.lee@email.com',
        'alamat_penerima': '789 Pine Rd, Seattle, WA 98101',
        'kota_tujuan':     'Seattle',
        'negara_tujuan':   'USA',
        'layanan_lokal':   'reguler',
        'additional_packaging': 'none',
        'winter_packaging': 'heat_insulation',
        'status':          'hold',
        '_tanaman': [
            {'nama_tanaman': 'Alocasia zebrina', 'jumlah': 6, 'ukuran': 'sedang', 'kondisi': 'belum_dicek'},
        ],
        '_tahapan': [
            ('01_registrasi', 'Menunggu konfirmasi dokumen ekspor.', 'Surabaya'),
        ],
    },
    {
        'nama_penitip':    'Dewi Permata',
        'hp_penitip':      '+62 878-5555-6666',
        'email_penitip':   'dewi@example.com',
        'alamat_penitip':  'Jl. Gatot Subroto No. 99, Denpasar 80361',
        'nama_penerima':   'Sarah Johnson',
        'hp_penerima':     '+1 555-555-6666',
        'email_penerima':  'sarah.j@email.com',
        'alamat_penerima': '321 Elm St, New York, NY 10001',
        'kota_tujuan':     'New York',
        'negara_tujuan':   'USA',
        'layanan_lokal':   'next_day',
        'additional_packaging': 'dakron',
        'winter_packaging': 'insulation',
        'status':          'shipped',
        '_tanaman': [
            {'nama_tanaman': 'Begonia maculata', 'jumlah': 8,  'ukuran': 'kecil', 'kondisi': 'sehat'},
            {'nama_tanaman': 'Ficus lyrata',     'jumlah': 2,  'ukuran': 'besar', 'kondisi': 'sehat'},
            {'nama_tanaman': 'Pothos golden',    'jumlah': 15, 'ukuran': 'kecil', 'kondisi': 'sehat'},
        ],
        '_tahapan': [
            ('01_registrasi',      'Pendaftaran kargo berhasil.',                  'Denpasar'),
            ('03_gudang_asal',     'Diterima di gudang AGF.',                      'Parongpong'),
            ('04_cek_dokumen',     'Semua dokumen lengkap.',                       'Parongpong'),
            ('05_terminal_asal',   'Tanaman tiba di terminal kargo.',              'Jakarta'),
            ('06_transit',         'Dalam perjalanan ke negara tujuan.',           'In-flight'),
            ('07_terminal_tujuan', 'Tiba di terminal kargo tujuan.',               'New York JFK'),
            ('08_bea_cukai',       'Lolos pemeriksaan bea cukai & USDA.',         'New York JFK'),
            ('10_pengiriman',      'Dalam pengiriman lokal ke alamat penerima.',   'New York'),
        ],
    },
    # Kargo #5 — status done (untuk stat card "Pesanan Selesai" & detail inactive via active batch)
    {
        'nama_penitip':    'Rina Kusuma',
        'hp_penitip':      '+62 856-7777-8888',
        'email_penitip':   'rina@example.com',
        'alamat_penitip':  'Jl. Asia Afrika No. 5, Bandung 40111',
        'nama_penerima':   'Emma Wilson',
        'hp_penerima':     '+44 20-7946-0958',
        'email_penerima':  'emma.wilson@email.com',
        'alamat_penerima': '10 Park Lane, London W1K 1AA',
        'kota_tujuan':     'London',
        'negara_tujuan':   'UK',
        'layanan_lokal':   'reguler',
        'additional_packaging': 'tissue',
        'winter_packaging': 'none',
        'status':          'done',
        '_tanaman': [
            {'nama_tanaman': 'Orchid Dendrobium', 'jumlah': 12, 'ukuran': 'kecil',  'kondisi': 'sehat'},
            {'nama_tanaman': 'Aglaonema red',     'jumlah': 3,  'ukuran': 'sedang', 'kondisi': 'sehat'},
        ],
        '_tahapan': [
            ('01_registrasi',      'Pendaftaran kargo berhasil.',                        'Bandung'),
            ('02_penjemputan',     'Tanaman dijemput.',                                   'Bandung'),
            ('03_gudang_asal',     'Diterima di gudang AGF.',                            'Parongpong'),
            ('04_cek_dokumen',     'Dokumen ekspor UK lengkap.',                         'Parongpong'),
            ('05_terminal_asal',   'Tanaman tiba di terminal Soekarno-Hatta.',           'Tangerang'),
            ('06_transit',         'Penerbangan menuju Heathrow.',                        'In-flight'),
            ('07_terminal_tujuan', 'Tiba di Heathrow, menunggu klaim.',                  'London LHR'),
            ('08_bea_cukai',       'Lolos pemeriksaan DEFRA.',                           'London LHR'),
            ('09_gudang_tujuan',   'Di gudang mitra lokal.',                             'London'),
            ('10_pengiriman',      'Dalam pengiriman ke penerima.',                       'London'),
            ('11_tiba',            'Tiba di alamat penerima.',                            'London'),
            ('12_selesai',         'Pesanan selesai, tanaman diterima dalam kondisi baik.', 'London'),
        ],
    },
]

HIST_BATCHES = [
    {
        'offset_days': 60,
        'status':      'terkirim',
        'catatan':     'Batch reguler Maret — terkirim semua',
        'kargo': [
            {
                'nama_penitip':    'Hendra Wijaya',
                'hp_penitip':      '+62 811-2222-3333',
                'email_penitip':   'hendra@example.com',
                'alamat_penitip':  'Jl. Pemuda No. 30, Semarang 50132',
                'nama_penerima':   'Thomas Müller',
                'hp_penerima':     '+49 30 1234 5678',
                'email_penerima':  'thomas.mueller@email.de',
                'alamat_penerima': 'Unter den Linden 5, 10117 Berlin',
                'kota_tujuan':     'Berlin',
                'negara_tujuan':   'Germany',
                'layanan_lokal':   'reguler',
                'additional_packaging': 'dakron',
                'winter_packaging': 'heat_pack',
                'status':          'done',
                '_tanaman': [
                    {'nama_tanaman': 'Monstera adansonii',        'jumlah': 8, 'ukuran': 'kecil',  'kondisi': 'sehat'},
                    {'nama_tanaman': 'Raphidophora tetrasperma',  'jumlah': 4, 'ukuran': 'sedang', 'kondisi': 'sehat'},
                ],
                '_tahapan': [
                    ('01_registrasi',      'Pendaftaran berhasil.',             'Semarang'),
                    ('03_gudang_asal',     'Diterima di gudang.',               'Parongpong'),
                    ('04_cek_dokumen',     'Dokumen EU lengkap.',               'Parongpong'),
                    ('05_terminal_asal',   'Di terminal kargo.',                'Jakarta'),
                    ('06_transit',         'Penerbangan menuju Frankfurt.',     'In-flight'),
                    ('07_terminal_tujuan', 'Tiba di Frankfurt Airport.',        'Frankfurt FRA'),
                    ('08_bea_cukai',       'Lolos pemeriksaan EU.',             'Frankfurt FRA'),
                    ('10_pengiriman',      'Pengiriman darat ke Berlin.',       'Frankfurt'),
                    ('11_tiba',            'Tiba di alamat.',                   'Berlin'),
                    ('12_selesai',         'Selesai, tanaman aman.',            'Berlin'),
                ],
            },
            {
                'nama_penitip':    'Lestari Andini',
                'hp_penitip':      '+62 822-4444-5555',
                'email_penitip':   'lestari@example.com',
                'alamat_penitip':  'Jl. Cihampelas No. 12, Bandung 40131',
                'nama_penerima':   'Sophie Dupont',
                'hp_penerima':     '+33 1 23 45 67 89',
                'email_penerima':  'sophie.dupont@email.fr',
                'alamat_penerima': '15 Rue de Rivoli, 75001 Paris',
                'kota_tujuan':     'Paris',
                'negara_tujuan':   'France',
                'layanan_lokal':   'next_day',
                'additional_packaging': 'tissue',
                'winter_packaging': 'insulation',
                'status':          'done',
                '_tanaman': [
                    {'nama_tanaman': 'Hoya carnosa',          'jumlah': 6, 'ukuran': 'sedang', 'kondisi': 'sehat'},
                    {'nama_tanaman': 'Peperomia obtusifolia', 'jumlah': 5, 'ukuran': 'kecil',  'kondisi': 'sehat'},
                ],
                '_tahapan': [
                    ('01_registrasi',      'Pendaftaran berhasil.',         'Bandung'),
                    ('03_gudang_asal',     'Diterima di gudang AGF.',       'Parongpong'),
                    ('04_cek_dokumen',     'Dokumen Perancis OK.',          'Parongpong'),
                    ('05_terminal_asal',   'Di terminal Soekarno-Hatta.',  'Tangerang'),
                    ('06_transit',         'Penerbangan via Dubai.',        'In-flight'),
                    ('07_terminal_tujuan', 'Tiba di CDG Paris.',           'Paris CDG'),
                    ('08_bea_cukai',       'Lolos customs Paris.',         'Paris CDG'),
                    ('10_pengiriman',      'Dalam pengiriman.',             'Paris'),
                    ('12_selesai',         'Diterima dalam kondisi sempurna.', 'Paris'),
                ],
            },
            {
                'nama_penitip':    'Yusuf Hakim',
                'hp_penitip':      '+62 813-6666-7777',
                'email_penitip':   'yusuf@example.com',
                'alamat_penitip':  'Jl. Imam Bonjol No. 8, Medan 20152',
                'nama_penerima':   'Kenji Nakamura',
                'hp_penerima':     '+81 3-1234-5678',
                'email_penerima':  'kenji.nakamura@email.jp',
                'alamat_penerima': '3-1-1 Marunouchi, Chiyoda-ku, Tokyo 100-0005',
                'kota_tujuan':     'Tokyo',
                'negara_tujuan':   'Japan',
                'layanan_lokal':   'southwest',
                'additional_packaging': 'dakron',
                'winter_packaging': 'none',
                'status':          'done',
                '_tanaman': [
                    {'nama_tanaman': 'Vanilla planifolia', 'jumlah': 3, 'ukuran': 'sedang', 'kondisi': 'sehat'},
                    {'nama_tanaman': 'Jasminum sambac',    'jumlah': 7, 'ukuran': 'kecil',  'kondisi': 'sehat'},
                ],
                '_tahapan': [
                    ('01_registrasi',      'Pendaftaran berhasil.',                     'Medan'),
                    ('03_gudang_asal',     'Diterima di gudang.',                       'Parongpong'),
                    ('04_cek_dokumen',     'Dokumen Jepang terlengkap.',               'Parongpong'),
                    ('05_terminal_asal',   'Di terminal kargo.',                        'Jakarta'),
                    ('06_transit',         'Penerbangan ke Narita.',                    'In-flight'),
                    ('07_terminal_tujuan', 'Tiba di Narita Airport.',                   'Tokyo NRT'),
                    ('08_bea_cukai',       'Lolos karantina Jepang.',                  'Tokyo NRT'),
                    ('10_pengiriman',      'Pengiriman dalam kota Tokyo.',              'Tokyo'),
                    ('12_selesai',         'Diterima, kondisi prima.',                  'Tokyo'),
                ],
            },
        ],
    },
    {
        'offset_days': 30,
        'status':      'selesai',
        'catatan':     'Batch reguler April — selesai diproses',
        'kargo': [
            {
                'nama_penitip':    'Bambang Priyono',
                'hp_penitip':      '+62 817-8888-9999',
                'email_penitip':   'bambang@example.com',
                'alamat_penitip':  'Jl. Malioboro No. 45, Yogyakarta 55213',
                'nama_penerima':   'Carlos Rodríguez',
                'hp_penerima':     '+34 91 123 4567',
                'email_penerima':  'carlos.rodriguez@email.es',
                'alamat_penerima': 'Gran Vía 28, 28013 Madrid',
                'kota_tujuan':     'Madrid',
                'negara_tujuan':   'Spain',
                'layanan_lokal':   'reguler',
                'additional_packaging': 'none',
                'winter_packaging': 'heat_insulation',
                'status':          'done',
                '_tanaman': [
                    {'nama_tanaman': 'Zamioculcas zamiifolia',  'jumlah': 5,  'ukuran': 'sedang', 'kondisi': 'sehat'},
                    {'nama_tanaman': 'Sansevieria trifasciata', 'jumlah': 10, 'ukuran': 'kecil',  'kondisi': 'sehat'},
                ],
                '_tahapan': [
                    ('01_registrasi',      'Terdaftar sukses.',           'Yogyakarta'),
                    ('03_gudang_asal',     'Diterima di gudang.',         'Parongpong'),
                    ('04_cek_dokumen',     'Dokumen EU OK.',              'Parongpong'),
                    ('05_terminal_asal',   'Di terminal Jakarta.',        'Jakarta'),
                    ('06_transit',         'Penerbangan via Doha.',       'In-flight'),
                    ('07_terminal_tujuan', 'Tiba di Madrid Barajas.',     'Madrid MAD'),
                    ('08_bea_cukai',       'Lolos customs Spanyol.',      'Madrid MAD'),
                    ('10_pengiriman',      'Pengiriman dalam kota.',      'Madrid'),
                    ('12_selesai',         'Diterima baik.',              'Madrid'),
                ],
            },
            {
                'nama_penitip':    'Indah Sari',
                'hp_penitip':      '+62 815-1010-2020',
                'email_penitip':   'indah@example.com',
                'alamat_penitip':  'Jl. Raya Ubud No. 22, Gianyar 80571',
                'nama_penerima':   'Anna Kowalski',
                'hp_penerima':     '+48 22 123 4567',
                'email_penerima':  'anna.kowalski@email.pl',
                'alamat_penerima': 'ul. Nowy Swiat 15, 00-029 Warszawa',
                'kota_tujuan':     'Warsaw',
                'negara_tujuan':   'Poland',
                'layanan_lokal':   'next_day',
                'additional_packaging': 'dakron',
                'winter_packaging': 'heat_pack',
                'status':          'done',
                '_tanaman': [
                    {'nama_tanaman': 'Alocasia frydek',    'jumlah': 2, 'ukuran': 'besar', 'kondisi': 'kurang_sehat',
                     'catatan_kondisi': 'Daun sedikit layu saat packing, dipantau selama perjalanan'},
                    {'nama_tanaman': 'Maranta leuconeura', 'jumlah': 4, 'ukuran': 'kecil', 'kondisi': 'sehat'},
                ],
                '_tahapan': [
                    ('01_registrasi',      'Terdaftar.',                                 'Gianyar'),
                    ('03_gudang_asal',     'Tiba di gudang, kondisi alocasia dicatat.',  'Parongpong'),
                    ('04_cek_dokumen',     'Dokumen Polandia OK.',                       'Parongpong'),
                    ('05_terminal_asal',   'Di terminal Ngurah Rai.',                   'Denpasar'),
                    ('06_transit',         'Penerbangan via Doha.',                      'In-flight'),
                    ('07_terminal_tujuan', 'Tiba di Warsaw Chopin.',                    'Warsaw WAW'),
                    ('08_bea_cukai',       'Lolos customs EU.',                         'Warsaw WAW'),
                    ('10_pengiriman',      'Dalam pengiriman.',                          'Warsaw'),
                    ('12_selesai',         'Diterima. Penerima lapor kondisi OK.',       'Warsaw'),
                ],
            },
            {
                'nama_penitip':    'Rizky Pratama',
                'hp_penitip':      '+62 819-3030-4040',
                'email_penitip':   'rizky@example.com',
                'alamat_penitip':  'Jl. Pahlawan No. 17, Malang 65113',
                'nama_penerima':   "Liam O'Brien",
                'hp_penerima':     '+61 2 9876 5432',
                'email_penerima':  'liam.obrien@email.au',
                'alamat_penerima': '42 George St, Sydney NSW 2000',
                'kota_tujuan':     'Sydney',
                'negara_tujuan':   'Australia',
                'layanan_lokal':   'southwest',
                'additional_packaging': 'tissue',
                'winter_packaging': 'none',
                'status':          'done',
                '_tanaman': [
                    {'nama_tanaman': 'Philodendron bipinnatifidum', 'jumlah': 3, 'ukuran': 'besar', 'kondisi': 'sehat'},
                    {'nama_tanaman': 'Syngonium podophyllum',       'jumlah': 8, 'ukuran': 'kecil', 'kondisi': 'sehat'},
                ],
                '_tahapan': [
                    ('01_registrasi',      'Pendaftaran berhasil.',                    'Malang'),
                    ('03_gudang_asal',     'Diterima di gudang.',                      'Parongpong'),
                    ('04_cek_dokumen',     'Dokumen Australia (DAFF) OK.',            'Parongpong'),
                    ('05_terminal_asal',   'Di terminal Juanda.',                      'Surabaya'),
                    ('06_transit',         'Penerbangan Surabaya–Sydney.',             'In-flight'),
                    ('07_terminal_tujuan', 'Tiba di Sydney Kingsford Smith.',          'Sydney SYD'),
                    ('08_bea_cukai',       'Lolos karantina DAFF Australia.',         'Sydney SYD'),
                    ('10_pengiriman',      'Pengiriman dalam kota Sydney.',            'Sydney'),
                    ('12_selesai',         'Diterima, kondisi excellent.',             'Sydney'),
                ],
            },
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────
# Seeder functions
# ─────────────────────────────────────────────────────────────────────

def seed_active_batch(models, uid):
    today = date.today()
    departure = (today + timedelta(days=14)).isoformat()

    print('\n📦 Membuat batch aktif...')
    batch_id = create(models, uid, 'agf.batch', {
        'tanggal_keberangkatan': departure,
        'tanggal_mulai':         today.isoformat(),
        'status':                'aktif',
        'catatan':               'Batch test data — generated by seed script',
    })
    info = search_read(models, uid, 'agf.batch', [('id', '=', batch_id)], ['name', 'batch_id'])
    batch_code = info[0]['batch_id']
    print(f"   Batch ID={batch_id}  kode={batch_code}  berangkat={departure}")

    print('\n🌿 Membuat kargo batch aktif (5 pesanan)...')
    kargo_ids = []
    for fixture in ACTIVE_KARGO:
        tanaman_data = fixture.pop('_tanaman')
        tahapan_data = fixture.pop('_tahapan')
        fixture['batch_id'] = batch_id

        kargo_id = create(models, uid, 'agf.kargo', fixture)
        kinfo = search_read(models, uid, 'agf.kargo', [('id', '=', kargo_id)], ['nomor_penitip'])
        print(f"   {kinfo[0]['nomor_penitip']}  ({fixture['status']})")

        for t in tanaman_data:
            t['kargo_id'] = kargo_id
            create(models, uid, 'agf.tanaman.item', t)
        add_tahapan(models, uid, kargo_id, tahapan_data)

        fixture['_tanaman'] = tanaman_data
        fixture['_tahapan'] = tahapan_data
        kargo_ids.append(kargo_id)

    return batch_id, batch_code, kargo_ids


def seed_historical_batches(models, uid):
    today = date.today()
    print('\n📋 Membuat batch historis...')
    hist_batch_ids = []
    hist_kargo_ids = []

    for spec in HIST_BATCHES:
        departure    = (today - timedelta(days=spec['offset_days'])).isoformat()
        tanggal_mulai = (today - timedelta(days=spec['offset_days'] + 14)).isoformat()

        batch_id = create(models, uid, 'agf.batch', {
            'tanggal_keberangkatan': departure,
            'tanggal_mulai':         tanggal_mulai,
            'status':                spec['status'],
            'catatan':               spec['catatan'],
        })
        binfo = search_read(models, uid, 'agf.batch', [('id', '=', batch_id)], ['name'])
        print(f"   {binfo[0]['name']}  (status={spec['status']}, berangkat={departure})")

        for fixture in spec['kargo']:
            tanaman_data = fixture.pop('_tanaman')
            tahapan_data = fixture.pop('_tahapan')
            fixture['batch_id'] = batch_id

            kargo_id = create(models, uid, 'agf.kargo', fixture)
            kinfo = search_read(models, uid, 'agf.kargo', [('id', '=', kargo_id)], ['nomor_penitip'])
            print(f"      {kinfo[0]['nomor_penitip']}  (done)")

            for t in tanaman_data:
                t['kargo_id'] = kargo_id
                create(models, uid, 'agf.tanaman.item', t)
            add_tahapan(models, uid, kargo_id, tahapan_data)

            fixture['_tanaman'] = tanaman_data
            fixture['_tahapan'] = tahapan_data
            hist_kargo_ids.append(kargo_id)

        hist_batch_ids.append(batch_id)

    return hist_batch_ids, hist_kargo_ids


def seed_qr_tags(models, uid, active_batch_id, active_kargo_ids, hist_batch_ids):
    print('\n🏷  Membuat QR tags...')
    binfo = search_read(models, uid, 'agf.batch', [('id', '=', active_batch_id)], ['batch_id'])
    batch_code = binfo[0]['batch_id']

    qr_fixtures = [
        {'status': 'aktif',  'kargo_id': active_kargo_ids[0], 'batch_id': active_batch_id},
        {'status': 'aktif',  'kargo_id': active_kargo_ids[1], 'batch_id': active_batch_id},
        {'status': 'idle',   'kargo_id': False,               'batch_id': active_batch_id},
        {'status': 'idle',   'kargo_id': False,               'batch_id': active_batch_id},
        {'status': 'rusak',  'kargo_id': False,               'batch_id': active_batch_id},
        {'status': 'rusak',  'kargo_id': False,               'batch_id': active_batch_id},
        {'status': 'rusak',  'kargo_id': False,               'batch_id': hist_batch_ids[0] if hist_batch_ids else active_batch_id},
    ]
    for i, qr in enumerate(qr_fixtures, 1):
        tag_id = f'QR-{batch_code}-{i:04d}'
        vals = {'tag_id': tag_id, 'status': qr['status'], 'batch_id': qr['batch_id']}
        if qr['kargo_id']:
            vals['kargo_id'] = qr['kargo_id']
        create(models, uid, 'agf.qr.tag', vals)
        print(f"   {tag_id}  ({qr['status']})")


def seed_test_users(models, uid, group_ids):
    print('\n👥 Membuat test users...')
    test_users = [
        {'name': 'Operator Manajer', 'login': 'manajer_test', 'password': 'Test@1234', 'group': 'manajer'},
        {'name': 'Petugas Gudang',   'login': 'gudang_test',  'password': 'Test@1234', 'group': 'gudang'},
    ]
    for spec in test_users:
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
            call(models, uid, 'res.users', 'write', [[user_id], {'groups_id': ops}])
            print(f"   → role: {spec['group']}")


def print_sql_commands(active_kargo_ids, hist_kargo_ids):
    """Print SQL yang perlu dijalankan untuk fitur alert & chart 7 hari."""
    hold_id = active_kargo_ids[2] if len(active_kargo_ids) > 2 else '?'

    # Spread active kargo across last 6 days; hist kargo already "old"
    spread = []
    day_offsets = [6, 5, 4, 2, 1]
    for kid, offset in zip(active_kargo_ids, day_offsets):
        spread.append(f"  UPDATE agf_kargo SET create_date = NOW() - INTERVAL '{offset} days' WHERE id = {kid};")
    # Hist batch kargo spread across older days (outside 7-day window — fine for history page)

    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 SQL OPSIONAL — jalankan di PostgreSQL untuk fitur:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] Dashboard Alert "Hold > 3 hari" (kargo Ahmad Fauzi id={hold_id}):
  UPDATE agf_kargo SET write_date = NOW() - INTERVAL '5 days' WHERE id = {hold_id};

[2] Bar chart 7 hari — sebar create_date kargo aktif:
""" + '\n'.join(spread) + f"""

Docker: docker compose exec db psql -U odoo -d {DB} -c "<query>"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")


# ─────────────────────────────────────────────────────────────────────

def seed(models, uid):
    ensure_admin_group(models, uid)
    group_ids = get_agf_group_ids(models, uid)

    active_batch_id, batch_code, active_kargo_ids = seed_active_batch(models, uid)
    hist_batch_ids, hist_kargo_ids                = seed_historical_batches(models, uid)
    seed_qr_tags(models, uid, active_batch_id, active_kargo_ids, hist_batch_ids)
    seed_test_users(models, uid, group_ids)

    # Summary
    binfo = search_read(models, uid, 'agf.batch', [('id', '=', active_batch_id)],
                        ['name', 'total_pesanan', 'total_tanaman'])
    b = binfo[0]
    today = date.today()
    departure = (today + timedelta(days=14)).isoformat()

    print(f"""
✅ Selesai! Data test siap.

Batch Aktif  : {b['name']}  (keberangkatan {departure})
  Pesanan    : {b['total_pesanan']}  (arrival / processing / hold / shipped / done)
  Tanaman    : {b['total_tanaman']} pcs

Batch Historis:
  2 batch (terkirim + selesai) × 3 kargo done = 6 kargo historis
  → Untuk test: Riwayat Batch, Detail Batch, Detail Pesanan Inactive

QR Tags      : 2 aktif, 2 idle, 3 rusak
Test Users   : manajer_test / gudang_test  (pw: Test@1234)

🌐 Admin Portal  : http://localhost:8069/agf/admin
🌐 Warehouse     : http://localhost:8069/agf/warehouse
   Login         : admin / admin
""")

    print_sql_commands(active_kargo_ids, hist_kargo_ids)


if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    uid, models = connect()

    if '--fresh' in sys.argv:
        clear_existing(models, uid)

    seed(models, uid)
