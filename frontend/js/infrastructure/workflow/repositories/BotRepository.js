import { Result } from '../../../shared/result/Result.js';

export class BotRepository {
    /**
     * @param {import('../../../shared/http/HttpClient.js').HttpClient} httpClient 
     */
    constructor(httpClient) {
        this.http = httpClient;
    }

    async start(payload) {
        const response = await this.http.post('/api/bot/run-sequential', payload);
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'ok' || response.data?.status === 'started') {
            return Result.ok(response.data);
        }

        // Handle explicit already_running case for business logic
        if (response.data?.status === 'already_running') {
            return Result.fail(new Error('ALREADY_RUNNING'));
        }

        return Result.fail(new Error(response.data?.error || 'Failed to start bot'));
    }

    async stop(groupId) {
        const response = await this.http.post('/api/bot/stop', { group_id: groupId });
        if (!response.ok) return Result.fail(response.error);

        if (
            response.data?.status === 'ok'
            || response.data?.status === 'stopping'
            || response.data?.status === 'not_running'
        ) {
            return Result.ok(response.data);
        }

        return Result.fail(new Error(response.data?.error || 'Failed to stop bot'));
    }

    async getStatus(groupId = null) {
        const url = groupId ? `/api/bot/status?group_id=${groupId}` : '/api/bot/status';
        const response = await this.http.get(url);

        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'ok') {
            return Result.ok(groupId ? response.data.data : response.data.groups);
        }
        if (response.data?.status === 'not_running') {
            return Result.ok(null);
        }

        return Result.fail(new Error(response.data?.error || 'Failed to fetch status'));
    }
}
