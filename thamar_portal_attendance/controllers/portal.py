from datetime import datetime

from dateutil.relativedelta import relativedelta

import pytz

from odoo import _, http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager


class PortalAttendance(CustomerPortal):
    @http.route(
        ['/my/attendance', '/my/attendance/page/<int:page>'],
        type='http', auth='user', website=True, methods=['GET'],
    )
    def portal_attendance(self, page=1, month='', status='all', **kw):
        values = self._prepare_portal_layout_values()
        # Identity is always resolved on the server, never from request parameters.
        employee = request.env.user.sudo().employee_id
        attendance = request.env['hr.attendance'].sudo()
        domain = [('employee_id', '=', employee.id)] if employee else [('id', '=', 0)]
        if status not in ('all', 'open', 'closed'):
            status = 'all'
        if status != 'all':
            domain.append(('check_out', '=' if status == 'open' else '!=', False))
        timezone = pytz.timezone(request.env.user.tz or employee.tz or 'UTC')
        error = False
        try:
            if month:
                start = datetime.strptime(month, '%Y-%m')
                end = start + relativedelta(months=1)
                for boundary, operator in ((start, '>='), (end, '<')):
                    utc = timezone.localize(boundary).astimezone(pytz.UTC)
                    domain.append(('check_in', operator, utc.replace(tzinfo=None)))
        except (ValueError, OverflowError):
            error = _('اختر شهراً وسنة صالحين.')
            domain.append(('id', '=', 0))
        total = attendance.search_count(domain)
        pagination = pager('/my/attendance', total, page=page, step=20, url_args={
            'month': month, 'status': status,
        })
        records = attendance.search(domain, order='check_in desc, id desc', limit=20,
                                    offset=pagination['offset'])
        values.update({
            'page_name': 'attendance', 'employee': employee, 'attendances': records,
            'pager': pagination, 'total': total, 'error': error,
            'month': month, 'status': status,
            'attendance_timezone': timezone.zone,
            'format_attendance_time': lambda dt: pytz.UTC.localize(dt).astimezone(timezone).strftime('%Y-%m-%d %H:%M'),
        })
        return request.render('thamar_portal_attendance.portal_attendance_page', values)
