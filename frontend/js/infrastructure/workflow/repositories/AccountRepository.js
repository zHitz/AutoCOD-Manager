import { Result } from '../../../shared/result/Result.js';

export class AccountRepository {
    /**
     * @param {import('../../../shared/http/HttpClient.js').HttpClient} httpClient 
     */
    constructor(httpClient) {
        this.http = httpClient;
        // In-memory cache for fast lookups
        this._cache = [];
    }

    async getAll(forceRefresh = false) {
        if (!forceRefresh && this._cache.length > 0) {
            return Result.ok(this._cache);
        }

        const response = await this.http.get('/api/accounts');
        if (!response.ok) return Result.fail(response.error);

        if (Array.isArray(response.data)) {
            this._cache = response.data;
            return Result.ok(this._cache);
        }
        return Result.fail(new Error(response.data?.message || 'Failed to load accounts'));
    }

    async getByIds(ids) {
        const result = await this.getAll();
        if (!result.ok) return result;

        const idSet = new Set(ids.map(id => parseInt(id, 10)));
        const accounts = result.data.filter(a => idSet.has(a.account_id));
        return Result.ok(accounts);
    }
}
