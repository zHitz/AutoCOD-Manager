import { Result } from '../../../shared/result/Result.js';

export class EmulatorRepository {
    /**
     * @param {import('../../../shared/http/HttpClient.js').HttpClient} httpClient 
     */
    constructor(httpClient) {
        this.http = httpClient;
    }

    async getAll() {
        const response = await this.http.get('/api/devices');
        if (!response.ok) return Result.fail(response.error);

        if (Array.isArray(response.data)) {
            return Result.ok(response.data);
        }
        return Result.fail(new Error(response.data?.error || 'Failed to load emulators'));
    }

    async getOnline() {
        const result = await this.getAll();
        if (!result.ok) return result;

        const online = result.data.filter(emu => emu.is_running === true);
        return Result.ok(online);
    }
}
