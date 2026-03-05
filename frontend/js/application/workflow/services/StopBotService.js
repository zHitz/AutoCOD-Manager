import { Result } from '../../../shared/result/Result.js';

export class StopBotService {
    constructor({ botRepo }) {
        this.botRepo = botRepo;
    }

    async execute(groupId) {
        try {
            if (!groupId) {
                return Result.fail(new Error('Group ID is required to stop the bot.'));
            }

            const result = await this.botRepo.stop(groupId);

            if (!result.ok) {
                return Result.fail(result.error);
            }

            return Result.ok(result.data);

        } catch (error) {
            return Result.fail(error);
        }
    }
}
