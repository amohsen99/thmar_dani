/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

export const teamLeaveService = {
    fetchData(statusFilter = "all") {
        return rpc("/my/team/timeoff/data", { status_filter: statusFilter });
    },

    applyAction(leaveId, action) {
        return rpc("/my/team/timeoff/action", {
            leave_id: leaveId,
            action,
        });
    },

    createLeave(values) {
        return rpc("/my/team/timeoff/create", values);
    },
};
