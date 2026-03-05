import { Result } from '../../../shared/result/Result.js';

export class ExecutionRepository {
    /**
     * @param {import('../../../shared/http/HttpClient.js').HttpClient} httpClient 
     */
    constructor(httpClient) {
        this.http = httpClient;
    }

    async run(payload) {
        // Payload typically contains: { emulator_index, steps, name }
        const response = await this.http.post('/api/workflow/run', payload);
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'accepted' || response.data?.status === 'ok') {
            return Result.ok(response.data);
        }

        return Result.fail(new Error(response.data?.message || 'Failed to run workflow'));
    }
}
