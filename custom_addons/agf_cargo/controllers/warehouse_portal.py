from odoo import http
from odoo.http import request


class WarehousePortal(http.Controller):

    @http.route('/agf/warehouse', type='http', auth='user', website=True)
    def landing(self, **kwargs):
        return request.render('agf_cargo.warehouse_landing', {})

    @http.route('/agf/warehouse/pesanan', type='http', auth='user', website=True)
    def daftar_pesanan(self, **kwargs):
        batch_aktif = request.env['agf.batch'].search([('status', '=', 'aktif')], limit=1)
        kargo_list = batch_aktif.kargo_ids if batch_aktif else []
        return request.render('agf_cargo.warehouse_daftar_pesanan', {
            'batch': batch_aktif,
            'kargo_list': kargo_list,
        })

    @http.route('/agf/warehouse/pesanan/<int:kargo_id>', type='http', auth='user', website=True)
    def detail_pesanan(self, kargo_id, **kwargs):
        kargo = request.env['agf.kargo'].browse(kargo_id)
        if not kargo.exists():
            return request.not_found()
        return request.render('agf_cargo.warehouse_detail_pesanan', {'kargo': kargo})

    @http.route('/agf/warehouse/scan', type='http', auth='user', website=True)
    def scan_qr(self, **kwargs):
        return request.render('agf_cargo.warehouse_scan_qr', {})

    @http.route('/agf/warehouse/scan/result', type='json', auth='user')
    def scan_result(self, tag_id, **kwargs):
        tag = request.env['agf.qr.tag'].sudo().search([('tag_id', '=', tag_id)], limit=1)
        if not tag:
            return {'found': False}
        return {
            'found': True,
            'tag_id': tag.tag_id,
            'status': tag.status,
            'kargo_id': tag.kargo_id.id if tag.kargo_id else None,
            'kargo_ref': tag.kargo_id.name if tag.kargo_id else None,
            'nama_penitip': tag.kargo_id.nama_penitip if tag.kargo_id else None,
        }

    @http.route('/agf/warehouse/update/<int:kargo_id>', type='http', auth='user', website=True)
    def update_status(self, kargo_id, **kwargs):
        kargo = request.env['agf.kargo'].browse(kargo_id)
        if not kargo.exists():
            return request.not_found()
        return request.render('agf_cargo.warehouse_update_status', {
            'kargo': kargo,
            'tahapan_steps': request.env['agf.tahapan']._fields['tahap'].selection,
            'status_choices': request.env['agf.kargo']._fields['status'].selection,
        })

    @http.route('/agf/warehouse/update/<int:kargo_id>/submit', type='http', auth='user', methods=['POST'], website=True)
    def update_status_submit(self, kargo_id, **post):
        kargo = request.env['agf.kargo'].browse(kargo_id)
        if not kargo.exists():
            return request.not_found()

        tahap = post.get('tahap')
        lokasi = post.get('lokasi', '')
        catatan = post.get('catatan', '')
        status_baru = post.get('status_baru')
        cek_daun = bool(post.get('cek_daun'))
        cek_akar = bool(post.get('cek_akar'))
        cek_hama = bool(post.get('cek_hama'))

        # Create tahapan log entry
        request.env['agf.tahapan'].create({
            'kargo_id': kargo.id,
            'tahap': tahap,
            'lokasi': lokasi,
            'catatan': catatan,
            'status_baru': status_baru,
            'cek_daun': cek_daun,
            'cek_akar': cek_akar,
            'cek_hama': cek_hama,
        })

        # Update kargo status
        if status_baru:
            kargo.write({'status': status_baru})

        return request.redirect(f'/agf/warehouse/pesanan/{kargo_id}')
