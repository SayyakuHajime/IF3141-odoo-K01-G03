from odoo import models, fields, api


class AgfQrTag(models.Model):
    _name = 'agf.qr.tag'
    _description = 'QR Tag Fisik Reusable — AGF Cargo'
    _order = 'tag_id'

    _sql_constraints = [
        ('tag_id_unique', 'UNIQUE(tag_id)', 'QR Tag ID harus unik!'),
    ]

    tag_id = fields.Char(
        string='QR Tag ID',
        required=True,
        copy=False,
        index=True,
    )
    status = fields.Selection(
        selection=[
            ('idle', 'Idle'),
            ('aktif', 'Aktif'),
            ('rusak', 'Rusak'),
        ],
        string='Status',
        default='idle',
        required=True,
        index=True,
    )

    kargo_id = fields.Many2one(
        'agf.kargo',
        string='Pesanan Aktif',
        ondelete='set null',
        help='Pesanan kargo yang sedang menggunakan tag ini',
    )
    batch_id = fields.Many2one(
        'agf.batch',
        string='Batch',
        ondelete='set null',
    )

    catatan = fields.Text(string='Catatan')
    tanggal_cetak = fields.Date(string='Tanggal Cetak', default=fields.Date.today)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('tag_id'):
                batch = self.env['agf.batch'].browse(vals.get('batch_id'))
                seq = self.env['ir.sequence'].next_by_code('agf.qr.tag') or '0000'
                prefix = batch.batch_id if batch and batch.batch_id else 'AGF'
                vals['tag_id'] = f'QR-{prefix}-{seq}'
        return super().create(vals_list)

    def action_assign(self, kargo_id):
        """Assign tag ke pesanan kargo; set status aktif."""
        self.ensure_one()
        self.write({'kargo_id': kargo_id, 'status': 'aktif'})

    def action_release(self):
        """Lepas tag dari pesanan; kembalikan ke idle."""
        self.write({'kargo_id': False, 'status': 'idle'})

    def action_mark_rusak(self):
        self.write({'status': 'rusak'})
