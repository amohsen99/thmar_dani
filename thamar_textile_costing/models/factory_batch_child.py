from odoo import api, fields, models
from odoo.exceptions import UserError


class BatchChild(models.AbstractModel):
    _name = 'factory.batch.child'
    _description = 'حماية تفاصيل التشغيلة'
    _check_company_auto = True
    batch_id = fields.Many2one('factory.dyeing.batch', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='batch_id.company_id', store=True)
    currency_id = fields.Many2one(related='batch_id.currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        batches = self.env['factory.dyeing.batch'].browse([v.get('batch_id') for v in vals_list if v.get('batch_id')])
        if any(b.state == 'approved' for b in batches):
            raise UserError('لا يمكن إضافة سطور لتشغيلة معتمدة.')
        return super().create(vals_list)

    def write(self, vals):
        batches = self.mapped('batch_id') | self.env['factory.dyeing.batch'].browse(vals.get('batch_id', []))
        if any(b.state == 'approved' for b in batches):
            raise UserError('لا يمكن تعديل سطور تشغيلة معتمدة.')
        return super().write(vals)

    def unlink(self):
        if any(r.batch_id.state == 'approved' for r in self):
            raise UserError('لا يمكن حذف سطور تشغيلة معتمدة.')
        return super().unlink()
