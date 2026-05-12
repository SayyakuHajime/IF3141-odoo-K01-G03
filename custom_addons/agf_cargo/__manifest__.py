{
    'name': 'AGF Cargo',
    'version': '17.0.1.0.0',
    'summary': 'Sistem Manajemen Kargo Tanaman — PT Berkah Melano Indonesia',
    'author': 'K01-G03 IF3141',
    'category': 'Logistics',
    'depends': ['base', 'web', 'portal', 'website'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        
        'views/assets.xml',  
        
        # Warehouse views (Hazim)
        'views/warehouse/wh_landing.xml',
        'views/warehouse/wh_daftar_pesanan.xml',
        'views/warehouse/wh_detail_pesanan.xml',
        'views/warehouse/wh_update_status.xml',
        
        # Admin Layout Base
        'views/admin/admin_layout.xml',
        
        # Admin views 
        'views/admin/admin_dashboard.xml',
        'views/admin/batch.xml', 
        'views/admin/pesanan.xml', 
        'views/admin/qr.xml',
        'views/admin/admin_riwayat_batch.xml',
        'views/admin/admin_detail_batch.xml',
        'views/admin/admin_detail_pesanan_inactive.xml',
        'views/admin/admin_pengguna.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}