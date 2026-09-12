/**
 * Portal Employee Information – Vanilla JS
 * Mounted on .o_portal_employee_app
 */
(function () {
    'use strict';

    const SELECTOR = '.o_portal_employee_app';
    const API_URL = '/my/employee/data';

    function $(sel, ctx) { return (ctx || document).querySelector(sel); }
    function $$(sel, ctx) { return [...(ctx || document).querySelectorAll(sel)]; }

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.getAttribute('content');
        const cookie = document.cookie.split('; ').find(row => row.startsWith('csrf_token='));
        if (cookie) return cookie.split('=')[1];
        return null;
    }

    function callRpc(url, params) {
        const token = getCsrfToken();
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Csrf-Token'] = token;
        return fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params }),
            credentials: 'same-origin',
        }).then(res => res.json()).then(data => {
            if (data.error) throw new Error(data.error.message || 'RPC error');
            return data.result;
        });
    }

    function formatDate(val) {
        if (!val) return '';
        const d = new Date(val + 'T00:00:00');
        if (isNaN(d)) return val;
        return d.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    }

    function formatDateTime(val) {
        if (!val) return '';
        const d = new Date(val + 'T00:00:00');
        if (isNaN(d)) return val;
        return d.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    }

    function formatHours(h) {
        if (h === null || h === undefined || h === '') return '';
        const hrs = Math.floor(h);
        const mins = Math.round((h - hrs) * 60);
        const suffix = hrs >= 12 ? 'PM' : 'AM';
        let displayHrs = hrs % 12;
        if (displayHrs === 0) displayHrs = 12;
        const mm = mins.toString().padStart(2, '0');
        return `${displayHrs}:${mm} ${suffix}`;
    }

    function getInitials(name) {
        if (!name) return '?';
        const parts = name.trim().split(/\s+/);
        if (parts.length >= 2) {
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }
        return name.substring(0, 2).toUpperCase();
    }

    function dayName(index) {
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return days[parseInt(index)] || '';
    }

    function showToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `pei-toast ${type}`;
        toast.innerHTML = `
            <i class="fa ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"/>
            <span>${message}</span>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    function renderField(label, value, isEmpty = false) {
        const cls = isEmpty ? 'pei-item-value empty' : 'pei-item-value';
        const display = isEmpty ? '—' : value;
        return `
            <div class="pei-item">
                <span class="pei-item-label">${label}</span>
                <span class="${cls}">${display}</span>
            </div>
        `;
    }

    function renderPersonalSection(emp) {
        const isEmpty = (v) => !v && v !== 0;

        return `
            <div class="pei-section">
                <div class="pei-section-title">
                    <i class="fa fa-user"/>
                    Personal Information
                </div>
                <div class="pei-grid">
                    ${renderField('Employee ID', emp.identification_id, isEmpty(emp.identification_id))}
                    ${renderField('Gender', emp.gender, isEmpty(emp.gender))}
                    ${renderField('Marital Status', emp.marital, isEmpty(emp.marital))}
                    ${renderField('Birthday', formatDate(emp.birthday), isEmpty(emp.birthday))}
                    ${renderField('Country of Birth', emp.country_of_birth, isEmpty(emp.country_of_birth))}
                    ${renderField('Place of Birth', emp.place_of_birth, isEmpty(emp.place_of_birth))}
                    ${renderField('Passport ID', emp.passport_id, isEmpty(emp.passport_id))}
                    ${renderField('Work Email', emp.work_email, isEmpty(emp.work_email))}
                    ${renderField('Work Phone', emp.work_phone, isEmpty(emp.work_phone))}
                    ${renderField('Mobile', emp.mobile_phone, isEmpty(emp.mobile_phone))}
                </div>
            </div>
        `;
    }

    function renderJobSection(emp) {
        const isEmpty = (v) => !v && v !== 0;

        return `
            <div class="pei-section">
                <div class="pei-section-title">
                    <i class="fa fa-briefcase"/>
                    Job Information
                </div>
                <div class="pei-grid">
                    ${renderField('Job Title', emp.job_id, isEmpty(emp.job_id))}
                    ${renderField('Department', emp.department_id, isEmpty(emp.department_id))}
                    ${renderField('Manager', emp.manager_id, isEmpty(emp.manager_id))}
                    ${renderField('Coach', emp.coach_id, isEmpty(emp.coach_id))}
                    ${renderField('Supervisor', emp.supervisor_id, isEmpty(emp.supervisor_id))}
                    ${renderField('Employment Type', emp.employee_type, isEmpty(emp.employee_type))}
                    ${renderField('Hire Date', formatDateTime(emp.hire_date), isEmpty(emp.hire_date))}
                    ${renderField('Administrative Type', emp.admin_type, isEmpty(emp.admin_type))}
                    ${renderField('Work Location', emp.work_location, isEmpty(emp.work_location))}
                    ${renderField('Address', emp.address, isEmpty(emp.address))}
                </div>
            </div>
        `;
    }

    function renderScheduleSection(emp) {
        if (!emp.schedule_lines || !emp.schedule_lines.length) {
            return `
                <div class="pei-section">
                    <div class="pei-section-title">
                        <i class="fa fa-clock-o"/>
                        Work Schedule
                    </div>
                    <div class="pei-empty-state">
                        No schedule configured for <strong>${emp.resource_calendar || 'this employee'}</strong>.
                    </div>
                </div>
            `;
        }

        const rows = emp.schedule_lines.map(line => `
            <tr>
                <td>${line.day_name || dayName(line.day)}</td>
                <td>${formatHours(line.hour_from)}</td>
                <td>${formatHours(line.hour_to)}</td>
                <td>${(line.hour_to - line.hour_from).toFixed(2)}h</td>
            </tr>
        `).join('');

        return `
            <div class="pei-section">
                <div class="pei-section-title">
                    <i class="fa fa-clock-o"/>
                    Work Schedule
                </div>
                <div style="margin-bottom: 0.75rem; color: var(--pei-text-muted); font-size: 0.85rem;">
                    <i class="fa fa-calendar me-1"/>
                    ${emp.resource_calendar || 'Custom Schedule'}
                </div>
                <div style="overflow-x: auto;">
                    <table class="pei-schedule-table">
                        <thead>
                            <tr>
                                <th>Day</th>
                                <th>From</th>
                                <th>To</th>
                                <th>Hours</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    function renderOtherSection(emp) {
        const isEmpty = (v) => !v && v !== 0;

        return `
            <div class="pei-section">
                <div class="pei-section-title">
                    <i class="fa fa-info-circle"/>
                    Additional Information
                </div>
                <div class="pei-grid">
                    ${renderField('Timezone', emp.tz, isEmpty(emp.tz))}
                    ${renderField('Distance to Work (km)', emp.km_home_work, isEmpty(emp.km_home_work))}
                    ${renderField('Emergency Contact', emp.emergency_contact, isEmpty(emp.emergency_contact))}
                    ${renderField('Emergency Phone', emp.emergency_phone, isEmpty(emp.emergency_phone))}
                </div>
            </div>
        `;
    }

    function renderProfile(emp) {
        const avatarInitials = getInitials(emp.name);
        const jobTitle = emp.job_id || 'Employee';
        const department = emp.department_id || '';
        const typeLabel = emp.employee_type === 'employee' ? 'Employee'
            : emp.employee_type === 'student' ? 'Student'
            : emp.employee_type || 'Employee';
        const typeClass = typeLabel === 'Employee' ? 'primary' : 'success';

        const tags = [];
        if (typeLabel) tags.push(`<span class="pei-tag ${typeClass}">${typeLabel}</span>`);
        if (department) tags.push(`<span class="pei-tag">${department}</span>`);
        if (emp.work_location) tags.push(`<span class="pei-tag">${emp.work_location}</span>`);

        return `
            <div class="pei-profile-card">
                <div class="pei-profile-top">
                    <div class="pei-avatar">${avatarInitials}</div>
                    <div class="pei-profile-info">
                        <h3>${emp.name}</h3>
                        <div class="pei-job-title">${jobTitle}</div>
                        ${department ? `<div class="pei-department">${department}</div>` : ''}
                        <div class="pei-profile-tags">
                            ${tags.join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async function loadData() {
        const el = document.querySelector(SELECTOR);
        if (!el) return;

        const employeeId = el.dataset.employeeId;
        if (!employeeId || employeeId === 'False') {
            el.innerHTML = `
                <div class="pei-wrapper">
                    <div class="alert alert-warning text-center m-4">
                        <i class="fa fa-exclamation-triangle me-2"></i>
                        No employee record is linked to your portal account. Please contact HR.
                    </div>
                </div>
            `;
            return;
        }

        try {
            const data = await callRpc(API_URL, {});

            if (!data || !data.employee) {
                throw new Error('Invalid response');
            }

            const emp = data.employee;

            // Remove loading state
            const loadingEl = document.getElementById('employee_loading');
            if (loadingEl) {
                loadingEl.remove();
            }

            // Build and inject content
            const html = `
                <div class="pei-wrapper">
                    ${renderProfile(emp)}
                    <div class="pei-actions">
                        <button class="pei-btn-secondary" onclick="window.print()">
                            <i class="fa fa-print"/>
                            Print Profile
                        </button>
                    </div>
                    ${renderPersonalSection(emp)}
                    ${renderJobSection(emp)}
                    ${renderScheduleSection(emp)}
                    ${renderOtherSection(emp)}
                </div>
            `;

            el.innerHTML = html;

        } catch (e) {
            console.error('Failed to load employee data:', e);
            const loadingEl = document.getElementById('employee_loading');
            if (loadingEl) {
                loadingEl.outerHTML = `
                    <div class="pei-wrapper">
                        <div class="alert alert-danger text-center m-4">
                            <i class="fa fa-exclamation-circle me-2"></i>
                            Failed to load profile. Please try again later.
                        </div>
                    </div>
                `;
            }
            showToast('Failed to load employee profile.', 'error');
        }
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadData);
    } else {
        loadData();
    }
})();
