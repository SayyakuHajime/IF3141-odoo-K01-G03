from odoo import models, fields


class AgfKargoLog(models.Model):
    _name = 'agf.kargo.log'
    _description = 'Log Aktivitas Pesanan'
    _order = 'timestamp desc, id desc'

    kargo_id = fields.Many2one(
        'agf.kargo',
        string='Pesanan',
        required=True,
        ondelete='cascade',
        index=True,
    )
    jenis = fields.Selection(
        selection=[
            ('status', 'Perubahan Status'),
            ('detail', 'Perubahan Detail'),
        ],
        string='Jenis Perubahan',
        required=True,
    )
    deskripsi = fields.Char(string='Deskripsi', required=True)
    user_id = fields.Many2one(
        'res.users',
        string='Diubah Oleh',
        default=lambda self: self.env.user,
        readonly=True,
    )
    timestamp = fields.Datetime(
        string='Waktu',
        default=fields.Datetime.now,
        readonly=True,
    )