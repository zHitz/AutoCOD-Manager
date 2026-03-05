export class ActivitySelectionPolicy {
    /**
     * Determines which activities are currently enabled in the UI state
     * @param {Array} systemActivities - Registry of all valid activities
     * @param {Object} groupConfig - V2 config object for the group
     * @returns {Array} List of enabled activity objects
     */
    static pickEnabled(systemActivities, groupConfig) {
        if (!groupConfig || !groupConfig.activities) return [];

        return systemActivities
            .map(sys => {
                const actConf = groupConfig.activities[sys.id] || {};
                return {
                    id: sys.id,
                    name: sys.name,
                    description: sys.description,
                    enabled: !!actConf.enabled,
                    sysDefaults: sys.defaults || {},
                    configFields: sys.config_fields || []
                };
            })
            .filter(act => act.enabled);
    }

    /**
     * Helper to retrieve full merged config for an activity
     * @param {Object} activity - The activity definition from pickEnabled
     * @param {Object} groupConfig - V2 config object for the group 
     * @returns {Object} Merged config (defaults + user overrides + meta)
     */
    static getMergedConfig(activity, groupConfig) {
        const actConf = (groupConfig && groupConfig.activities && groupConfig.activities[activity.id]) || {};

        const defaults = { ...activity.sysDefaults };
        if (activity.configFields) {
            activity.configFields.forEach(f => {
                if (f.default !== undefined) defaults[f.key] = f.default;
            });
        }

        const userPayload = actConf.config || {};

        return {
            ...defaults,
            ...userPayload,
            cooldown_enabled: actConf.cooldown_enabled ?? defaults.cooldown_enabled,
            cooldown_minutes: actConf.cooldown_minutes ?? defaults.cooldown_minutes,
            last_run: actConf.last_run || null
        };
    }
}
