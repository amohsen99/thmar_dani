# -*- coding: utf-8 -*-
"""Enable the existing Casual Leave monthly policy without replacing data."""


def migrate(cr, version):
    """Update only the policy flag on the module-owned Casual Leave type.

    ``leave_type_casual`` was originally imported with ``noupdate=1``.  Its
    XML ID and target record must remain untouched, but the new policy has to
    apply to already-installed databases as well as new installations.
    """
    cr.execute("""
        UPDATE hr_leave_type
           SET use_monthly_accrual = TRUE
         WHERE id = (
             SELECT res_id
               FROM ir_model_data
              WHERE module = 'thamar_hr_leaves'
                AND name = 'leave_type_casual'
                AND model = 'hr.leave.type'
         )
           AND use_monthly_accrual IS NOT TRUE
    """)
