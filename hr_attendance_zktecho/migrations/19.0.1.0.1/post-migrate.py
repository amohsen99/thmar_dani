"""Remove a legacy daily uniqueness index incompatible with Odoo 19 intervals."""


def migrate(cr, version):
    # Odoo 19 can generate multiple overtime intervals/rates for one day.
    # This custom index is not an Odoo constraint; keep all overtime rows and
    # the standard interval validity constraints intact.
    cr.execute("""
        SELECT 1
          FROM pg_indexes
         WHERE schemaname = current_schema()
           AND tablename = 'hr_attendance_overtime_line'
           AND indexname = 'uq_hr_attendance_overtime_employee_date'
    """)
    if cr.fetchone():
        cr.execute('DROP INDEX uq_hr_attendance_overtime_employee_date')
