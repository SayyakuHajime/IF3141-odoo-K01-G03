from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AgfBatch(models.Model):
    _name = 'agf.batch'
    _description = 'Batch Pengiriman AGF Cargo'
    _order = 'tanggal_keberangkatan desc, id desc'

    name = fields.Char(
        string='Nama Batch',
        required=True,
        copy=False,
        default='New',
    )
    batch_id = fields.Char(
        string='Kode Batch',
        required=True,
        copy=False,
        index=True,
    )
    status = fields.Selection(
        selection=[
            ('aktif', 'Aktif'),
            ('selesai', 'Selesai'),
            ('terkirim', 'Terkirim'),
            ('dibatalkan', 'Dibatalkan'),
        ],
        string='Status',
        default='aktif',
        required=True,
        index=True,
    )

    # Tanggal buka pendaftaran ke batch ini
    tanggal_mulai = fields.Date(
        string='Tanggal Buka Pendaftaran',
        required=True,
        default=fields.Date.today,
    )
    # Tanggal keberangkatan ditetapkan admin di sini → baru diumumkan ke channel lain (IG, WA, dll)
    tanggal_keberangkatan = fields.Date(
        string='Tanggal Keberangkatan',
        required=True,
        help='Tanggal pengiriman dari Indonesia ke negara tujuan. Ditetapkan admin, lalu dikomunikasikan ke customer. bisa juga dilihat pengumuman Instagram @artgarden.flowers',
    )
    tanggal_selesai = fields.Date(string='Tanggal Tutup Pendaftaran')
    catatan = fields.Text(string='Catatan')
    negara_tujuan = fields.Char(
        string='Negara Tujuan',
        default='United States',
    )
    kapasitas_maks = fields.Integer(
        string='Kapasitas Maksimal (tanaman)',
        default=0,
        help='0 = tidak dibatasi',
    )

    kargo_ids = fields.One2many('agf.kargo', 'batch_id', string='Daftar Pesanan')

    total_pesanan = fields.Integer(
        string='Total Pesanan',
        compute='_compute_stats',
        store=True,
    )
    total_tanaman = fields.Integer(
        string='Total Tanaman',
        compute='_compute_stats',
        store=True,
    )
    pesanan_selesai = fields.Integer(
        string='Pesanan Selesai',
        compute='_compute_stats',
        store=True,
    )

    @api.depends('kargo_ids', 'kargo_ids.status', 'kargo_ids.tanaman_ids')
    def _compute_stats(self):
        for batch in self:
            batch.total_pesanan = len(batch.kargo_ids)
            batch.total_tanaman = sum(batch.kargo_ids.mapped('tanaman_ids').mapped('jumlah'))
            batch.pesanan_selesai = len(batch.kargo_ids.filtered(lambda k: k.status == '12_selesai'))

    @api.constrains('status')
    def _check_single_aktif(self):
        """Hanya boleh ada satu batch berstatus 'aktif' pada satu waktu."""
        for batch in self:
            if batch.status == 'aktif':
                lain = self.search([('status', '=', 'aktif'), ('id', '!=', batch.id)])
                if lain:
                    raise ValidationError(
                        f'Sudah ada batch aktif: "{lain[0].name}" '
                        f'(keberangkatan {lain[0].tanggal_keberangkatan}). '
                        f'Tutup batch tersebut sebelum mengaktifkan batch baru.'
                    )

    def action_tutup(self):
        """Tutup batch aktif → selesai. Dipakai admin setelah pengiriman selesai diproses."""
        self.ensure_one()
        self.status = 'selesai'

    def action_terkirim(self):
        """Tandai batch sebagai terkirim — semua pesanan sudah sampai tujuan."""
        self.ensure_one()
        self.status = 'terkirim'

    def action_cancel(self):
        self.ensure_one()
        self.status = 'dibatalkan'
        
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq = self.env['ir.sequence'].next_by_code('agf.batch') or 'New'
                vals['name'] = seq
            if not vals.get('batch_id'):
                vals['batch_id'] = vals.get('name', 'New')
        return super().create(vals_list)
