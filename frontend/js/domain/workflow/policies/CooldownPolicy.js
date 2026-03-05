export class CooldownPolicy {
    /**
     * Checks if an activity is currently on cooldown
     * @param {Object} mergedConfig - the output of ActivitySelectionPolicy.getMergedConfig
     * @returns {boolean} True if on cooldown
     */
    static isOnCooldown(mergedConfig) {
        if (!mergedConfig.cooldown_enabled) return false;

        const cdMinutes = mergedConfig.cooldown_minutes || 0;
        if (cdMinutes <= 0) return false;

        const lastRunTimeMs = this.getLastRunMs(mergedConfig);
        if (lastRunTimeMs === 0) return false;

        const elapsedMs = Date.now() - lastRunTimeMs;
        return elapsedMs < cdMinutes * 60 * 1000;
    }

    /**
     * Gets the remaining cooldown time in a presentable exact format
     * @param {Object} mergedConfig 
     * @returns {string} Formatted time string (e.g. "12m 30s") or empty if not on cooldown
     */
    static formatRemaining(mergedConfig) {
        if (!this.isOnCooldown(mergedConfig)) return '';

        const cdMinutes = mergedConfig.cooldown_minutes || 0;
        const lastRunTimeMs = this.getLastRunMs(mergedConfig);

        const remainMs = (cdMinutes * 60 * 1000) - (Date.now() - lastRunTimeMs);
        if (remainMs <= 0) return '';

        const m = Math.floor(remainMs / 60000);
        const s = Math.floor((remainMs % 60000) / 1000);

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
