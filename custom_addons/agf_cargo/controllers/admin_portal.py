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
    
    @http.route('/agf/admin/batch-aktif', type='http', auth='user', website=True)
    def batch_aktif_page(self, status=None, **kwargs):
        batch = request.env['agf.batch'].search([('status', '=', 'aktif')], limit=1)
        
        if batch:
            kargo_list = batch.kargo_ids
            if status:
                kargo_list = kargo_list.filtered(lambda k: k.status == status)
            status_counts = {
                s: len(batch.kargo_ids.filtered(lambda k: k.status == s))
                for s in ['hold', 'arrival', 'processing', 'shipped', 'done']
            }
        else:
            kargo_list = []
            status_counts = {}

        return request.render('agf_cargo.admin_batch_aktif_page', {
            'batch': batch,
            'kargo_list': kargo_list,
            'status_counts': status_counts,
            'current_status': status,
            'user_initials': self._get_user_initials(),
        })

    @http.route('/agf/admin/riwayat-batch', type='http', auth='user', website=True)
    def riwayat_batch(self, **kwargs):
        batches = request.env['agf.batch'].search([], order='tanggal_mulai desc')
        return request.render('agf_cargo.admin_riwayat_batch', {
            'batches': batches,
            'user_initials': self._get_user_initials(),
        })
    

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

    @http.route('/agf/admin/batch/baru', type='http', auth='user', website=True)
    def form_batch_baru(self, **kwargs):
        return request.render('agf_cargo.admin_form_batch_baru', {
            'user_initials': self._get_user_initials(),
        })

    @http.route('/agf/admin/batch/baru/submit', type='http', auth='user', methods=['POST'], website=True)
    def form_batch_baru_submit(self, **post):
        from datetime import date

        tanggal_mulai_str = post.get('tanggal_mulai', '')
        tanggal_keberangkatan_str = post.get('tanggal_keberangkatan', '')
        tanggal_selesai_str = post.get('tanggal_selesai', '')

        errors = []

        # Parse tanggal
        try:
            from datetime import datetime
            tanggal_mulai = datetime.strptime(tanggal_mulai_str, '%Y-%m-%d').date() if tanggal_mulai_str else None
            tanggal_keberangkatan = datetime.strptime(tanggal_keberangkatan_str, '%Y-%m-%d').date() if tanggal_keberangkatan_str else None
            tanggal_selesai = datetime.strptime(tanggal_selesai_str, '%Y-%m-%d').date() if tanggal_selesai_str else None
        except ValueError:
            errors.append('Format tanggal tidak valid.')
            tanggal_mulai = tanggal_keberangkatan = tanggal_selesai = None

        today = date.today()

        if not tanggal_mulai:
            errors.append('Tanggal buka pendaftaran wajib diisi.')
        if not tanggal_keberangkatan:
            errors.append('Tanggal keberangkatan wajib diisi.')

        if tanggal_mulai and tanggal_keberangkatan:
            # Tanggal keberangkatan harus setelah tanggal mulai
            if tanggal_keberangkatan <= tanggal_mulai:
                errors.append('Tanggal keberangkatan harus setelah tanggal buka pendaftaran.')

            # Tanggal keberangkatan tidak boleh di masa lalu
            if tanggal_keberangkatan < today:
                errors.append('Tanggal keberangkatan tidak boleh di masa lalu.')

            # Tanggal mulai tidak boleh setelah hari ini
            # (tidak masuk akal buka pendaftaran di masa depan saat batch dibuat)
            # if tanggal_mulai > today:
            #     errors.append('Tanggal buka pendaftaran tidak boleh di masa depan.')

            # Kalau ada tanggal selesai, harus antara mulai dan keberangkatan
            if tanggal_selesai:
                if tanggal_selesai < tanggal_mulai:
                    errors.append('Tanggal tutup pendaftaran tidak boleh sebelum tanggal buka.')
                if tanggal_selesai > tanggal_keberangkatan:
                    errors.append('Tanggal tutup pendaftaran tidak boleh setelah tanggal keberangkatan.')

        if errors:
            return request.render('agf_cargo.admin_form_batch_baru', {
                'errors': errors,
                'user_initials': self._get_user_initials(),
                'post': post,
            })

        vals = {
            'tanggal_mulai': tanggal_mulai_str,
            'tanggal_keberangkatan': tanggal_keberangkatan_str,
            'tanggal_selesai': tanggal_selesai_str or False,
            'negara_tujuan': post.get('negara_tujuan', 'United States'),
            'kapasitas_maks': int(post.get('kapasitas_maks', 0) or 0),
            'catatan': post.get('catatan', ''),
            'status': 'aktif',
        }

        try:
            request.env['agf.batch'].create(vals)
            return request.redirect('/agf/admin/batch-aktif')
        except Exception as e:
            return request.render('agf_cargo.admin_form_batch_baru', {
                'errors': [str(e)],
                'user_initials': self._get_user_initials(),
                'post': post,
            })

    @http.route('/agf/admin/batch/<int:batch_id>/edit', type='http', auth='user', website=True)
    def form_batch_edit(self, batch_id, **kwargs):
        batch = request.env['agf.batch'].browse(batch_id)
        if not batch.exists():
            return request.not_found()
        return request.render('agf_cargo.admin_form_batch_edit', {
            'batch': batch,
            'user_initials': self._get_user_initials(),
        })

    @http.route('/agf/admin/batch/<int:batch_id>/edit/submit', type='http', auth='user', methods=['POST'], website=True)
    def form_batch_edit_submit(self, batch_id, **post):
        batch = request.env['agf.batch'].browse(batch_id)
        if not batch.exists():
            return request.not_found()
        
        try:
            batch.write({
                'tanggal_keberangkatan': post.get('tanggal_keberangkatan'),
                'tanggal_selesai': post.get('tanggal_selesai') or False,
                'negara_tujuan': post.get('negara_tujuan', 'United States'),
                'kapasitas_maks': int(post.get('kapasitas_maks', 0) or 0),
                'catatan': post.get('catatan', ''),
                'status': post.get('status') or batch.status,
            })
            return request.redirect(f'/agf/admin/batch-aktif')
        except Exception as e:
            return request.render('agf_cargo.admin_form_batch_edit', {
                'batch': batch,
                'error': str(e),
                'user_initials': self._get_user_initials(),
            })
            
    @http.route('/agf/admin/batch/<int:batch_id>/cancel', type='http', auth='user', methods=['POST'], website=True)
    def batch_cancel(self, batch_id, **kwargs):
        batch = request.env['agf.batch'].browse(batch_id)
        if not batch.exists():
            return request.not_found()
        batch.write({'status': 'dibatalkan'})
        return request.redirect('/agf/admin/batch-aktif')
    
    @http.route('/agf/admin/debug-batch', type='http', auth='user', website=True)
    def debug_batch(self, **kwargs):
        all_batches = request.env['agf.batch'].search([])
        result = []
        for b in all_batches:
            result.append(f"ID:{b.id} Name:{b.name} Status:{b.status}")
        return request.make_response(
            '<br>'.join(result) if result else 'TIDAK ADA BATCH SAMA SEKALI',
            headers=[('Content-Type', 'text/html')]
        )