from werkzeug.exceptions import HTTPException

from odoo import models
from odoo.http import request


def _raise_redirect(url):
    """Lempar HTTPException berisi redirect — ditangkap Odoo/werkzeug dispatcher."""
    response = request.redirect(url, 302)
    raise HTTPException(response=response)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _pre_dispatch(cls, rule, arguments):
        super()._pre_dispatch(rule, arguments)

        path = request.httprequest.path
        uid = request.env.uid  # None/False kalau anonymous

        # ── /agf/admin/** : hanya Admin AGF atau Manajer Operasional ──────────
        if path.startswith('/agf/admin'):
            if not uid:
                _raise_redirect('/web/login?redirect=' + path)
            user = request.env.user
            if user._is_superuser():
                return
            if not (user.has_group('agf_cargo.group_agf_admin') or
                    user.has_group('agf_cargo.group_agf_manajer')):
                _raise_redirect('/web/login')

        # ── /agf/warehouse/** (bukan landing) : hanya Gudang atau Admin ──────
        elif path.startswith('/agf/warehouse/'):
            if not uid:
                _raise_redirect('/web/login?redirect=' + path)
            user = request.env.user
            if user._is_superuser():
                return
            if not (user.has_group('agf_cargo.group_agf_gudang') or
                    user.has_group('agf_cargo.group_agf_admin')):
                _raise_redirect('/web/login')
