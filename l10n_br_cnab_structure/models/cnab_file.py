# Copyright 2022 Engenere
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from email.policy import default
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CNABFile(models.Model):

    _name = "l10n_br_cnab.file"
    _description = (
        "An structure with header, body and trailer that make up the CNAB file."
    )

    name = fields.Char(readonly=True, states={"draft": [("readonly", "=", False)]})

    cnab_format = fields.Selection(
        selection=[("240", "240"), ("400", "400")],
        required=True,
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )

    batch_ids = fields.One2many(
        comodel_name="l10n_br_cnab.batch",
        inverse_name="cnab_file_id",
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )

    line_ids = fields.One2many(
        comodel_name="l10n_br_cnab.line",
        inverse_name="cnab_file_id",
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )

    state = fields.Selection(
        selection=[("draft", "Draft"), ("review", "Review"), ("approved", "Approved")],
        readonly=True,
        default="draft",
    )

    def unlink(self):
        lines = self.filtered(lambda l: l.state != "draft")
        if lines:
            raise UserError(_("You cannot delete an CNAB File which is not draft !"))
        return super(CNABFile, self).unlink()

    def action_review(self):
        self.check_file()
        self.line_ids.field_ids.write({"state": "review"})
        self.line_ids.batch_id.write({"state": "review"})
        self.line_ids.write({"state": "review"})
        self.write({"state": "review"})

    def action_approve(self):
        self.line_ids.field_ids.write({"state": "approved"})
        self.line_ids.batch_id.write({"state": "approved"})
        self.line_ids.write({"state": "approved"})
        self.write({"state": "approved"})

    def action_draft(self):
        self.line_ids.field_ids.write({"state": "draft"})
        self.line_ids.batch_id.write({"state": "draft"})
        self.line_ids.write({"state": "draft"})
        self.write({"state": "draft"})

    def check_file(self):

        for l in self.line_ids:
            l.check_line()

        for l in self.batch_ids:
            l.check_batch()
