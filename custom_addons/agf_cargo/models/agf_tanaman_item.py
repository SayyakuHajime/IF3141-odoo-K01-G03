from odoo import models, fields, api


class AgfTanamanItem(models.Model):
    _name = 'agf.tanaman.item'
    _description = 'Item Tanaman dalam Pesanan Kargo'
    _order = 'kargo_id, id'

    kargo_id = fields.Many2one(
        'agf.kargo',
        string='Pesanan Kargo',
        required=True,
        ondelete='cascade',
        index=True,
    )

    nama_tanaman = fields.Char(string='Nama / Genus Tanaman', required=True)
    jumlah = fields.Integer(string='Jumlah', required=True, default=1)
    ukuran = fields.Selection(
        selection=[
            ('kecil', 'Kecil'),
            ('sedang', 'Sedang'),
            ('besar', 'Besar'),
        ],
        string='Ukuran',
        default='sedang',
    )
    kondisi = fields.Selection(
        selection=[
            ('sehat', 'Sehat'),
            ('kurang_sehat', 'Kurang Sehat'),
            ('bermasalah', 'Bermasalah'),
            ('belum_dicek', 'Belum Dicek'),
        ],
        string='Kondisi',
        default='belum_dicek',
        required=True,
    )
    status_persiapan = fields.Selection(
        selection=[
            ('belum_mulai',      'Belum Mulai'),
            ('pengecekan_awal',  'Pengecekan Awal'),
            ('pencucian',        'Pencucian'),
            ('pengemasan',       'Pengemasan'),
            ('pengecekan_akhir', 'Pengecekan Akhir'),
            ('siap_kirim',       'Siap Kirim'),
        ],
        string='Status Persiapan',
        default='belum_mulai',
    )

    # Checklist kondisi detail (diisi saat warehouse update)
    cek_daun = fields.Boolean(string='Daun OK')
    cek_akar = fields.Boolean(string='Akar OK')
    cek_hama = fields.Boolean(string='Bebas Hama')

    catatan_kondisi = fields.Text(string='Catatan Kondisi')

    qr_tag_id = fields.Many2one(
        'agf.qr.tag',
        string='QR Tag',
        ondelete='set null',
    )

    @api.constrains('jumlah')
    def _check_jumlah(self):
        for item in self:
            if item.jumlah < 1:
                from odoo.exceptions import ValidationError
                raise ValidationError('Jumlah tanaman minimal 1.')
