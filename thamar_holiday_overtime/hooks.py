def post_init_hook(env):
    env['hr.department']._sync_overtime_approver_groups()
