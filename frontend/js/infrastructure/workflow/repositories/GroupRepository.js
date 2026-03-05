import { Result } from '../../../shared/result/Result.js';

export class GroupRepository {
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

        const response = await this.http.get('/api/groups');
        if (!response.ok) return Result.fail(response.error);

        if (Array.isArray(response.data)) {
            this._cache = response.data;
            return Result.ok(this._cache);
        }
        return Result.fail(new Error(response.data?.message || 'Failed to load groups'));
    }

    async getById(id) {
        const result = await this.getAll();
        if (!result.ok) return result;

        const group = result.data.find(g => g.id === parseInt(id, 10));
        if (!group) return Result.fail(new Error(`Group ${id} not found`));
        return Result.ok(group);
    }

    async create(data) {
        const response = await this.http.post('/api/groups', data);
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'created' || response.data?.id) {
            this._cache = [];
            return Result.ok(response.data);
        }
        return Result.fail(new Error(response.data?.error || 'Failed to create group'));
    }

    async update(id, data) {
        const response = await this.http.put(`/api/groups/${id}`, data);
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'ok') {
            this._cache = [];
            return Result.ok(response.data);
        }
        return Result.fail(new Error(response.data?.error || 'Failed to update group'));
    }

    async delete(id) {
        const response = await this.http.delete(`/api/groups/${id}`);
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'deleted') {
            this._cache = [];
            return Result.ok(true);
        }
        return Result.fail(new Error(response.data?.error || 'Failed to delete group'));
    }
}
