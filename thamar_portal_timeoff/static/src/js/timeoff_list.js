/** @odoo-module **/

import { Component } from "@odoo/owl";

export class TimeOffList extends Component {
    static template = "thamar_portal_timeoff.TimeOffList";
    static props = {
        leaves: { type: Array },
        filter: { type: String },
        onFilterChange: { type: Function },
        onEdit: { type: Function },
        onDelete: { type: Function },
    };
}
