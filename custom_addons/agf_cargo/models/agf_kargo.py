from odoo import models, fields, api


class AgfKargo(models.Model):
    _name = 'agf.kargo'
    _description = 'Pesanan Kargo AGF Cargo'
    _order = 'id desc'

    name = fields.Char(
        string='Referensi',
        readonly=True,
        copy=False,
        default='New',
    )

    # --- Dual nomor via ir.sequence ---
    nomor_penitip = fields.Char(
        string='Nomor Penitip',
        readonly=True,
        copy=False,
        index=True,
        help='Nomor untuk penitip / pengirim — prefix AGF-',
    )
    nomor_penerima = fields.Char(
        string='Nomor Penerima',
        readonly=True,
        copy=False,
        index=True,
        help='Nomor untuk penerima / pembeli — prefix TRK-',
    )

    batch_id = fields.Many2one(
        'agf.batch',
        string='Batch',
        ondelete='restrict',
        index=True,
    )

    status = fields.Selection(
        selection=[
            ('hold', 'Hold'),
            ('arrival', 'Arrival'),
            ('processing', 'Processing'),
            ('shipped', 'Shipped'),
            ('done', 'Done'),
        ],
        string='Status',
        default='hold',
        required=True,
        index=True,
    )

    # --- Info penitip (pengirim) ---
    nama_penitip = fields.Char(string='Nama Pengirim', required=True)
    hp_penitip = fields.Char(string='No. HP Pengirim', required=True)
    email_penitip = fields.Char(string='Email Pengirim', required=True)
    alamat_penitip = fields.Text(string='Alamat Pengirim', required=True)

    # --- Info penerima ---
    nama_penerima = fields.Char(string='Nama Penerima', required=True)
    hp_penerima = fields.Char(string='No. HP Penerima', required=True)
    email_penerima = fields.Char(string='Email Penerima', required=True)
    alamat_penerima = fields.Text(
        string='Alamat Lengkap Penerima + Kode Pos',
        required=True,
        help='Sertakan kode pos di akhir alamat',
    )
    kota_tujuan = fields.Char(string='Kota Tujuan')
    negara_tujuan = fields.Char(string='Negara Tujuan')

    # --- Pengiriman ---
    # Computed dari batch — tidak perlu diisi customer, otomatis ikut batch aktif saat pendaftaran
    tanggal_keberangkatan = fields.Date(
        string='Tanggal Keberangkatan',
        compute='_compute_tanggal_keberangkatan',
        store=True,
        help='Otomatis diambil dari tanggal keberangkatan batch yang ditetapkan admin.',
    )
    layanan_lokal = fields.Selection(
        selection=[
            ('reguler', 'Reguler 3–5 Hari UPS/USPS'),
            ('next_day', 'Next Day 1–2 Hari UPS/USPS (Biaya Tambahan)'),
            ('southwest', 'SouthWest Cargo — Pickup at Local Airport (Biaya Tambahan)'),
        ],
        string='Layanan Lokal',
        required=True,
        default='reguler',
    )

    # --- Packaging tambahan ---
    additional_packaging = fields.Selection(
        selection=[
            ('none', 'None'),
            ('dakron', 'Dakron (Poly Fill)'),
            ('tissue', 'Tissue'),
        ],
        string='Additional Packaging',
        required=True,
        default='none',
    )
    winter_packaging = fields.Selection(
        selection=[
            ('none', 'None'),
            ('heat_pack', 'Heat Pack'),
            ('insulation', 'Insulation'),
            ('heat_insulation', 'Heatpack & Insulation'),
        ],
        string='Winter Packaging',
        required=True,
        default='none',
        help='Special winter request — semua +$8',
    )

    catatan = fields.Text(string='Catatan')
    bukti_pembayaran = fields.Many2one(
        'ir.attachment',
        string='Bukti Pembayaran',
        ondelete='set null',
    )
    konfirmasi_penjemputan = fields.Boolean(
        string='Tanaman Sudah Diambil',
        default=False,
    )
    bukti_transaksi = fields.Binary(
        string='Bukti Transaksi',
        attachment=True,
    )
    bukti_transaksi_nama = fields.Char(string='Nama File Bukti Transaksi')
    tanggal_daftar = fields.Datetime(
        string='Tanggal Pendaftaran',
        default=fields.Datetime.now,
        readonly=True,
    )

    tanaman_ids = fields.One2many('agf.tanaman.item', 'kargo_id', string='Daftar Tanaman')
    tahapan_ids = fields.One2many(
        'agf.tahapan', 'kargo_id',
        string='Riwayat Tahapan',
    )
    qr_tag_id = fields.Many2one(
        'agf.qr.tag',
        string='QR Tag Aktif',
        ondelete='set null',
    )

    total_tanaman = fields.Integer(
        string='Total Tanaman',
        compute='_compute_total_tanaman',
        store=True,
    )
    tahapan_terakhir = fields.Many2one(
        'agf.tahapan',
        string='Tahapan Terakhir',
        compute='_compute_tahapan_terakhir',
    )
    
    log_ids = fields.One2many(
        'agf.kargo.log',
        'kargo_id',
        string='Log Aktivitas',
    )

    @api.depends('batch_id', 'batch_id.tanggal_keberangkatan')
    def _compute_tanggal_keberangkatan(self):
        for kargo in self:
            kargo.tanggal_keberangkatan = kargo.batch_id.tanggal_keberangkatan if kargo.batch_id else False

    @api.depends('tanaman_ids', 'tanaman_ids.jumlah')
    def _compute_total_tanaman(self):
        for kargo in self:
            kargo.total_tanaman = sum(kargo.tanaman_ids.mapped('jumlah'))

    @api.depends('tahapan_ids')
    def _compute_tahapan_terakhir(self):
        for kargo in self:
            kargo.tahapan_terakhir = kargo.tahapan_ids[:1]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('nomor_penitip'):
                vals['nomor_penitip'] = (
                    self.env['ir.sequence'].next_by_code('agf.kargo.penitip') or '/'
                )
            if not vals.get('nomor_penerima'):
                vals['nomor_penerima'] = (
                    self.env['ir.sequence'].next_by_code('agf.kargo.penerima') or '/'
                )
            if vals.get('name', 'New') == 'New':
                vals['name'] = vals.get('nomor_penitip', 'New')
        
        records = super().create(vals_list)
        
        # Auto-assign QR tag idle ke setiap kargo baru
        for kargo in records:
            qr_idle = self.env['agf.qr.tag'].search(
                [('status', '=', 'idle')], limit=1
            )
            if qr_idle:
                qr_idle.action_assign(kargo.id)
                kargo.qr_tag_id = qr_idle.id
        
        return records
    
    def write(self, vals):
        result = super().write(vals)
        if vals.get('status') == 'done':
            for kargo in self:
                if kargo.qr_tag_id:
                    kargo.qr_tag_id.action_release()
                    kargo.qr_tag_id = False
        return result
