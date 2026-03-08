export class BotPayloadBuilder {
    /**
     * Builds the final payload for the /api/bot/run-sequential endpoint
     * @param {number|string} groupId 
     * @param {Array} readyActivities - List of activities that are enabled and NOT on cooldown
     * @param {Object} groupConfig - Full v2 group config
     * @param {Function} getMergedConfigFn - Usually ActivitySelectionPolicy.getMergedConfig
     * @param {number|null} startAccountId - ID of the account to run first
     * @returns {Object} Payload dictionary ready to be JSON encoded
     */
    static build(groupId, readyActivities, groupConfig, getMergedConfigFn, startAccountId = null) {
        const activitiesPayload = readyActivities.map(act => {
            const perCfg = getMergedConfigFn(act, groupConfig);

            // Strip out cooldown meta-fields when sending to executor payload
            const executorCfg = { ...perCfg };
            delete executorCfg.last_run; // Backend will query DB for this

            return {
                id: act.id,
                name: act.name,
                config: executorCfg
            };
        });

        // Parse misc setting defaults
        const defaultMisc = { cooldown_min: 30, limit_min: 45 };
        const misc = (groupConfig && groupConfig.misc) ? { ...defaultMisc, ...groupConfig.misc } : defaultMisc;

        const payloadObj = {
            group_id: parseInt(groupId, 10),
            activities: activitiesPayload,
            misc: misc
        };

        if (startAccountId) {
            payloadObj.start_account_id = startAccountId;
        }

        return payloadObj;
    }
}
