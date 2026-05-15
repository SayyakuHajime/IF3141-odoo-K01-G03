import base64
from odoo import http
from odoo.http import request
from odoo.addons.agf_cargo.models.agf_tahapan import PREP_SUBSTEPS, WAREHOUSE_ALLOWED_STATUS

def _kargo_search_domain(search_text):
    """
    Multi-word AND search across all key kargo fields.

    Each whitespace-separated token must match at least one of the four
    searchable fields (OR within token, AND across tokens).

    Example: "John 0042" →
        (nama_penitip ilike 'John' OR nomor_penitip ilike 'John' OR ...)
        AND
        (nama_penitip ilike '0042' OR nomor_penitip ilike '0042' OR ...)
    """
    domain = []
    tokens = [t for t in search_text.strip().split() if t]
    for token in tokens:
        domain += ['|', '|', '|',
            ('nomor_penitip',  'ilike', token),
            ('nomor_penerima', 'ilike', token),
            ('nama_penitip',   'ilike', token),
            ('nama_penerima',  'ilike', token),
        ]
    return domain


class WarehousePortal(http.Controller):

    @http.route('/agf/warehouse', type='http', auth='public', website=True)
    def landing(self, **kwargs):
        user = request.env.user
        if user and not user._is_public():
            if (user._is_superuser() or
                    user.has_group('agf_cargo.group_agf_gudang') or
                    user.has_group('agf_cargo.group_agf_admin')):
                return request.redirect('/agf/warehouse/pesanan')
        return request.render('agf_cargo.warehouse_landing', {})

    @http.route('/agf/warehouse/pesanan', type='http', auth='user', website=True)
    def daftar_pesanan(self, tab='pesanan', status=None, search=None, **kwargs):
        batch = request.env['agf.batch'].sudo().search([('status', '=', 'aktif')], limit=1)

        domain = []
        if batch:
            domain.append(('batch_id', '=', batch.id))
        if status:
            domain.append(('status', '=', status))
        if search and search.strip():
            domain += _kargo_search_domain(search)

        kargo_list = request.env['agf.kargo'].sudo().search(domain, order='id desc')

        # Pass parsed tokens to template for visual feedback
        search_tokens = [t for t in (search or '').strip().split() if t]

        return request.render('agf_cargo.warehouse_daftar_pesanan', {
            'batch': batch,
            'kargo_list': kargo_list,
            'active_tab': tab,
            'current_status': status,
            'search': search,
            'search_tokens': search_tokens,
        })

    # Scan QR tab is just a tab on /pesanan — redirect for backwards compat
    @http.route('/agf/warehouse/scan', type='http', auth='user', website=True)
    def scan_redirect(self, **kwargs):
        return request.redirect('/agf/warehouse/pesanan?tab=scan')

    @http.route('/agf/warehouse/scan/result', type='json', auth='user')
    def scan_result(self, tag_id, **kwargs):
        tag = request.env['agf.qr.tag'].sudo().search(
            [('tag_id', '=', tag_id)], limit=1
        )
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

    @http.route('/agf/warehouse/pesanan/<int:kargo_id>', type='http', auth='user', website=True)
    def detail_pesanan(self, kargo_id, **kwargs):
        kargo = request.env['agf.kargo'].sudo().browse(kargo_id)
        if not kargo.exists():
            return request.not_found()
        return request.render('agf_cargo.warehouse_detail_pesanan', {'kargo': kargo})

    @http.route('/agf/warehouse/update/<int:kargo_id>', type='http', auth='user', website=True)
    def update_status(self, kargo_id, **kwargs):
        kargo = request.env['agf.kargo'].sudo().browse(kargo_id)
        if not kargo.exists():
            return request.not_found()
        return request.render('agf_cargo.warehouse_update_status', {
            'kargo': kargo,
            'prep_substeps': PREP_SUBSTEPS,
            'warehouse_allowed_status': WAREHOUSE_ALLOWED_STATUS,
            'status_choices': [
                s for s in request.env['agf.kargo']._fields['status'].selection
                if s[0] in WAREHOUSE_ALLOWED_STATUS
            ],
            'in_prep_phase': kargo.status == '05_gudang_asal',
        })

    @http.route(
        '/agf/warehouse/update/<int:kargo_id>/submit',
        type='http', auth='user', methods=['POST'], website=True,
    )
    def update_status_submit(self, kargo_id, **post):
        kargo = request.env['agf.kargo'].browse(kargo_id)
        if not kargo.exists():
            return request.not_found()

        tahap       = post.get('tahap')
        lokasi      = post.get('lokasi', '')
        catatan     = post.get('catatan', '')
        status_baru = post.get('status_baru') or None
        prep_substep = post.get('prep_substep') or None
        cek_daun    = bool(post.get('cek_daun'))
        cek_akar    = bool(post.get('cek_akar'))
        cek_hama    = bool(post.get('cek_hama'))

        # Guard: warehouse hanya boleh set status dalam WAREHOUSE_ALLOWED_STATUS
        if status_baru and status_baru not in WAREHOUSE_ALLOWED_STATUS:
            status_baru = None

        tahapan_vals = {
            'kargo_id':    kargo.id,
            'tahap':       tahap,
            'lokasi':      lokasi,
            'catatan':     catatan,
            'cek_daun':    cek_daun,
            'cek_akar':    cek_akar,
            'cek_hama':    cek_hama,
            'petugas_id':  request.env.user.id,
            'is_internal': False,
        }
        if prep_substep:
            tahapan_vals['prep_substep'] = prep_substep

        tahapan = request.env['agf.tahapan'].create(tahapan_vals)

        # Handle up to 4 photo uploads
        foto_ids = []
        for slot in ['foto_1', 'foto_2', 'foto_3', 'foto_4']:
            file = request.httprequest.files.get(slot)
            if file and file.filename:
                data = base64.b64encode(file.read()).decode()
                att = request.env['ir.attachment'].sudo().create({
                    'name':      file.filename,
                    'datas':     data,
                    'res_model': 'agf.tahapan',
                    'res_id':    tahapan.id,
                    'mimetype':  file.content_type or 'image/jpeg',
                })
                foto_ids.append(att.id)
        if foto_ids:
            tahapan.foto_ids = [(6, 0, foto_ids)]

        # Update status_persiapan semua tanaman dalam pesanan ini
        if prep_substep and kargo.tanaman_ids:
            kargo.tanaman_ids.write({'status_persiapan': prep_substep})

        # Update status kargo, hanya kalau dalam scope warehouse
        if status_baru and status_baru != kargo.status:
            kargo.write({'status': status_baru})

        return request.redirect(f'/agf/warehouse/pesanan/{kargo_id}')