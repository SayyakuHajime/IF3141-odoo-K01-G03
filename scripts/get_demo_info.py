#!/usr/bin/env python3
"""
Ambil nomor resi dan info login untuk persiapan demo.
Jalankan SETELAH seed_test_data_2.py.

Usage: python3 scripts/get_demo_info.py
"""
import xmlrpc.client

URL      = 'http://localhost:8069'
DB       = 'postgres'
USERNAME = 'admin'
PASSWORD = 'admin'

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid    = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

def call(model, method, args, kwargs=None):
    return models.execute_kw(DB, uid, PASSWORD, model, method, args, kwargs or {})

# Ambil kargo K4 (Dewi Permata) dan K6 (Fajar Nugroho)
targets = ['Dewi Permata', 'Fajar Nugroho']
rows = call('agf.kargo', 'search_read',
    [[('nama_penitip', 'in', targets)]],
    {'fields': ['nama_penitip', 'nomor_penitip', 'nomor_penerima', 'status', 'id']}
)

print('\n' + '═'*55)
print('  INFO DEMO WAREHOUSE — nomor resi & login')
print('═'*55)

for r in sorted(rows, key=lambda x: x['nama_penitip']):
    print(f"\n  Kargo   : {r['nama_penitip']} (id={r['id']})")
    print(f"  Status  : {r['status']}")
    print(f"  AGF-    : {r['nomor_penitip']}   ← buka di Customer Portal (penitip)")
    print(f"  TRK-    : {r['nomor_penerima']}  ← buka di Customer Portal (penerima)")

print('\n' + '─'*55)
print('  Login Warehouse App  : gudang_test / Test@1234')
print('  Login Admin Dashboard: admin / admin')
print('                         atau: manajer_test / Test@1234')
print('─'*55)
print('\n  URL:')
print('  Customer Portal  → http://localhost:8069/agf/customer')
print('  Warehouse App    → http://localhost:8069/agf/warehouse')
print('  Admin Dashboard  → http://localhost:8069/agf/admin')
print('═'*55 + '\n')
