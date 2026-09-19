from datetime import datetime

import pytz

from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import format_datetime
from odoo.addons.portal.controllers.portal import pager as portal_pager
from .portal import PortalTimeOff


class PortalOvertime(PortalTimeOff):
    _REQUEST_CATEGORIES = {
        'overtime': {
            'base_url': '/my/overtime',
            'page_name': 'overtime',
            'title': 'طلبات العمل الإضافي',
            'singular': 'عمل إضافي',
        },
        'mission': {
            'base_url': '/my/missions',
            'page_name': 'missions',
            'title': 'المأموريات',
            'singular': 'مأمورية',
        },
    }

    def _request_category(self, request_category):
        return self._REQUEST_CATEGORIES.get(request_category, self._REQUEST_CATEGORIES['overtime'])

    def _overtime_values(self, scope='mine', page=1, error=None, form_values=None,
                         request_category='overtime'):
        category = self._request_category(request_category)
        model = request.env['thamar.overtime.request']
        departments = model._managed_departments()
        team = scope == 'team' and bool(departments)
        domain = [('company_id', 'in', request.env.companies.ids)]
        domain += [('kind', '=', 'mission')] if request_category == 'mission' else [('kind', '!=', 'mission')]
        domain += [('department_id', 'in', departments.ids)] if team else [('employee_id.user_id', '=', request.env.uid)]
        pager = portal_pager(url=category['base_url'], total=model.sudo().search_count(domain), page=page,
                             step=50, url_args={'scope': 'team' if team else 'mine'})
        records = model.sudo().search(domain, limit=50, offset=pager['offset'])
        employees = request.env['hr.employee'].sudo().search([
            ('department_id', 'in', departments.ids), ('company_id', 'in', request.env.companies.ids),
            ('user_id', '!=', request.env.uid),
        ], order='name') if departments else request.env['hr.employee']
        form_values = form_values or {}
        start_date, start_hour = self._portal_date_hour_values(form_values.get('date_start'))
        stop_date, stop_hour = self._portal_date_hour_values(form_values.get('date_stop'))
        values = self._prepare_portal_layout_values()
        kinds = dict(model._fields['kind']._description_selection(request.env))
        if request_category == 'mission':
            kinds = {'mission': kinds['mission']}
        else:
            kinds.pop('mission', None)
        values.update(page_name=category['page_name'], overtime_records=records, overtime_employees=employees,
                      can_create_overtime=bool(departments), overtime_team=team, pager=pager,
                      overtime_error=error, overtime_form=form_values, overtime_kinds=kinds,
                      overtime_start_date=start_date, overtime_start_hour=start_hour,
                      overtime_stop_date=stop_date, overtime_stop_hour=stop_hour,
                      overtime_states=dict(model._fields['state']._description_selection(request.env)),
                      request_category=request_category, portal_base_url=category['base_url'],
                      portal_title=category['title'], portal_singular=category['singular'],
                      overtime_datetime=lambda value: format_datetime(
                          request.env, value, tz=request.env.user.tz or 'UTC',
                          dt_format='yyyy-MM-dd HH',
                      ))
        return values

    @staticmethod
    def _portal_date_hour_values(value):
        value = value or ''
        if len(value) >= 13 and value[10] in ('T', ' '):
            return value[:10], value[11:13]
        return '', ''

    @staticmethod
    def _portal_datetime_value(value, date_value, hour_value, label):
        if not date_value and not hour_value:
            return value or ''
        try:
            hour = int(hour_value)
            datetime.strptime(date_value, '%Y-%m-%d')
        except (TypeError, ValueError):
            raise ValidationError(_('أدخل تاريخ وساعة %(label)s بصورة صحيحة.') % {'label': label})
        if not 0 <= hour <= 23:
            raise ValidationError(_('ساعة %(label)s يجب أن تكون بين 00 و23.') % {'label': label})
        return '%sT%02d:00' % (date_value, hour)

    @http.route(['/my/overtime', '/my/overtime/page/<int:page>'], type='http', auth='user', website=True, methods=['GET'])
    def portal_overtime(self, scope='mine', page=1, **kw):
        return self._portal_request_page('overtime', scope, page)

    @http.route(['/my/missions', '/my/missions/page/<int:page>'], type='http', auth='user', website=True, methods=['GET'])
    def portal_missions(self, scope='mine', page=1, **kw):
        return self._portal_request_page('mission', scope, page)

    def _portal_request_page(self, request_category, scope, page):
        feedback = request.session.pop('thamar_overtime_feedback', {})
        if feedback.get('request_category') != request_category:
            feedback = {}
        return request.render('thamar_portal_timeoff.portal_overtime', self._overtime_values(
            scope, page, error=feedback.get('error'), form_values=feedback.get('form_values'),
            request_category=request_category,
        ))

    def _overtime_redirect(self, request_category='overtime', error=None, form_values=None):
        # Always render forms on GET: reloads and language/debug navigation must
        # neither replay a mutation nor hide validation errors behind HTTP 405.
        if error:
            request.session['thamar_overtime_feedback'] = {
                'error': str(error), 'form_values': form_values or {},
                'request_category': request_category,
            }
        else:
            request.session.pop('thamar_overtime_feedback', None)
        return request.redirect('%s?scope=team' % self._request_category(request_category)['base_url'], code=303)

    @http.route(['/my/overtime/create', '/my/overtime/action'], type='http', auth='user',
                website=True, methods=['GET'])
    def portal_overtime_form_redirect(self, request_category='overtime', **kw):
        # GET is navigation only. All creation and approval still require POST + CSRF.
        return self._overtime_redirect(request_category)

    @http.route('/my/overtime/create', type='http', auth='user', website=True, methods=['POST'])
    def portal_overtime_create(self, employee_id=None, kind=None, date_start=None, date_stop=None,
                               date_start_date=None, date_start_hour=None,
                               date_stop_date=None, date_stop_hour=None, reason='',
                               request_category='overtime', **kw):
        try:
            with request.env.cr.savepoint():
                model = request.env['thamar.overtime.request']
                employee = request.env['hr.employee'].sudo().browse(self._parse_positive_id(employee_id, _('الموظف'))).exists()
                if not employee or employee.department_id not in model._managed_departments() or employee.user_id.id == request.env.uid:
                    raise AccessError(_('يمكنك إنشاء طلب لموظفي أقسامك فقط.'))
                if kind not in dict(model._fields['kind'].selection):
                    raise ValidationError(_('نوع العمل الإضافي غير صالح.'))
                if (request_category == 'mission') != (kind == 'mission'):
                    raise ValidationError(_('اختر نوع الطلب من قائمته المخصصة.'))
                if not reason.strip() or len(reason) > 2000:
                    raise ValidationError(_('أدخل سبباً لا يتجاوز 2000 حرف.'))
                date_start = self._portal_datetime_value(
                    date_start, date_start_date, date_start_hour, _('البداية'))
                date_stop = self._portal_datetime_value(
                    date_stop, date_stop_date, date_stop_hour, _('النهاية'))
                zone = pytz.timezone(employee.resource_calendar_id.tz or employee.company_id.resource_calendar_id.tz or 'UTC')
                try:
                    start = zone.localize(datetime.strptime(date_start or '', '%Y-%m-%dT%H:%M'), is_dst=None).astimezone(pytz.utc).replace(tzinfo=None)
                    stop = zone.localize(datetime.strptime(date_stop or '', '%Y-%m-%dT%H:%M'), is_dst=None).astimezone(pytz.utc).replace(tzinfo=None)
                except (ValueError, TypeError, pytz.InvalidTimeError):
                    raise ValidationError(_('أدخل وقت بداية ونهاية صالحين حسب توقيت الموظف.'))
                rec = model.sudo().create({'employee_id': employee.id, 'kind': kind,
                    'date_start': start, 'date_stop': stop, 'reason': reason.strip()})
                rec.action_submit()
        except (AccessError, UserError, ValidationError) as exc:
            return self._overtime_redirect(request_category, exc, {
                'employee_id': str(employee_id or ''), 'kind': kind or '',
                'date_start': date_start or '', 'date_stop': date_stop or '',
                'reason': (reason or '')[:2000],
            })
        return self._overtime_redirect(request_category)

    @http.route('/my/overtime/action', type='http', auth='user', website=True, methods=['POST'])
    def portal_overtime_action(self, overtime_id=None, action=None, request_category='overtime', **kw):
        try:
            with request.env.cr.savepoint():
                rec = request.env['thamar.overtime.request'].sudo().browse(self._parse_positive_id(overtime_id, _('الطلب'))).exists()
                if not rec or not rec._is_department_approver():
                    raise AccessError(_('لا يمكنك إدارة هذا الطلب.'))
                request_category = 'mission' if rec.kind == 'mission' else 'overtime'
                methods = {'approve': 'action_approve', 'refuse': 'action_refuse', 'cancel': 'action_cancel'}
                if action not in methods:
                    raise UserError(_('إجراء غير صالح.'))
                getattr(rec, methods[action])()
        except (AccessError, UserError, ValidationError) as exc:
            return self._overtime_redirect(request_category, exc)
        return self._overtime_redirect(request_category)
