/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { teamLeaveService } from "./team_leave_service";

export class TeamLeaveApp extends Component {
    static template = "thamar_portal_timeoff.TeamLeaveApp";
    static props = {};

    setup() {
        this.state = useState({
            leaves: [],
            employees: [],
            leaveTypes: [],
            canCreateLeaves: false,
            filter: "all",
            loading: true,
            processingId: null,
            showLeaveForm: false,
            submitting: false,
            error: "",
            toast: null,
            form: this.emptyLeaveForm(),
        });
        onWillStart(() => this.loadData());
    }

    emptyLeaveForm() {
        return {
            employee_id: "",
            leave_type_id: "",
            date_from: "",
            date_to: "",
            description: "",
        };
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await teamLeaveService.fetchData(this.state.filter);
            this.state.leaves = data.leaves || [];
            this.state.employees = data.employees || [];
            this.state.leaveTypes = data.leave_types || [];
            this.state.canCreateLeaves = Boolean(data.can_create_leaves);
        } catch (error) {
            this.showToast("error", "تعذر تحميل طلبات إجازات الفريق.");
            console.error(error);
        } finally {
            this.state.loading = false;
        }
    }

    async onFilterChange(filter) {
        this.state.filter = filter;
        await this.loadData();
    }

    async onAction(leave, action) {
        const actionLabel = action === "approve" ? "اعتماد" : "رفض";
        if (!confirm(`هل أنت متأكد من ${actionLabel} طلب ${leave.employee_name}؟`)) {
            return;
        }
        this.state.processingId = leave.id;
        try {
            const result = await teamLeaveService.applyAction(leave.id, action);
            this.showToast(result.success ? "success" : "error", result.message);
            if (result.success) {
                await this.loadData();
            }
        } catch (error) {
            this.showToast("error", "تعذر تنفيذ الإجراء على الطلب.");
            console.error(error);
        } finally {
            this.state.processingId = null;
        }
    }

    get availableLeaveTypes() {
        const employee = this.state.employees.find(
            (item) => String(item.id) === String(this.state.form.employee_id)
        );
        if (!employee) {
            return [];
        }
        const availableIds = new Set(employee.leave_type_ids || []);
        return this.state.leaveTypes.filter((item) => availableIds.has(item.id));
    }

    openLeaveForm() {
        this.state.form = this.emptyLeaveForm();
        this.state.error = "";
        this.state.showLeaveForm = true;
    }

    closeLeaveForm() {
        if (!this.state.submitting) {
            this.state.showLeaveForm = false;
            this.state.error = "";
        }
    }

    onFormField(field, event) {
        this.state.form[field] = event.target.value;
        if (field === "employee_id") {
            this.state.form.leave_type_id = "";
        }
        this.state.error = "";
    }

    async createLeave() {
        const form = this.state.form;
        if (!form.employee_id || !form.leave_type_id || !form.date_from || !form.date_to) {
            this.state.error = "اختر الموظف ونوع الإجازة وحدد تاريخ البداية والنهاية.";
            return;
        }
        if (form.date_from > form.date_to) {
            this.state.error = "يجب أن يكون تاريخ النهاية مساويًا لتاريخ البداية أو بعده.";
            return;
        }
        this.state.submitting = true;
        try {
            const result = await teamLeaveService.createLeave({ ...form });
            if (!result.success) {
                this.state.error = result.message;
                return;
            }
            this.state.showLeaveForm = false;
            this.showToast("success", result.message);
            await this.loadData();
        } catch (error) {
            this.state.error = "تعذر إنشاء طلب الإجازة حاليًا.";
            console.error(error);
        } finally {
            this.state.submitting = false;
        }
    }

    showToast(type, message) {
        this.state.toast = { type, message };
        window.setTimeout(() => {
            this.state.toast = null;
        }, 3000);
    }
}

export class TeamLeaveAppInteraction extends Interaction {
    static selector = ".o_portal_team_timeoff_app";

    async start() {
        const loadingElement = this.el.querySelector(".pto-loading");
        if (loadingElement) {
            loadingElement.remove();
        }
        this.env.config = { ...this.env.config, isPortal: true };
        this.mountComponent(this.el, TeamLeaveApp);
    }
}

registry.category("public.interactions").add(
    "thamar_portal_timeoff.team_app",
    TeamLeaveAppInteraction
);
