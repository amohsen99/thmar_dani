/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

/**
 * Service layer for all portal time off RPC calls.
 */
export const timeoffService = {
    /**
     * Fetch all data: leaves, balances, leave types.
     */
    async fetchData(statusFilter = 'all') {
        return rpc('/my/timeoff/data', { status_filter: statusFilter });
    },

    /**
     * Create a new leave request.
     */
    async createLeave(leaveTypeId, dateFrom, dateTo, description) {
        return rpc('/my/timeoff/create', {
            leave_type_id: leaveTypeId,
            date_from: dateFrom,
            date_to: dateTo,
            description: description || '',
        });
    },

    /**
     * Update an existing leave request.
     */
    async updateLeave(leaveId, leaveTypeId, dateFrom, dateTo, description) {
        return rpc('/my/timeoff/update', {
            leave_id: leaveId,
            leave_type_id: leaveTypeId,
            date_from: dateFrom,
            date_to: dateTo,
            description: description || '',
        });
    },

    /**
     * Delete a leave request.
     */
    async deleteLeave(leaveId) {
        return rpc('/my/timeoff/delete', { leave_id: leaveId });
    },
};
