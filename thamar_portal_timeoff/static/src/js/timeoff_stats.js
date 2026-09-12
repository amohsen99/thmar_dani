/** @odoo-module **/

import { Component } from "@odoo/owl";

export class TimeOffStats extends Component {
    static template = "thamar_portal_timeoff.TimeOffStats";
    static props = {
        balances: { type: Array },
    };
}
