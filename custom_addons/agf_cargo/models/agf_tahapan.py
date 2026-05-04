from odoo import models, fields


TAHAPAN_STEPS = [
    ('01_registrasi', 'Pendaftaran Kargo'),
    ('02_penjemputan', 'Penjemputan'),
    ('03_gudang_asal', 'Penerimaan di Gudang Asal'),
    ('04_cek_dokumen', 'Pemeriksaan Dokumen'),
    ('05_terminal_asal', 'Terminal Kargo Asal'),
    ('06_transit', 'Dalam Perjalanan'),
    ('07_terminal_tujuan', 'Terminal Kargo Tujuan'),
    ('08_bea_cukai', 'Pemeriksaan Bea Cukai'),
    ('09_gudang_tujuan', 'Gudang Tujuan'),
    ('10_pengiriman', 'Dalam Pengiriman'),
    ('11_tiba', 'Tiba di Alamat'),
    ('12_selesai', 'Selesai'),
]


class AgfTahapan(models.Model):
    _name = 'agf.tahapan'
    _description = 'Log Perubahan Status Tahapan Pengiriman'
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

    # Checklist kondisi (untuk halaman Update Status warehouse)
    cek_daun = fields.Boolean(string='Daun OK')
    cek_akar = fields.Boolean(string='Akar OK')
    cek_hama = fields.Boolean(string='Bebas Hama')

    status_baru = fields.Selection(
        selection=[
            ('hold', 'Hold'),
            ('arrival', 'Arrival'),
            ('processing', 'Processing'),
            ('shipped', 'Shipped'),
            ('done', 'Done'),
        ],
        string='Status Setelah Tahapan',
    )
