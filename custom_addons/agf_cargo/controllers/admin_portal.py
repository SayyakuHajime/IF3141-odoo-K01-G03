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

    @http.route('/agf/admin/pesanan/baru', type='http', auth='user', website=True)
    def form_pesanan_baru(self, **kwargs):
        batch_aktif = request.env['agf.batch'].search([('status', '=', 'aktif')], limit=1)
        if not batch_aktif:
            return request.redirect('/agf/admin/batch-aktif')
        return request.render('agf_cargo.admin_form_pesanan_baru', {
            'batch': batch_aktif,
            'user_initials': self._get_user_initials(),
        })

    @http.route('/agf/admin/pesanan/baru/submit', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def form_pesanan_baru_submit(self, **post):
        import logging
        _logger = logging.getLogger(__name__)
        
        batch_aktif = request.env['agf.batch'].search([('status', '=', 'aktif')], limit=1)
        if not batch_aktif:
            return request.redirect('/agf/admin/batch-aktif')

        errors = []
        if not post.get('nama_penitip'):
            errors.append('Nama pengirim wajib diisi.')
        if not post.get('hp_penitip'):
            errors.append('No. HP pengirim wajib diisi.')
        if not post.get('email_penitip'):
            errors.append('Email pengirim wajib diisi.')
        if not post.get('alamat_penitip'):
            errors.append('Alamat pengirim wajib diisi.')
        if not post.get('nama_penerima'):
            errors.append('Nama penerima wajib diisi.')
        if not post.get('alamat_penerima'):
            errors.append('Alamat penerima wajib diisi.')

        # Parse tanaman
        tanaman_list = []
        idx = 0
        while post.get(f'tanaman_nama_{idx}'):
            nama = post.get(f'tanaman_nama_{idx}', '').strip()
            jumlah_raw = post.get(f'tanaman_jumlah_{idx}', '1')
            ukuran = post.get(f'tanaman_ukuran_{idx}', 'sedang')
            kondisi = post.get(f'tanaman_kondisi_{idx}', 'belum_dicek')
            if nama:
                try:
                    jumlah = int(jumlah_raw)
                except ValueError:
                    jumlah = 1
                tanaman_list.append({
                    'nama_tanaman': nama,
                    'jumlah': jumlah,
                    'ukuran': ukuran,
                    'kondisi': kondisi,
                })
            idx += 1

        if not tanaman_list:
            errors.append('Minimal satu tanaman harus diisi.')

        if errors:
            return request.render('agf_cargo.admin_form_pesanan_baru', {
                'batch': batch_aktif,
                'errors': errors,
                'post': post,
                'user_initials': self._get_user_initials(),
            })

        try:
            kargo = request.env['agf.kargo'].create({
                'nama_penitip': post.get('nama_penitip'),
                'hp_penitip': post.get('hp_penitip'),
                'email_penitip': post.get('email_penitip'),
                'alamat_penitip': post.get('alamat_penitip'),
                'nama_penerima': post.get('nama_penerima'),
                'hp_penerima': post.get('hp_penerima', ''),
                'email_penerima': post.get('email_penerima', ''),
                'alamat_penerima': post.get('alamat_penerima'),
                'negara_tujuan': post.get('negara_tujuan', ''),
                'layanan_lokal': post.get('layanan_lokal', 'reguler'),
                'additional_packaging': post.get('additional_packaging', 'none'),
                'winter_packaging': post.get('winter_packaging', 'none'),
                'catatan': post.get('catatan', ''),
                'batch_id': batch_aktif.id,
                'status': 'hold',
            })

            # Create tanaman items
            for t in tanaman_list:
                t['kargo_id'] = kargo.id
                request.env['agf.tanaman.item'].create(t)

            # Handle bukti transaksi upload
            bukti = request.httprequest.files.get('bukti_transaksi')
            if bukti and bukti.filename:
                import base64
                kargo.write({
                    'bukti_transaksi': base64.b64encode(bukti.read()),
                    'bukti_transaksi_nama': bukti.filename,
                })

            return request.redirect(f'/agf/admin/pesanan/{kargo.id}')
        except Exception as e:
            _logger.error(f"CREATE PESANAN ERROR: {e}")
            return request.render('agf_cargo.admin_form_pesanan_baru', {
                'batch': batch_aktif,
                'errors': [str(e)],
                'post': post,
                'user_initials': self._get_user_initials(),
            })

    @http.route('/agf/admin/pesanan/<int:kargo_id>', type='http', auth='user', website=True)
    def detail_pesanan(self, kargo_id, **kwargs):
        kargo = request.env['agf.kargo'].browse(kargo_id)
        if not kargo.exists():
            return request.not_found()
        return request.render('agf_cargo.admin_detail_pesanan_aktif', {
            'kargo': kargo,
            'user_initials': self._get_user_initials(),
        })

    @http.route('/agf/admin/pesanan/<int:kargo_id>/edit', type='http', auth='user', website=True)
    def form_pesanan_edit(self, kargo_id, **kwargs):
        kargo = request.env['agf.kargo'].browse(kargo_id)
        if not kargo.exists():
            return request.not_found()
        return request.render('agf_cargo.admin_form_pesanan_edit', {
            'kargo': kargo,
            'user_initials': self._get_user_initials(),
        })

    @http.route('/agf/admin/pesanan/<int:kargo_id>/edit/submit', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def form_pesanan_edit_submit(self, kargo_id, **post):
        import logging
        _logger = logging.getLogger(__name__)
        kargo = request.env['agf.kargo'].browse(kargo_id)
        if not kargo.exists():
            return request.not_found()

        try:
            # Simpan status lama sebelum write
            status_lama = kargo.status
            status_baru = post.get('status', kargo.status)

            kargo.write({
                'nama_penitip': post.get('nama_penitip', kargo.nama_penitip),
                'hp_penitip': post.get('hp_penitip', kargo.hp_penitip),
                'email_penitip': post.get('email_penitip', kargo.email_penitip),
                'alamat_penitip': post.get('alamat_penitip', kargo.alamat_penitip),
                'nama_penerima': post.get('nama_penerima', kargo.nama_penerima),
                'hp_penerima': post.get('hp_penerima', kargo.hp_penerima),
                'email_penerima': post.get('email_penerima', kargo.email_penerima),
                'alamat_penerima': post.get('alamat_penerima', kargo.alamat_penerima),
                'negara_tujuan': post.get('negara_tujuan', kargo.negara_tujuan),
                'layanan_lokal': post.get('layanan_lokal', kargo.layanan_lokal),
                'additional_packaging': post.get('additional_packaging', kargo.additional_packaging),
                'winter_packaging': post.get('winter_packaging', kargo.winter_packaging),
                'catatan': post.get('catatan', ''),
                'status': status_baru,
            })

            # Update tanaman
            kargo.tanaman_ids.unlink()
            idx = 0
            while post.get(f'tanaman_nama_{idx}'):
                nama = post.get(f'tanaman_nama_{idx}', '').strip()
                if nama:
                    try:
                        jumlah = int(post.get(f'tanaman_jumlah_{idx}', '1'))
                    except ValueError:
                        jumlah = 1
                    request.env['agf.tanaman.item'].create({
                        'kargo_id': kargo.id,
                        'nama_tanaman': nama,
                        'jumlah': jumlah,
                        'ukuran': post.get(f'tanaman_ukuran_{idx}', 'sedang'),
                        'kondisi': post.get(f'tanaman_kondisi_{idx}', 'belum_dicek'),
                    })
                idx += 1

            # Handle bukti transaksi
            bukti = request.httprequest.files.get('bukti_transaksi')
            if bukti and bukti.filename:
                import base64
                kargo.write({
                    'bukti_transaksi': base64.b64encode(bukti.read()),
                    'bukti_transaksi_nama': bukti.filename,
                })

            # Catat log
            status_labels = {
                'hold': 'Hold', 'arrival': 'Arrival', 'processing': 'Processing',
                'shipped': 'Shipped', 'done': 'Done',
            }
            if status_baru != status_lama:
                request.env['agf.kargo.log'].create({
                    'kargo_id': kargo.id,
                    'jenis': 'status',
                    'deskripsi': f"Status diubah dari {status_labels.get(status_lama, status_lama)} menjadi {status_labels.get(status_baru, status_baru)}",
                })
            else:
                request.env['agf.kargo.log'].create({
                    'kargo_id': kargo.id,
                    'jenis': 'detail',
                    'deskripsi': 'Detail pesanan diperbarui',
                })

            return request.redirect(f'/agf/admin/pesanan/{kargo_id}')

        except Exception as e:
            _logger.error(f"EDIT PESANAN ERROR: {e}")
            return request.render('agf_cargo.admin_form_pesanan_edit', {
                'kargo': kargo,
                'errors': [str(e)],
                'user_initials': self._get_user_initials(),
            })

    @http.route('/agf/admin/pesanan/<int:kargo_id>/hapus', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def hapus_pesanan(self, kargo_id, **kwargs):
        kargo = request.env['agf.kargo'].browse(kargo_id)
        if not kargo.exists():
            return request.not_found()
        kargo.unlink()
        return request.redirect('/agf/admin/batch-aktif')

    @http.route('/agf/admin/pesanan/<int:kargo_id>/bukti', type='http', auth='user', website=True)
    def lihat_bukti(self, kargo_id, **kwargs):
        kargo = request.env['agf.kargo'].browse(kargo_id)
        if not kargo.exists() or not kargo.bukti_transaksi:
            return request.not_found()
        import base64
        data = base64.b64decode(kargo.bukti_transaksi)
        filename = kargo.bukti_transaksi_nama or 'bukti_transaksi'
        mime = 'application/pdf' if filename.endswith('.pdf') else 'image/jpeg'
        return request.make_response(data, headers=[
            ('Content-Type', mime),
            ('Content-Disposition', f'inline; filename="{filename}"'),
        ])

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