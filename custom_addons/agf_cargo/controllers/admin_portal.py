import json
from datetime import datetime, timedelta, date

from odoo import http
from odoo.http import request


class AdminPortal(http.Controller):

    def _base_ctx(self):
        """Context dasar yang dibutuhkan admin_layout (user, dll.)."""
        return {'user': request.env.user}

    @http.route('/agf/admin', type='http', auth='user', website=True)
    def redirect_dashboard(self, **kwargs):
        return request.redirect('/agf/admin/dashboard')

    @http.route('/agf/admin/dashboard', type='http', auth='user', website=True)
    def dashboard(self, **kwargs):
        env = request.env
        batch = env['agf.batch'].sudo().search([('status', '=', 'aktif')], limit=1)

        total_pesanan = (
            env['agf.kargo'].sudo().search_count([('batch_id', '=', batch.id)])
            if batch else 0
        )
        total_qr = env['agf.qr.tag'].sudo().search_count([])
        qr_aktif = env['agf.qr.tag'].sudo().search_count([('status', '=', 'aktif')])
        pesanan_selesai = (
            env['agf.kargo'].sudo().search_count([
                ('status', '=', 'done'), ('batch_id', '=', batch.id)
            ]) if batch else 0
        )

        statuses = ['hold', 'arrival', 'processing', 'shipped', 'done']
        pesanan_by_status = {
            s: env['agf.kargo'].sudo().search_count([('status', '=', s)])
            for s in statuses
        }

        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_kargo = env['agf.kargo'].sudo().search(
            [('create_date', '>=', seven_days_ago)],
            order='create_date desc',
            limit=5,
        )

        three_days_ago = datetime.now() - timedelta(days=3)
        alerts_hold_lama = env['agf.kargo'].sudo().search([
            ('status', '=', 'hold'),
            ('write_date', '<=', three_days_ago),
        ])
        alerts_qr_rusak = env['agf.qr.tag'].sudo().search([('status', '=', 'rusak')])

        recent_batches = env['agf.batch'].sudo().search(
            [], order='tanggal_keberangkatan desc', limit=5
        )

        # Bar chart: kargo per hari 7 hari terakhir (1 query)
        today = date.today()
        week_start = datetime.combine(today - timedelta(days=6), datetime.min.time())
        week_kargo = env['agf.kargo'].sudo().search([('create_date', '>=', week_start)])
        day_labels_id = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
        chart_labels = []
        chart_counts = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            count = sum(1 for k in week_kargo if k.create_date and k.create_date.date() == d)
            chart_labels.append(day_labels_id[d.weekday()])
            chart_counts.append(count)

        return request.render('agf_cargo.admin_dashboard', {
            **self._base_ctx(),
            'batch_aktif': batch,
            'total_pesanan': total_pesanan,
            'total_qr': total_qr,
            'qr_aktif': qr_aktif,
            'pesanan_selesai': pesanan_selesai,
            'pesanan_by_status': pesanan_by_status,
            'recent_kargo': recent_kargo,
            'alerts_hold_lama': alerts_hold_lama,
            'alerts_qr_rusak': alerts_qr_rusak,
            'recent_batches': recent_batches,
            'chart_labels_json': json.dumps(chart_labels),
            'chart_counts_json': json.dumps(chart_counts),
        })

    @http.route('/agf/admin/pesanan', type='http', auth='user', website=True)
    def batch_aktif(self, status=None, search=None, **kwargs):
        domain = []
        batch = request.env['agf.batch'].sudo().search([('status', '=', 'aktif')], limit=1)
        if batch:
            domain.append(('batch_id', '=', batch.id))
        if status:
            domain.append(('status', '=', status))
        if search:
            domain += ['|', ('nomor_penitip', 'ilike', search), ('nama_penitip', 'ilike', search)]
        kargo_list = request.env['agf.kargo'].sudo().search(domain)
        return request.render('agf_cargo.admin_batch_aktif', {
            **self._base_ctx(),
            'batch': batch,
            'kargo_list': kargo_list,
            'current_status': status,
            'search': search,
        })

    @http.route('/agf/admin/pesanan/baru', type='http', auth='user', website=True)
    def form_pesanan(self, **kwargs):
        batch_aktif = request.env['agf.batch'].sudo().search([('status', '=', 'aktif')], limit=1)
        return request.render('agf_cargo.admin_form_pesanan', {**self._base_ctx(), 'batch_aktif': batch_aktif})

    @http.route('/agf/admin/pesanan/<int:kargo_id>', type='http', auth='user', website=True)
    def detail_pesanan(self, kargo_id, **kwargs):
        kargo = request.env['agf.kargo'].sudo().browse(kargo_id)
        if not kargo.exists():
            return request.not_found()
        if kargo.batch_id and kargo.batch_id.status == 'aktif':
            return request.render('agf_cargo.admin_detail_pesanan_aktif', {
                **self._base_ctx(),
                'kargo': kargo,
                'is_active': True,
            })
        return request.render('agf_cargo.admin_detail_pesanan_inactive', {
            **self._base_ctx(),
            'kargo': kargo,
            'is_active': False,
        })

    @http.route('/agf/admin/qr', type='http', auth='user', website=True)
    def qr_management(self, **kwargs):
        tags = request.env['agf.qr.tag'].sudo().search([])
        stats = {
            'total': len(tags),
            'aktif': len(tags.filtered(lambda t: t.status == 'aktif')),
            'idle': len(tags.filtered(lambda t: t.status == 'idle')),
            'rusak': len(tags.filtered(lambda t: t.status == 'rusak')),
        }
        return request.render('agf_cargo.admin_qr_code', {**self._base_ctx(), 'tags': tags, 'stats': stats})

    @http.route('/agf/admin/batch', type='http', auth='user', website=True)
    def riwayat_batch(self, **kwargs):
        env = request.env
        batches = env['agf.batch'].sudo().search([], order='tanggal_keberangkatan desc')
        active_batch = env['agf.batch'].sudo().search([('status', '=', 'aktif')], limit=1)
        total_pesanan_all = sum(batches.mapped('total_pesanan'))
        total_tanaman_all = sum(batches.mapped('total_tanaman'))
        return request.render('agf_cargo.admin_riwayat_batch', {
            **self._base_ctx(),
            'batches': batches,
            'has_active_batch': bool(active_batch),
            'active_batch': active_batch,
            'total_batch': len(batches),
            'total_pesanan_all': total_pesanan_all,
            'total_tanaman_all': total_tanaman_all,
        })

    @http.route('/agf/admin/batch/baru', type='json', auth='user', methods=['POST'], csrf=False)
    def admin_buat_batch(self, tanggal_keberangkatan=None, catatan='', **kwargs):
        env = request.env
        existing = env['agf.batch'].sudo().search([('status', '=', 'aktif')], limit=1)
        if existing:
            return {
                'success': False,
                'error': f'Sudah ada batch aktif: {existing.name}. Tutup batch aktif dulu.',
            }
        if not tanggal_keberangkatan:
            return {'success': False, 'error': 'Tanggal keberangkatan wajib diisi.'}
        batch = env['agf.batch'].sudo().create({
            'tanggal_keberangkatan': tanggal_keberangkatan,
            'tanggal_mulai': date.today().isoformat(),
            'catatan': catatan or '',
            'status': 'aktif',
        })
        return {'success': True, 'batch_id': batch.id, 'batch_name': batch.name}

    @http.route('/agf/admin/batch/<int:batch_id>', type='http', auth='user', website=True)
    def detail_batch(self, batch_id, **kwargs):
        batch = request.env['agf.batch'].sudo().browse(batch_id)
        if not batch.exists():
            return request.not_found()
        return request.render('agf_cargo.admin_detail_batch', {**self._base_ctx(), 'batch': batch})

    @http.route('/agf/admin/pengguna', type='http', auth='user', website=True)
    def pengguna(self, **kwargs):
        env = request.env
        try:
            group_admin = env.ref('agf_cargo.group_agf_admin')
            group_manajer = env.ref('agf_cargo.group_agf_manajer')
            group_gudang = env.ref('agf_cargo.group_agf_gudang')
        except Exception:
            group_admin = group_manajer = group_gudang = env['res.groups'].browse([])

        agf_group_ids = (group_admin | group_manajer | group_gudang).ids
        users = env['res.users'].sudo().search([
            ('groups_id', 'in', agf_group_ids),
            ('active', '=', True),
        ])
        all_users = env['res.users'].sudo().search([
            ('groups_id', 'not in', agf_group_ids),
            ('active', '=', True),
            ('share', '=', False),
        ])
        return request.render('agf_cargo.admin_pengguna', {
            **self._base_ctx(),
            'users': users,
            'all_users': all_users,
            'group_admin': group_admin,
            'group_manajer': group_manajer,
            'group_gudang': group_gudang,
            'group_admin_id': group_admin.id if group_admin else 0,
            'group_manajer_id': group_manajer.id if group_manajer else 0,
            'group_gudang_id': group_gudang.id if group_gudang else 0,
        })

    @http.route('/agf/admin/pengguna/tambah', type='json', auth='user', methods=['POST'], csrf=False)
    def admin_tambah_user(self, user_id=None, group_xml_id=None, **kwargs):
        if not user_id or not group_xml_id:
            return {'success': False, 'error': 'Parameter tidak lengkap.'}
        env = request.env
        user = env['res.users'].sudo().browse(int(user_id))
        group = env.ref(group_xml_id)
        user.write({'groups_id': [(4, group.id)]})
        return {'success': True}

    @http.route('/agf/admin/pengguna/<int:user_id>/edit', type='json', auth='user', methods=['POST'], csrf=False)
    def admin_edit_role(self, user_id, group_xml_id=None, **kwargs):
        if not group_xml_id:
            return {'success': False, 'error': 'Parameter tidak lengkap.'}
        env = request.env
        user = env['res.users'].sudo().browse(user_id)
        agf_groups = [
            env.ref('agf_cargo.group_agf_admin'),
            env.ref('agf_cargo.group_agf_manajer'),
            env.ref('agf_cargo.group_agf_gudang'),
        ]
        new_group = env.ref(group_xml_id)
        user.write({'groups_id':
            [(3, g.id) for g in agf_groups] +
            [(4, new_group.id)]
        })
        return {'success': True}
