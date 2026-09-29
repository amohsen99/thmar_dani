from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestFactoryCosting(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.center = cls.env['factory.cost.center'].create({'name': 'صباغة'})
        cls.machine = cls.env['factory.machine'].create({'name': 'جيت اختبار', 'code': 'TEST-J1', 'center_id': cls.center.id})
        cls.fabric = cls.env['factory.fabric'].create({'name': 'قماش اختبار', 'meters_per_kg': 3})
        cls.job = cls.env['factory.job'].create({'name': 'TEST-JOB', 'fabric_id': cls.fabric.id})
        cls.operation = cls.env.ref('thamar_textile_costing.operation_0')
        cls.color = cls.env.ref('thamar_textile_costing.color_0')

    def rate(self, month, amount):
        rate = self.env['factory.machine.cost.rate'].create({'machine_id': self.machine.id, 'month': month, 'manual_rate': amount})
        rate.action_approve()
        return rate

    def batch(self, day='2026-09-10', **extra):
        vals = {'job_id': self.job.id, 'date': day, 'color_id': self.color.id, 'raw_kg': 100,
                'finished_kg': 90, 'finished_meters': 270,
                'operation_ids': [Command.create({'operation_id': self.operation.id, 'machine_id': self.machine.id, 'manual_hours': 2})],
                'material_ids': [Command.create({'name': 'أصباغ', 'amount': 100})]}
        vals.update(extra)
        return self.env['factory.dyeing.batch'].create(vals)

    def test_month_selection_and_snapshot(self):
        september = self.rate('2026-09-01', 250)
        self.rate('2026-10-01', 300)
        first = self.batch()
        second = self.batch('2026-10-15')
        self.assertEqual(first.operation_ids.rate_id, september)
        self.assertEqual(first.total_cost, 600)
        self.assertEqual(second.total_cost, 700)
        first.action_approve()
        september.action_draft()
        september.write({'manual_rate': 900})
        september.action_approve()
        self.assertEqual(first.operation_ids.snapshot_rate, 250)
        self.assertEqual(first.total_cost, 600)
        self.assertEqual(first.cost_per_kg, first.currency_id.round(600 / 90))
        self.assertEqual(first.cost_per_meter, first.currency_id.round(600 / 270))

    def test_missing_month_and_refresh(self):
        self.rate('2026-08-01', 100)
        batch = self.batch()
        self.assertTrue(batch.operation_ids.rate_missing)
        with self.assertRaises(UserError):
            batch.action_approve()
        self.rate('2026-09-01', 250)
        batch.action_refresh_rates()
        self.assertFalse(batch.operation_ids.rate_missing)
        batch.action_approve()

    def test_zero_is_valid_rate(self):
        self.rate('2026-09-01', 0)
        batch = self.batch()
        self.assertFalse(batch.operation_ids.rate_missing)
        batch.action_approve()
        self.assertEqual(batch.total_cost, 100)

    def test_date_change_selects_new_month(self):
        self.rate('2026-09-01', 250)
        october = self.rate('2026-10-01', 300)
        batch = self.batch()
        batch.date = '2026-10-01'
        self.assertEqual(batch.operation_ids.rate_id, october)
        self.assertEqual(batch.total_cost, 700)

    def test_lock_and_direct_state_bypass(self):
        rate = self.rate('2026-09-01', 250)
        batch = self.batch()
        with self.assertRaises(UserError):
            batch.write({'state': 'approved'})
        batch.action_approve()
        for obj, vals in [(batch, {'date': '2026-10-01'}), (batch.operation_ids, {'manual_hours': 8}),
                          (batch.material_ids, {'amount': 0}), (self.job, {'name': 'Changed'}),
                          (rate, {'manual_rate': 1})]:
            with self.assertRaises(UserError):
                obj.write(vals)
        with self.assertRaises(UserError):
            batch.material_ids.unlink()
        with self.assertRaises(UserError):
            self.env['factory.batch.material'].create({'batch_id': batch.id, 'name': 'Extra', 'amount': 1})
        with self.assertRaises(UserError):
            batch.unlink()

    def test_speed_and_extra(self):
        self.rate('2026-09-01', 250)
        batch = self.batch(extra_percent=10, extra_reason='إضافة اختبار')
        batch.operation_ids.write({'duration_method': 'speed', 'processed_meters': 600, 'meters_per_minute': 10})
        self.assertEqual(batch.operation_ids.hours, 1)
        self.assertEqual(batch.extra_cost, 25)
        self.assertEqual(batch.total_cost, 375)
        self.assertEqual(batch.raw_meters, 300)
        self.assertEqual(batch.loss_percent, 10)

    def test_cost_components(self):
        cat = self.env.ref('thamar_textile_costing.category_0')
        rate = self.env['factory.machine.cost.rate'].create({
            'machine_id': self.machine.id, 'month': '2026-09-01', 'method': 'detail', 'idle_percent': 10,
            'line_ids': [Command.create({'category_id': cat.id, 'method': 'usage', 'consumption': 5, 'unit_price': 2}),
                         Command.create({'category_id': cat.id, 'method': 'allocated', 'period_amount': 1000, 'allocation_percent': 50, 'period_hours': 100}),
                         Command.create({'category_id': cat.id, 'fixed_amount': 20})]})
        self.assertEqual(rate.base_rate, 35)
        self.assertAlmostEqual(rate.hourly_rate, 38.5)
        rate.action_approve()
        with self.assertRaises(UserError):
            rate.line_ids[0].write({'consumption': 999})

    def test_invalid_month_and_duplicate(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.rate('2026-09-10', 1)
        self.rate('2026-09-01', 1)
        with self.assertRaises(IntegrityError), self.cr.savepoint(), mute_logger('odoo.sql_db'):
            self.rate('2026-09-01', 2)

    def test_clock_overnight_and_month_change(self):
        self.rate('2026-09-01', 250)
        batch = self.batch()
        batch.operation_ids.with_context(tz='UTC').write({'duration_method': 'clock', 'start_at': '2026-09-10 23:00:00', 'end_at': '2026-09-11 01:00:00'})
        self.assertEqual(batch.operation_ids.hours, 2)
        batch.date = '2026-10-01'
        with self.assertRaises(ValidationError):
            batch.with_context(tz='UTC').action_approve()

    def test_empty_output_and_extra_reason(self):
        self.rate('2026-09-01', 250)
        batch = self.batch(finished_kg=0)
        with self.assertRaises(UserError):
            batch.action_approve()
        batch.write({'finished_kg': 90, 'extra_percent': 35})
        with self.assertRaises(UserError):
            batch.action_approve()

    def test_user_cannot_approve(self):
        self.rate('2026-09-01', 250)
        user = self.env['res.users'].create({'name': 'Cost user', 'login': 'cost_user_test', 'group_ids': [Command.set([self.env.ref('thamar_textile_costing.group_user').id])]})
        batch = self.batch()
        with self.assertRaises(UserError):
            batch.with_user(user).action_approve()

    def test_company_machine_mismatch(self):
        other = self.env['res.company'].create({'name': 'Other factory'})
        with self.assertRaises(UserError), self.cr.savepoint():
            self.env['factory.machine.cost.rate'].create({'company_id': other.id, 'machine_id': self.machine.id, 'month': '2026-09-01'})
