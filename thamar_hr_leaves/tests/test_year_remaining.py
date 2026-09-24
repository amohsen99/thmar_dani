from datetime import date
from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestYearRemaining(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True,
            mail_notrack=True, mail_notify_force_send=False, import_file=True))
        cls.Allocation = cls.env['hr.leave.allocation']
        cls.Opening = cls.env['hr.leave.opening.balance']
        cls.annual = cls.env.ref('thamar_hr_leaves.leave_type_annual')
        cls.casual = cls.env.ref('thamar_hr_leaves.leave_type_casual')
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Opening balance regression test',
            'hire_date': '2010-01-01 00:00:00',
            'birthday': '1985-01-01',
            'company_id': cls.env.company.id,
            'resource_calendar_id': cls.env.company.resource_calendar_id.id,
        })
        cls.Allocation._generate_employee_allocations(cls.employee, 2026)

    def opening(self, leave_type=None, amount=53, entitlement=23, carryover=38):
        return self.Opening.create({
            'employee_id': self.employee.id,
            'leave_type_id': (leave_type or self.annual).id,
            'balance_date': '2026-08-26',
            'balance_basis': 'year_remaining',
            'amount': amount,
            'carryover_days': carryover,
            'year_entitlement_days': entitlement,
        })

    def status(self, leave_type=None, day=date(2026, 9, 21)):
        return self.Allocation._get_monthly_accrual_status(
            self.employee, leave_type or self.annual, 2026, day,
        )

    def test_stock_does_not_grow_and_monthly_limit_unlocks(self):
        annual = self.opening()
        self.opening(self.casual, 7, 7, 0)
        self.assertEqual(annual.gross_balance_days, 61)
        self.assertEqual(annual.used_before_cutoff_days, 8)
        august = self.status(day=date(2026, 8, 26))
        september = self.status()
        december = self.status(day=date(2026, 12, 31))
        self.assertEqual([s['remaining_balance'] for s in (august,september,december)], [53,53,53])
        self.assertEqual(august['accrued_remaining'], 45.33)
        self.assertEqual(september['accrued_remaining'], 47.25)
        self.assertEqual(december['accrued_remaining'], 53)
        self.assertEqual(self.status(self.casual)['accrued_remaining'], 5.25)
        info = self.annual.get_allocation_data(self.employee, date(2026,9,21))[self.employee][0][1]
        self.assertEqual(info['virtual_remaining_leaves'], 53)
        self.assertEqual(info['leaves_taken'], 8)

    def test_negative_zero_and_repeated_sync_preserve_records(self):
        balance = self.opening(amount=-1, entitlement=14, carryover=0)
        self.assertEqual(self.status()['remaining_balance'], -1)
        self.assertEqual(self.status()['accrued_remaining'], 0)
        balance.write({'amount': 5})
        allocation_ids = balance.opening_allocation_ids.ids
        balance.write({'amount': 5})
        self.assertEqual(balance.opening_allocation_ids.ids, allocation_ids)
        self.assertEqual(balance.opening_allocation_ids.number_of_days, 5)
        balance.write({'amount': 0})
        self.assertEqual(balance.opening_allocation_ids.ids, allocation_ids)
        self.assertEqual(balance.opening_allocation_ids.state, 'refuse')
        balance.write({'amount': 3})
        self.assertEqual(balance.opening_allocation_ids.ids, allocation_ids)
        self.assertEqual(balance.opening_allocation_ids.state, 'validate')

    def test_regenerate_does_not_add_full_year_again(self):
        balance = self.opening()
        before = self.Allocation.search_count([('employee_id','=',self.employee.id)])
        self.Allocation._generate_employee_allocations(self.employee,2026)
        self.assertEqual(self.Allocation.search_count([('employee_id','=',self.employee.id)]),before)
        active = self.Allocation.search([
            ('employee_id','=',self.employee.id),('holiday_status_id','=',self.annual.id),
            ('state','=','validate'),('date_from','<=',date(2026,9,21)),
            '|',('date_to','=',False),('date_to','>=',date(2026,9,21)),
        ])
        self.assertEqual(sum(active.mapped('number_of_days')), balance.amount)
        self.assertEqual(self.Allocation._compute_annual_carryover(self.employee,2026),53)

    @freeze_time('2026-09-21')
    def test_post_cutoff_request_is_deducted_once(self):
        self.opening()
        leave = self.env['hr.leave'].create({
            'employee_id':self.employee.id, 'holiday_status_id':self.annual.id,
            'request_date_from':'2026-08-27', 'request_date_to':'2026-08-27',
        })
        status = self.status()
        self.assertGreater(leave.number_of_days, 0)
        self.assertEqual(status['remaining_balance'],round(53-leave.number_of_days,2))
        self.assertEqual(status['accrued_remaining'],round(47.25-leave.number_of_days,2))
        excluded = self.Allocation.with_context(ignored_leave_ids=leave.ids)._get_monthly_accrual_status(
            self.employee,self.annual,2026,date(2026,9,21))
        self.assertEqual(excluded['remaining_balance'],53)
        leave.action_refuse()
        self.assertEqual(self.status()['remaining_balance'],53)

    @freeze_time('2026-09-21')
    def test_monthly_limit_still_requires_hr_exception(self):
        self.opening(self.casual, 7, 7, 0)
        values = {
            'employee_id':self.employee.id, 'holiday_status_id':self.casual.id,
            'request_date_from':'2026-09-14', 'request_date_to':'2026-09-21',
        }
        with self.assertRaisesRegex(ValidationError, 'Monthly Accrual Limit Exceeded'), self.cr.savepoint():
            self.env['hr.leave'].create(values)
        leave = self.env['hr.leave'].create(dict(values, accrual_limit_override=True))
        self.assertGreater(leave.number_of_days, 5.25)
        self.assertLessEqual(leave.number_of_days, 7)

    def test_new_hire_prorated_source_does_not_accrue_twice(self):
        self.employee.write({'hire_date':'2026-03-14 00:00:00','birthday':'1990-01-01'})
        self.opening(amount=2.25, entitlement=11.25, carryover=0)
        self.assertEqual(self.status()['monthly_rate'],1.25)
        self.assertEqual(self.status()['remaining_balance'],2.25)
        self.assertEqual(self.status()['accrued_remaining'],0)
        self.assertEqual(self.status(day=date(2026,12,31))['accrued_remaining'],2.25)

    def test_age_and_verified_service_grant_one_bonus(self):
        self.employee.write({'birthday':'1960-01-01','has_verified_service_bonus':True,
                             'external_experience_years':0,'is_hazardous_location':True})
        details=self.Allocation._compute_employee_entitlement(self.employee,date(2026,12,31))
        self.assertEqual(details['age_bonus']+details['experience_bonus'],9)
        self.assertEqual(details['total_annual'],30)
