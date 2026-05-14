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

    # Status sekarang identik dengan key tahapan — single source of truth.
    # Nilai diupdate otomatis oleh agf.tahapan.create(), bukan diisi manual.
    status = fields.Selection(
        selection=[
            ('01_registrasi',       'Pendaftaran Kargo'),
            ('02_menunggu_bayar',   'Menunggu Pembayaran'),
            ('03_bayar_verified',   'Pembayaran Terverifikasi'),
            ('04_penjemputan',      'Penjemputan Tanaman'),
            ('05_gudang_asal',      'Di Gudang Asal'),
            ('06_terminal_asal',    'Terminal Asal'),
            ('07_transit',          'Dalam Perjalanan'),
            ('08_terminal_tujuan',  'Terminal Tujuan'),
            ('09_bea_cukai',        'Bea Cukai'),
            ('10_pengiriman_lokal', 'Pengiriman Lokal'),
            ('11_tiba',             'Tiba di Tujuan'),
            ('12_selesai',          'Selesai'),
        ],
        string='Status',
        default='01_registrasi',
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

    # Bukti pembayaran — satu field, diupload customer lewat tracking page
    bukti_pembayaran = fields.Many2one(
        'ir.attachment',
        string='Bukti Pembayaran',
        ondelete='set null',
        help='Diupload oleh customer. Admin verifikasi dengan membuat tahapan 03_bayar_verified.',
    )

    konfirmasi_penjemputan = fields.Boolean(
        string='Tanaman Sudah Diambil (Konfirmasi Customer)',
        default=False,
    )

    # bukti_transaksi dihapus — digabung ke bukti_pembayaran.
    # Kalau admin perlu attach file, gunakan foto_ids di tahapan 03_bayar_verified.

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

    # Helper computed untuk template — CSS class pill sesuai status
    status_pill_class = fields.Char(
        string='CSS Pill Class',
        compute='_compute_status_pill',
    )
    status_label = fields.Char(
        string='Label Status',
        compute='_compute_status_pill',
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
            # Hanya tahapan publik yang dihitung sebagai "terakhir" untuk customer
            publik = kargo.tahapan_ids.filtered(lambda t: not t.is_internal)
            kargo.tahapan_terakhir = publik[:1] if publik else kargo.tahapan_ids[:1]

    @api.depends('status')
    def _compute_status_pill(self):
        # Grouping status ke dalam 5 visual bucket untuk pill color
        bucket_map = {
            '01_registrasi':       ('pill-registrasi', 'Pendaftaran'),
            '02_menunggu_bayar':   ('pill-menunggu',   'Menunggu Bayar'),
            '03_bayar_verified':   ('pill-verified',   'Bayar Verified'),
            '04_penjemputan':      ('pill-penjemputan','Penjemputan'),
            '05_gudang_asal':      ('pill-gudang',     'Di Gudang'),
            '06_terminal_asal':    ('pill-transit',    'Terminal Asal'),
            '07_transit':          ('pill-transit',    'Dalam Perjalanan'),
            '08_terminal_tujuan':  ('pill-transit',    'Terminal Tujuan'),
            '09_bea_cukai':        ('pill-transit',    'Bea Cukai'),
            '10_pengiriman_lokal': ('pill-shipped',    'Pengiriman Lokal'),
            '11_tiba':             ('pill-shipped',    'Tiba di Tujuan'),
            '12_selesai':          ('pill-done',       'Selesai'),
        }
        for kargo in self:
            cls, label = bucket_map.get(kargo.status, ('pill-registrasi', kargo.status))
            kargo.status_pill_class = cls
            kargo.status_label = label

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
            # Status awal selalu registrasi
            if not vals.get('status'):
                vals['status'] = '01_registrasi'

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
        # Saat status mencapai selesai, lepas QR tag
        if vals.get('status') == '12_selesai':
            for kargo in self:
                if kargo.qr_tag_id:
                    kargo.qr_tag_id.action_release()
                    kargo.qr_tag_id = False
        return result