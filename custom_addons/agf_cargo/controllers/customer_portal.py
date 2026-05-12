from odoo import http
from odoo.http import request
import base64

class CustomerPortal(http.Controller):

    @http.route(
        '/agf/customer', 
        type='http', auth='public', 
        website=True
    )
    def landing(self, **kwargs):
        # Public stats for landing page
        total_pesanan = request.env['agf.kargo'].sudo().search_count([])
        total_batch = request.env['agf.batch'].sudo().search_count([])
        return request.render('agf_cargo.customer_landing', {
            'total_pesanan': total_pesanan,
            'total_batch': total_batch,
        })

    @http.route(
        '/agf/customer/tracking', 
        type='http', auth='public', 
        website=True
    )
    def tracking(self, nomor=None, **kwargs):
        kargo = None
        error = None
        if nomor:
            kargo = request.env['agf.kargo'].sudo().search([
                '|',
                ('nomor_penitip', '=', nomor.strip()),
                ('nomor_penerima', '=', nomor.strip()),
            ], limit=1)
            if not kargo:
                error = f'Nomor "{nomor}" tidak ditemukan.'
        return request.render('agf_cargo.customer_tracking', {
            'nomor': nomor,
            'kargo': kargo,
            'error': error,
        })

    @http.route(
        '/agf/customer/daftar', 
        type='http', auth='public', 
        website=True
    )
    def form_kargo(self, **kwargs):
        # Tampilkan info batch aktif (termasuk tanggal keberangkatan) di halaman form
        batch_aktif = request.env['agf.batch'].sudo().search([('status', '=', 'aktif')], limit=1)
        return request.render('agf_cargo.customer_form_kargo', {
            'batch_aktif': batch_aktif,
        })

    @http.route(
        '/agf/customer/daftar/submit',
        type='http', auth='public', methods=['POST'],
        website=True, csrf=True,
    )
    def form_kargo_submit(self, **post):
        batch_aktif = request.env['agf.batch'].sudo().search(
            [('status', '=', 'aktif')], limit=1
        )

        kargo = request.env['agf.kargo'].sudo().create({
            # Pengirim
            'nama_penitip':     post.get('nama_penitip', ''),
            'hp_penitip':       post.get('hp_penitip', ''),
            'email_penitip':    post.get('email_penitip', ''),
            'alamat_penitip':   post.get('alamat_penitip', ''),
            # Penerima
            'nama_penerima':    post.get('nama_penerima', ''),
            'hp_penerima':      post.get('hp_penerima', ''),
            'email_penerima':   post.get('email_penerima', ''),
            'alamat_penerima':  post.get('alamat_penerima', ''),
            'kota_tujuan':      post.get('kota_tujuan', ''),
            'negara_tujuan':    post.get('negara_tujuan', ''),
            # Pengiriman
            'layanan_lokal':        post.get('layanan_lokal', 'reguler'),
            'additional_packaging': post.get('additional_packaging', 'none'),
            'winter_packaging':     post.get('winter_packaging', 'none'),
            'catatan':              post.get('catatan', ''),
            # Batch aktif
            'batch_id': batch_aktif.id if batch_aktif else False,
        })

        # Proses daftar tanaman
        tanaman_count = int(post.get('tanaman_count', 0))
        for i in range(tanaman_count):
            nama = post.get(f'tanaman_nama_{i}', '').strip()
            if not nama:
                continue
            request.env['agf.tanaman.item'].sudo().create({
                'kargo_id':     kargo.id,
                'nama_tanaman': nama,
                'jumlah':       int(post.get(f'tanaman_jumlah_{i}', 1)),
                'ukuran':       post.get(f'tanaman_ukuran_{i}', 'sedang'),
            })

        # Initial tahapan log
        request.env['agf.tahapan'].sudo().create({
            'kargo_id': kargo.id,
            'tahap':    '01_registrasi',
            'catatan':  'Pendaftaran kargo berhasil.',
        })

        return request.render('agf_cargo.customer_form_kargo', {
            'success':        True,
            'nomor_penitip':  kargo.nomor_penitip,
            'nomor_penerima': kargo.nomor_penerima,
        })
    
    @http.route(
        '/agf/customer/upload_bukti/<int:kargo_id>',
        type='http', auth='public', methods=['POST'],
        website=True, csrf=True,
    )
    def upload_bukti(self, kargo_id, **post):
        kargo = request.env['agf.kargo'].sudo().browse(kargo_id)
        if not kargo.exists():
            return request.not_found()

        file = request.httprequest.files.get('bukti_file')
        nomor = post.get('nomor', '')

        if file and file.filename:
            data = base64.b64encode(file.read()).decode()
            att = request.env['ir.attachment'].sudo().create({
                'name': file.filename,
                'datas': data,
                'res_model': 'agf.kargo',
                'res_id': kargo.id,
                'mimetype': file.content_type or 'image/jpeg',
            })
            kargo.sudo().write({'bukti_pembayaran': att.id})

        return request.redirect(
            f'/agf/customer/tracking?nomor={nomor}'
        )

    @http.route(
        '/agf/customer/konfirmasi_jemput/<int:kargo_id>',
        type='http', auth='public', methods=['POST'],
        website=True, csrf=True,
    )
    def konfirmasi_jemput(self, kargo_id, **post):
        kargo = request.env['agf.kargo'].sudo().browse(kargo_id)
        if not kargo.exists():
            return request.not_found()

        nomor = post.get('nomor', '')
        kargo.sudo().write({'konfirmasi_penjemputan': True})

        return request.redirect(
            f'/agf/customer/tracking?nomor={nomor}'
        )
