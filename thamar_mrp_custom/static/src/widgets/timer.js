/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { MrpTimer } from "@mrp/widgets/timer";

// Enhanced formatMinutes function with days, hours, minutes, seconds
function formatMinutesExtended(value) {
    if (value === false) {
        return "";
    }
    const isNegative = value < 0;
    if (isNegative) {
        value = Math.abs(value);
    }

    // Convert minutes to total seconds
    const totalSeconds = Math.floor(value * 60);

    // Calculate days, hours, minutes, and seconds
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    // Format the output
    let result = "";
    if (days > 0) {
        result += `${days}d `;
    }
    if (hours > 0 || days > 0) {
        result += `${String(hours).padStart(2, "0")}:`;
    }
    result += `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

    return `${isNegative ? "-" : ""}${result}`;
}

// Patch the MrpTimer component to use the new format function
patch(MrpTimer.prototype, {
    get durationFormatted() {
        return formatMinutesExtended(this.state.duration);
    }
});

// Replace the formatter in the registry
registry.category("formatters").add("mrp_timer", formatMinutesExtended, { force: true });

