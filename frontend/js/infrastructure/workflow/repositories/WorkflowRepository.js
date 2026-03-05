import { Result } from '../../../shared/result/Result.js';

export class WorkflowRepository {
    /**
     * @param {import('../../../shared/http/HttpClient.js').HttpClient} httpClient 
     */
    constructor(httpClient) {
        this.http = httpClient;
    }

    async getFunctions() {
        const response = await this.http.get('/api/workflow/functions');
        if (!response.ok) return Result.fail(response.error);

        // Backend usually returns { status: 'success', data: [...] }
        if (response.data?.status === 'success' || response.data?.status === 'ok') {
            return Result.ok(response.data.data);
        }
        return Result.fail(new Error(response.data?.message || 'Failed to load functions'));
    }

    async getTemplates() {
        const response = await this.http.get('/api/workflow/templates');
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'success' || response.data?.status === 'ok') {
            return Result.ok(response.data.data);
        }
        return Result.fail(new Error(response.data?.message || 'Failed to load templates'));
    }

    async getRecipes() {
        // Cache bust
        const response = await this.http.get(`/api/workflow/recipes?t=${Date.now()}`);
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'success' || response.data?.status === 'ok') {
            return Result.ok(response.data.data || []);
        }
        return Result.fail(new Error(response.data?.message || 'Failed to load recipes'));
    }

    async saveRecipe(recipeDto) {
        const response = await this.http.post('/api/workflow/recipes', recipeDto);
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'success' || response.data?.status === 'ok') {
            return Result.ok(response.data.data || response.data);
        }
        return Result.fail(new Error(response.data?.message || 'Failed to save recipe'));
    }

    async deleteRecipe(id) {
        const response = await this.http.delete(`/api/workflow/recipes/${id}`);
        if (!response.ok) return Result.fail(response.error);

        if (response.data?.status === 'success' || response.data?.status === 'ok') {
            return Result.ok(true);
        }
        return Result.fail(new Error(response.data?.message || 'Failed to delete recipe'));
    }
}
