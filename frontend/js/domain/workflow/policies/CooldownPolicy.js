export class CooldownPolicy {
    static getRemainingMs(mergedConfig) {
        if (!mergedConfig.cooldown_enabled) return 0;

        const cdMinutes = mergedConfig.cooldown_minutes || 0;
        if (cdMinutes <= 0) return 0;

        const lastRunTimeMs = this.getLastRunMs(mergedConfig);
        if (lastRunTimeMs === 0) return 0;

        const nowMs = Date.now();
        let remainMs = (cdMinutes * 60 * 1000) - (nowMs - lastRunTimeMs);
        if (remainMs <= 0) return 0;

        if (mergedConfig.cooldown_reset_daily_utc) {
            const lastRunDate = new Date(lastRunTimeMs);
            const nextUtcResetMs = Date.UTC(
                lastRunDate.getUTCFullYear(),
                lastRunDate.getUTCMonth(),
                lastRunDate.getUTCDate() + 1,
                0, 0, 0, 0
            );
            remainMs = Math.min(remainMs, nextUtcResetMs - nowMs);
        }

        return Math.max(0, remainMs);
    }

    /**
     * Checks if an activity is currently on cooldown
     * @param {Object} mergedConfig - the output of ActivitySelectionPolicy.getMergedConfig
     * @returns {boolean} True if on cooldown
     */
    static isOnCooldown(mergedConfig) {
        return this.getRemainingMs(mergedConfig) > 0;
    }

    /**
     * Gets the remaining cooldown time in a presentable exact format
     * @param {Object} mergedConfig 
     * @returns {string} Formatted time string (e.g. "12m 30s") or empty if not on cooldown
     */
    static formatRemaining(mergedConfig) {
        if (!this.isOnCooldown(mergedConfig)) return '';

        const remainMs = this.getRemainingMs(mergedConfig);
        if (remainMs <= 0) return '';

        const h = Math.floor(remainMs / 3600000);
        const m = Math.floor(remainMs / 60000);
        const s = Math.floor((remainMs % 60000) / 1000);

        if (h > 0) return `${h}h ${m % 60}m`;
        return `${m}m ${s}s`;
    }

    /**
     * Gets the last run time in milliseconds
     * @param {Object} mergedConfig 
     * @returns {number} Epoch timestamp in ms, or 0 if never run
     */
    static getLastRunMs(mergedConfig) {
        if (!mergedConfig.last_run) return 0;
        return new Date(mergedConfig.last_run).getTime();
    }
}
