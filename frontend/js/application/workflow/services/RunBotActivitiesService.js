import { Result } from '../../../shared/result/Result.js';
import { ActivitySelectionPolicy } from '../../../domain/workflow/policies/ActivitySelectionPolicy.js';
import { CooldownPolicy } from '../../../domain/workflow/policies/CooldownPolicy.js';
import { BotPayloadBuilder } from '../../../domain/workflow/policies/BotPayloadBuilder.js';

export class RunBotActivitiesService {
    constructor({ botRepo, configRepo, groupRepo, accountRepo }) {
        this.botRepo = botRepo;
        this.configRepo = configRepo;
        this.groupRepo = groupRepo;
        this.accountRepo = accountRepo;
    }

    async execute(groupId, systemActivities, startAccountId = null) {
        try {
            // 1. Load group config
            const configResult = await this.configRepo.loadConfig(groupId);
            if (!configResult.ok) return Result.fail(configResult.error);
            const groupConfig = configResult.data;

            // 2. Load group details to check if it has accounts (infrastructure)
            const groupResult = await this.groupRepo.getById(groupId);
            if (!groupResult.ok) return Result.fail(new Error('Group not found'));

            const groupData = groupResult.data;
            let accountsRaw = groupData.account_ids || '[]';
            let accountsArr = [];
            try { accountsArr = JSON.parse(accountsRaw) } catch (e) { }

            if (accountsArr.length === 0) {
                return Result.fail(new Error('This group has no accounts assigned.'));
            }

            // 3. Domain Logic: Pick Enabled
            const enabledActivities = ActivitySelectionPolicy.pickEnabled(systemActivities, groupConfig);
            if (enabledActivities.length === 0) {
                return Result.fail(new Error('NO_ACTIVITIES')); // We'll map this error code in UI
            }

            // 4. Domain Logic: No frontend cooldown check needed, backend orchestrator handles it per account
            const readyActivities = enabledActivities;
            const skippedLogs = [];

            // 5. Domain Logic: Build Payload
            const payload = BotPayloadBuilder.build(
                groupId,
                readyActivities,
                groupConfig,
                ActivitySelectionPolicy.getMergedConfig,
                startAccountId
            );

            // 6. Execute via repo
            const startResult = await this.botRepo.start(payload);

            if (!startResult.ok) {
                return Result.fail(startResult.error);
            }

            return Result.ok({
                response: startResult.data,
                skippedLogs: skippedLogs,
                readyActivities: readyActivities
            });

        } catch (error) {
            return Result.fail(error);
        }
    }
}
