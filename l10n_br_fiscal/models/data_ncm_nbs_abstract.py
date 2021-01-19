# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging
from datetime import timedelta
from lxml import etree
from erpbrasil.base import misc

from odoo import _, api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.osv import orm

from .ibpt.taxes import DeOlhoNoImposto

_logger = logging.getLogger(__name__)

OBJECT_NAMES = {
    'l10n_br_fiscal.ncm': 'NCM',
    'l10n_br_fiscal.nbs': 'NBS'
}

OBJECT_FIELDS = {
    'l10n_br_fiscal.ncm': 'ncm_id',
    'l10n_br_fiscal.nbs': 'nbs_id'
}


class DataNcmNbsAbstract(models.AbstractModel):
    _name = 'l10n_br_fiscal.data.ncm.nbs.abstract'
    _inherit = 'l10n_br_fiscal.data.product.abstract'
    _description = 'Fiscal NCM and NBS Data Abstract'

    tax_estimate_ids = fields.One2many(
        comodel_name='l10n_br_fiscal.tax.estimate',
        string='Estimate Taxes',
        readonly=True)

    estimate_tax_national = fields.Float(
        string='Estimate Tax Nacional Percent',
        store=True,
        readonly=True,
        digits=dp.get_precision('Fiscal Tax Percent'),
        compute='_compute_amount')

    estimate_tax_imported = fields.Float(
        string='Estimate Tax Imported Percent',
        store=True,
        readonly=True,
        digits=dp.get_precision('Fiscal Tax Percent'),
        compute='_compute_amount')

    @api.depends('tax_estimate_ids')
    def _compute_amount(self):
        for record in self:
            last_estimated = record.env['l10n_br_fiscal.tax.estimate'].search([
                '|', ('ncm_id', '=', record.id), ('nbs_id', '=', record.id),
                ('company_id', '=', record.env.user.company_id.id)],
                order='create_date DESC',
                limit=1)

            if last_estimated:
                record.estimate_tax_imported = (
                    last_estimated.federal_taxes_import
                    + last_estimated.state_taxes
                    + last_estimated.municipal_taxes)

                record.estimate_tax_national = (
                    last_estimated.federal_taxes_national
                    + last_estimated.state_taxes
                    + last_estimated.municipal_taxes)

    def _get_ibpt(self, config, code_unmasked):
        return False

    @api.multi
    def action_ibpt_inquiry(self):
        if not self.env.user.company_id.ibpt_api:
            return False

        object_name = OBJECT_NAMES.get(self._name)
        object_field = OBJECT_FIELDS.get(self._name)

        for record in self:
            try:
                company = self.env.user.company_id

                config = DeOlhoNoImposto(
                    company.ibpt_token,
                    misc.punctuation_rm(company.cnpj_cpf),
                    company.state_id.code)

                result = self._get_ibpt(config, record.code_unmasked)

                values = {
                    object_field: record.id,
                    'key': result.chave,
                    'origin': result.fonte,
                    'state_id': company.state_id.id,
                    'state_taxes': result.estadual,
                    'federal_taxes_national': result.nacional,
                    'federal_taxes_import': result.importado,
                }

                self.env['l10n_br_fiscal.tax.estimate'].create(values)

                record.message_post(
                    body=_("{} Tax Estimate Updated").format(object_name),
                    subject=_("{} Tax Estimate Updated").format(object_name))

            except Exception as e:
                _logger.warning(
                    _("{0} Tax Estimate Failure: {1}").format(object_name, e))
                record.message_post(
                    body=str(e),
                    subject=_("{} Tax Estimate Failure").format(object_name))
                continue

    @api.model
    def _scheduled_update(self):

        object_name = OBJECT_NAMES.get(self._name)

        _logger.info(
            _("Scheduled {} estimate taxes update...").format(object_name))

        config_date = self.env.user.company_id.ibpt_update_days
        today = fields.date.today()
        data_max = today - timedelta(days=config_date)

        all_records = self.env[self._name].search([])

        not_estimated = all_records.filtered(
            lambda r: r.product_tmpl_qty > 0 and not r.tax_estimate_ids)

        query = """
            WITH {0}_max_date AS (
               SELECT
                   {0}_id,
                   max(create_date)
               FROM
                   l10n_br_fiscal_tax_estimate
               GROUP BY {0}_id)
               SELECT {0}_id
               FROM {0}_max_date
            WHERE max < %(create_date)s
            """.format(object_name.lower())

        query_params = {'create_date': data_max.strftime('%Y-%m-%d')}

        self.env.cr.execute(self.env.cr.mogrify(query, query_params))
        past_estimated = self.env.cr.fetchall()

        ids = [estimate[0] for estimate in past_estimated]

        record_past_estimated = self.env[self._name].browse(ids)

        for record in not_estimated + record_past_estimated:
            try:
                record.action_ibpt_inquiry()
            except Exception:
                continue

        _logger.info(
            _("Scheduled {} estimate taxes update complete.").format(
                object_name))

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        res = super(DataNcmNbsAbstract, self).fields_view_get(
            view_id, view_type, toolbar, submenu)

        if view_type == 'form':
            xml = etree.XML(res['arch'])
            xml_button = xml.xpath("//button[@name='action_ibpt_inquiry']")
            if xml_button and not self.env.user.company_id.ibpt_api:
                xml_button[0].attrib['invisible'] = '1'
                orm.setup_modifiers(xml_button[0])
                res['arch'] = etree.tostring(xml, pretty_print=True)
        if res.get('toolbar') and not self.env.user.company_id.ibpt_api:
            res['toolbar']['action'] = []
        return res
