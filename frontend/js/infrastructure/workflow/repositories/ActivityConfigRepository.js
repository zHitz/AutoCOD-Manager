import { Result } from '../../../shared/result/Result.js';

export class ActivityConfigRepository {
    /**
     * @param {import('../../../shared/http/HttpClient.js').HttpClient} httpClient 
     */
    constructor(httpClient) {
        this.http = httpClient;
        // Cache to store the system activity registry (read-only definitions)
        this._registryCache = [];
    }

    async getRegistry() {
        if (this._registryCache.length > 0) {
            return Result.ok(this._registryCache);
        }

        const response = await this.http.get('/api/workflow/activity-registry');
        if (!response.ok) {
            // Provide fallback if API is not available
            return Result.ok([
                { id: 'gather_rss_center', name: 'Gather Resource Center', defaults: {} },
                { id: 'gather_resource', name: 'Gather Resource', defaults: {}, config_fields: [{ key: 'resource_type', default: 'wood' }] },
                { id: 'full_scan', name: 'Full Scan', defaults: {} },
                { id: 'catch_pet', name: 'Catch Pet', defaults: {} }
            ]);
        }

        if (response.data?.status === 'success') {
            this._registryCache = response.data.data || [];
            return Result.ok(this._registryCache);
        }
        return Result.fail(new Error(response.data?.message || 'Failed to load activity registry'));
    }

    async loadConfig(groupId) {
        // Use cache bust timestamp to always get freshest from backend
        const response = await this.http.get(`/api/workflow/activity-config/${groupId}?t=${Date.now()}`);
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'ok' && response.data?.config) {
            return Result.ok(response.data.config);
        }

        return Result.fail(new Error(response.data?.error || 'Failed to load config'));
    }

    async saveConfig(groupId, configPayload) {
        const response = await this.http.post(`/api/workflow/activity-config/${groupId}`, configPayload);
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'ok') {
            return Result.ok(response.data);
        }

        return Result.fail(new Error(response.data?.error || 'Failed to save config'));
    }
}
