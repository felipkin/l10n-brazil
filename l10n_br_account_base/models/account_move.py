# Copyright (C) 2022-Today - Engenere (<https://engenere.one>).
# @author Antônio S. Pereira Neto <neto@engenere.one>
# @author Felipe Motter Pereira <felipe@engenere.one>

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_payment_way_id = fields.Many2one(
        comodel_name="account.payment.way",
        string="Payment Way",
    )
