/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { timeoffService } from "./timeoff_service";
import { TimeOffStats } from "./timeoff_stats";
import { TimeOffList } from "./timeoff_list";
import { TimeOffForm } from "./timeoff_form";
import { Interaction } from "@web/public/interaction";

/**
 * Main application component mounted on the portal page.
 */
export class TimeOffApp extends Component {
    static template = "thamar_portal_timeoff.TimeOffApp";
    static components = { TimeOffStats, TimeOffList, TimeOffForm };
    static props = {
        employeeId: { type: Number, optional: true },
        employeeName: { type: String, optional: true },
        requestKind: { type: String, optional: true },
    };

    setup() {
        this.state = useState({
            leaves: [],
            balances: [],
            leaveTypes: [],
            filter: 'all',
            showForm: false,
            editingLeave: null,
            toast: null,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        try {
            const data = await timeoffService.fetchData(this.state.filter, this.props.requestKind);
            this.state.leaves = data.leaves || [];
            this.state.balances = data.balances || [];
            this.state.leaveTypes = data.leave_types || [];
        } catch (e) {
            const itemName = this.props.requestKind === 'assignment' ? 'التكليفات' : 'الإجازات';
            this.showToast('error', `تعذر تحميل بيانات ${itemName}.`);
            console.error(e);
        }
    }

    async onFilterChange(filter) {
        this.state.filter = filter;
        await this.loadData();
    }

    onNewRequest() {
        if (!this.state.leaveTypes.length) {
            this.showToast('error', 'لا يوجد نوع إجازة متاح حالياً للطلب من البوابة.');
            return;
        }
        this.state.editingLeave = null;
        this.state.showForm = true;
    }

    onEdit(leave) {
        this.state.editingLeave = leave;
        this.state.showForm = true;
    }

    onCloseForm() {
        this.state.showForm = false;
        this.state.editingLeave = null;
    }

    async onSave(formData) {
        try {
            let res;
            if (formData.id) {
                res = await timeoffService.updateLeave(
                    formData.id,
                    formData.leave_type_id,
                    formData.date_from,
                    formData.date_to,
                    formData.description
                );
            } else {
                res = await timeoffService.createLeave(
                    formData.leave_type_id,
                    formData.date_from,
                    formData.date_to,
                    formData.description
                );
            }

            if (res.success) {
                this.showToast('success', res.message);
                this.onCloseForm();
                await this.loadData();
            } else {
                throw new Error(res.message);
            }
        } catch (e) {
            throw e; // Form component will catch and display
        }
    }

    async onDelete(leave) {
        if (!confirm('هل أنت متأكد من حذف طلب الإجازة؟')) {
            return;
        }

        try {
            const res = await timeoffService.deleteLeave(leave.id);
            if (res.success) {
                this.showToast('success', res.message);
                await this.loadData();
            } else {
                this.showToast('error', res.message);
            }
        } catch (e) {
            this.showToast('error', 'حدث خطأ أثناء حذف الطلب.');
            console.error(e);
        }
    }

    showToast(type, message) {
        this.state.toast = { type, message };
        window.setTimeout(() => {
            this.state.toast = null;
        }, 3000);
    }
}

/**
 * Interaction to mount the OWL app to the portal DOM element.
 */
export class TimeOffAppInteraction extends Interaction {
    static selector = ".o_portal_timeoff_app";

    async start() {
        const employeeIdStr = this.el.dataset.employeeId;
        const employeeId = employeeIdStr && employeeIdStr !== 'False' ? parseInt(employeeIdStr) : null;
        
        if (!employeeId) {
            this.el.innerHTML = `
                <div class="alert alert-warning text-center m-4">
                    <i class="fa fa-exclamation-triangle me-2"></i>
                    لا يوجد سجل موظف مرتبط بحساب البوابة. يرجى التواصل مع إدارة الموارد البشرية.
                </div>`;
            return;
        }

        const employeeName = this.el.dataset.employeeName || '';
        const requestKind = this.el.dataset.requestKind || 'timeoff';
        
        // Remove loading state
        const loadingEl = this.el.querySelector(".pto-loading");
        if (loadingEl) {
            loadingEl.remove();
        }

        // Mount the OWL component
        this.env.config = { ...this.env.config, isPortal: true };
        this.mountComponent(this.el, TimeOffApp, { employeeId, employeeName, requestKind });
    }
}

registry.category("public.interactions").add("thamar_portal_timeoff.app", TimeOffAppInteraction);
