# -*- coding: utf-8 -*-
"""Installation-time ownership migration for records formerly in Custom."""


def pre_init_hook(env):
    """Rebind moved records before this module's XML is loaded.

    The rows and their ``res_id`` values are retained; only the XML-ID module
    namespace is reassigned.  This lets Odoo update the original views,
    groups, rules, actions, menus, and ACLs instead of creating replacements.
    """
    names = (
        'group_hr_holidays_clinical_manager',
        'hr_leave_clinical_manager_rule',
        'group_hr_holidays_department_supervisor',
        'hr_leave_department_supervisor_rule',
        'group_hr_holidays_department_manager',
        'hr_leave_department_manager_rule',
        'access_hr_leave_department_supervisor',
        'access_hr_leave_department_manager',
        'access_hr_leave_allocation_department',
        'access_hr_leave_allocation_department_manager',
        'hr_leave_view_tree_inherit_department',
        'hr_leave_view_form_inherit_supervisor',
        'hr_leave_view_search_inherit_clinical',
        'hr_leave_action_clinical_approval',
        'menu_hr_holidays_clinical_approval',
        'hr_leave_action_department_leaves',
        'menu_hr_leave_department_leaves',
        'hr_leave_type_view_form_inherit_clinical',
        'view_department_form_inherit_supervisor',
        'res_config_settings_view_form_clinical_manager',
    )
    env.cr.execute("""
        UPDATE ir_model_data old
           SET module = 'thamar_hr_leaves'
         WHERE old.module = 'thamar_hr_custom'
           AND old.name = ANY(%s)
           AND NOT EXISTS (
               SELECT 1 FROM ir_model_data new
                WHERE new.module = 'thamar_hr_leaves' AND new.name = old.name
           )
    """, [list(names)])
