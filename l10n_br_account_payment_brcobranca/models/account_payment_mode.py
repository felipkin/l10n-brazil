# Copyright (C) 2012-Today - KMEE (<http://kmee.com.br>).
#  @author Luis Felipe Miléo - mileo@kmee.com.br
#  @author Renato Lima - renato.lima@akretion.com.br
# Copyright (C) 2021-Today - Akretion (<http://www.akretion.com>).
# @author Magno Costa <magno.costa@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentMode(models.Model):
    """
    Override Account Payment Mode
    """

    _inherit = "account.payment.mode"

    cnab_processor = fields.Selection(
        selection_add=[("brcobranca", "BRCobrança")],
    )
