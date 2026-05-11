from odoo import http
from odoo.http import request


class AdminPortal(http.Controller):
    
    def _get_user_initials(self):
        name = request.env.user.name or 'AD'
        parts = name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper()

    @http.route('/agf/admin', type='http', auth='user', website=True)
    def redirect_dashboard(self, **kwargs):
        return request.redirect('/agf/admin/dashboard')

    @http.route('/agf/admin/dashboard', type='http', auth='user', website=True)
    def dashboard(self, **kwargs):
        batch_aktif = request.env['agf.batch'].search([('status', '=', 'aktif')], limit=1)
        total_pesanan = request.env['agf.kargo'].search_count([])
        total_qr = request.env['agf.qr.tag'].search_count([])
        qr_aktif = request.env['agf.qr.tag'].search_count([('status', '=', 'aktif')])
        return request.render('agf_cargo.admin_dashboard', {
            'batch_aktif': batch_aktif,
            'total_pesanan': total_pesanan,
            'total_qr': total_qr,
            'qr_aktif': qr_aktif,
            'user_initials': self._get_user_initials(),
        })

    @http.route('/agf/admin/pesanan', type='http', auth='user', website=True)
    def batch_aktif(self, status=None, search=None, **kwargs):
        domain = []
        batch = request.env['agf.batch'].search([('status', '=', 'aktif')], limit=1)
        if batch:
            domain.append(('batch_id', '=', batch.id))
        if status:
            domain.append(('status', '=', status))
        if search:
            domain += ['|', ('nomor_penitip', 'ilike', search), ('nama_penitip', 'ilike', search)]
        kargo_list = request.env['agf.kargo'].search(domain)
        return request.render('agf_cargo.admin_batch_aktif', {
            'batch': batch,
            'kargo_list': kargo_list,
            'current_status': status,
            'search': search,
            'user_initials': self._get_user_initials(),
        })

    @http.route('/agf/admin/pesanan/<int:kargo_id>', type='http', auth='user', website=True)
    def detail_pesanan(self, kargo_id, **kwargs):
        kargo = request.env['agf.kargo'].browse(kargo_id)
        if not kargo.exists():
            return request.not_found()
        return request.render('agf_cargo.admin_detail_pesanan_aktif', {'kargo': kargo, 'user_initials': self._get_user_initials(),})

    @http.route('/agf/admin/pesanan/baru', type='http', auth='user', website=True)
    def form_pesanan(self, **kwargs):
        batch_aktif = request.env['agf.batch'].search([('status', '=', 'aktif')], limit=1)
        return request.render('agf_cargo.admin_form_pesanan', {'batch_aktif': batch_aktif, 'user_initials': self._get_user_initials(),})

    @http.route('/agf/admin/qr', type='http', auth='user', website=True)
    def qr_management(self, **kwargs):
        tags = request.env['agf.qr.tag'].search([])
        stats = {
            'total': len(tags),
            'aktif': len(tags.filtered(lambda t: t.status == 'aktif')),
            'idle': len(tags.filtered(lambda t: t.status == 'idle')),
            'rusak': len(tags.filtered(lambda t: t.status == 'rusak')),
        }
        return request.render('agf_cargo.admin_qr_code', {'tags': tags, 'stats': stats, 'user_initials': self._get_user_initials(),})

    @http.route('/agf/admin/batch', type='http', auth='user', website=True)
    def riwayat_batch(self, **kwargs):
        batches = request.env['agf.batch'].search([], order='tanggal_mulai desc')
        return request.render('agf_cargo.admin_riwayat_batch', {'batches': batches, 'user_initials': self._get_user_initials(),})

    @http.route('/agf/admin/batch/<int:batch_id>', type='http', auth='user', website=True)
    def detail_batch(self, batch_id, **kwargs):
        batch = request.env['agf.batch'].browse(batch_id)
        if not batch.exists():
            return request.not_found()
        return request.render('agf_cargo.admin_detail_batch', {'batch': batch, 'user_initials': self._get_user_initials(),})

    @http.route('/agf/admin/pengguna', type='http', auth='user', website=True)
    def pengguna(self, **kwargs):
        users = request.env['res.users'].search([('share', '=', False)])
        return request.render('agf_cargo.admin_pengguna', {'users': users, 'user_initials': self._get_user_initials(),})
