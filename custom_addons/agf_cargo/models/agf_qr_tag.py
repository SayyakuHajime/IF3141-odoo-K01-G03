from odoo import models, fields, api
import qrcode
import base64
from io import BytesIO


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
    qr_image = fields.Binary(
        string='QR Image',
        attachment=True,
        readonly=True,
    )

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if not vals.get('tag_id'):
    #             batch = self.env['agf.batch'].browse(vals.get('batch_id'))
    #             seq = self.env['ir.sequence'].next_by_code('agf.qr.tag') or '0000'
    #             prefix = batch.batch_id if batch and batch.batch_id else 'AGF'
    #             vals['tag_id'] = f'QR-{prefix}-{seq}'
    #     return super().create(vals_list)

    def action_assign(self, kargo_id):
        """Assign tag ke pesanan kargo; set status aktif."""
        self.ensure_one()
        self.write({'kargo_id': kargo_id, 'status': 'aktif'})

    def action_release(self):
        """Lepas tag dari pesanan; kembalikan ke idle."""
        self.write({'kargo_id': False, 'status': 'idle'})

    def action_mark_rusak(self):
        self.write({'status': 'rusak'})

    def _generate_qr_image(self):
        """Generate QR image dari tag_id dan simpan ke field qr_image."""
        for tag in self:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            # Yang di-encode adalah tag_id — warehouse scan ini untuk lookup ke kargo
            qr.add_data(tag.tag_id)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            buffer = BytesIO()
            img.save(buffer, 'PNG')
            tag.qr_image = base64.b64encode(buffer.getvalue()).decode()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('tag_id'):
                seq = self.env['ir.sequence'].next_by_code('agf.qr.tag') or '0000'
                batch_id = vals.get('batch_id')
                if batch_id:
                    batch = self.env['agf.batch'].browse(batch_id)
                    prefix = batch.batch_id if batch.exists() and batch.batch_id else 'AGF'
                else:
                    prefix = 'AGF'
                vals['tag_id'] = f'QR-{prefix}-{seq}'
        records = super().create(vals_list)
        records._generate_qr_image()
        return records