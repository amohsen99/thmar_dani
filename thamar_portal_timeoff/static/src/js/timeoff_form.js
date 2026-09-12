/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class TimeOffForm extends Component {
    static template = "thamar_portal_timeoff.TimeOffForm";
    static props = {
        leave: { type: Object, optional: true },
        leaveTypes: { type: Array },
        onSave: { type: Function },
        onClose: { type: Function },
    };

    setup() {
        const leave = this.props.leave;
        this.state = useState({
            form: {
                leave_type_id: leave ? leave.leave_type_id : '',
                date_from: leave ? leave.date_from : '',
                date_to: leave ? leave.date_to : '',
                description: leave ? leave.description : '',
            },
            error: '',
            submitting: false,
        });
    }

    onLeaveTypeChange(ev) {
        this.state.form.leave_type_id = ev.target.value;
    }

    onFieldChange(field, value) {
        this.state.form[field] = value;
    }

    async onSubmit() {
        const { leave_type_id, date_from, date_to, description } = this.state.form;
        this.state.error = '';

        // Validation
        if (!leave_type_id) {
            this.state.error = 'Please select a leave type.';
            return;
        }
        if (!date_from) {
            this.state.error = 'Please select a start date.';
            return;
        }
        if (!date_to) {
            this.state.error = 'Please select an end date.';
            return;
        }
        if (date_from > date_to) {
            this.state.error = 'End date must be after start date.';
            return;
        }

        this.state.submitting = true;
        try {
            await this.props.onSave({
                id: this.props.leave ? this.props.leave.id : null,
                leave_type_id,
                date_from,
                date_to,
                description,
            });
        } catch (e) {
            this.state.error = e.message || 'An unexpected error occurred.';
        } finally {
            this.state.submitting = false;
        }
    }
}
