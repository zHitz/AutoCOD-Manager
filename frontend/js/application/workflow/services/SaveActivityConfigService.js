import { Result } from '../../../shared/result/Result.js';

export class SaveActivityConfigService {
    constructor({ configRepo }) {
        this.configRepo = configRepo;
    }

    async execute(groupId, configPayload) {
        try {
            if (!groupId) {
                return Result.fail(new Error('Group ID is required to save config.'));
            }

            // The repository handles the actual saving logic
            const result = await this.configRepo.saveConfig(groupId, configPayload);

            if (!result.ok) {
                return Result.fail(result.error);
            }

            return Result.ok(result.data);

        } catch (error) {
            return Result.fail(error);
        }
    }
}
