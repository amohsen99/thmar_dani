from odoo import fields, models
from odoo.exceptions import UserError


class Job(models.Model):
    _name = 'factory.job'
    _inherit = 'factory.company.mixin'
    _description = 'أمر شغل المصنع'
    name = fields.Char('رقم أمر الشغل', required=True)
    partner_id = fields.Many2one('res.partner', string='العميل', check_company=True)
    fabric_id = fields.Many2one('factory.fabric', string='صنف القماش', required=True, check_company=True)
    date = fields.Date('التاريخ', default=fields.Date.context_today, required=True)
    batch_ids = fields.One2many('factory.dyeing.batch', 'job_id', string='التشغيلات')
    notes = fields.Text('ملاحظات')
    _job_unique = models.Constraint('unique(company_id, name)', 'رقم أمر الشغل مكرر.')

    def write(self, vals):
        if {'company_id', 'fabric_id', 'partner_id', 'name'} & set(vals) and any(
            batch.state == 'approved' for batch in self.mapped('batch_ids')
        ):
            raise UserError('لا يمكن تغيير هوية أمر شغل له تشغيلات معتمدة.')
        return super().write(vals)
