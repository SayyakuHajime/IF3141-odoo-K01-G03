from odoo import models, fields, api


TAHAPAN_STEPS = [
    ('01_registrasi',       'Pendaftaran Kargo'),
    ('02_menunggu_bayar',   'Menunggu Pembayaran'),
    ('03_bayar_verified',   'Pembayaran Terverifikasi'),
    ('04_penjemputan',      'Penjemputan Tanaman'),
    ('05_gudang_asal',      'Penerimaan di Gudang Asal'),
    ('06_terminal_asal',    'Persiapan Pengiriman Internasional'),
    ('07_transit',          'Dalam Perjalanan ke Negara Tujuan'),
    ('08_terminal_tujuan',  'Tiba di Negara Tujuan'),
    ('09_bea_cukai',        'Proses Bea Cukai'),
    ('10_pengiriman_lokal', 'Diserahkan ke Kurir Lokal'),
    ('11_tiba',             'Tiba di Alamat Penerima'),
    ('12_selesai',          'Selesai'),
]


class AgfTahapan(models.Model):
    _name = 'agf.tahapan'
    _description = 'Log Tahapan & Aktivitas Pesanan Kargo'
    _order = 'timestamp desc, id desc'

    kargo_id = fields.Many2one(
        'agf.kargo',
        string='Pesanan Kargo',
        required=True,
        ondelete='cascade',
        index=True,
    )

    tahap = fields.Selection(
        selection=TAHAPAN_STEPS,
        string='Tahapan',
        required=True,
    )

    # is_internal=True → hanya terlihat di admin, tidak muncul di customer tracking.
    # Gunakan untuk log koreksi data, catatan internal, dsb.
    is_internal = fields.Boolean(
        string='Internal (Admin Only)',
        default=False,
        help='Jika dicentang, log ini tidak akan muncul di halaman tracking customer.',
    )

    lokasi = fields.Char(string='Lokasi')
    catatan = fields.Text(string='Catatan / Keterangan')

    # Foto via ir.attachment — bukan Binary agar database tidak berat
    foto_ids = fields.Many2many(
        'ir.attachment',
        'agf_tahapan_foto_rel',
        'tahapan_id',
        'attachment_id',
        string='Foto Kondisi',
        help='Maksimal 3 foto per tahapan',
    )

    timestamp = fields.Datetime(
        string='Waktu',
        default=fields.Datetime.now,
        required=True,
        readonly=True,
    )
    petugas_id = fields.Many2one(
        'res.users',
        string='Petugas',
        default=lambda self: self.env.user,
        readonly=True,
    )

    # Checklist kondisi tanaman (opsional, diisi tim gudang)
    cek_daun = fields.Boolean(string='Daun OK')
    cek_akar = fields.Boolean(string='Akar OK')
    cek_hama = fields.Boolean(string='Bebas Hama')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        step_keys = [s[0] for s in TAHAPAN_STEPS]
        for rec in records:
            if not rec.is_internal and rec.tahap:
                current = rec.kargo_id.status
                current_idx = step_keys.index(current) if current in step_keys else -1
                new_idx = step_keys.index(rec.tahap) if rec.tahap in step_keys else -1
                if new_idx >= current_idx:
                    rec.kargo_id.sudo().write({'status': rec.tahap})
        return records