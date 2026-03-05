export class ExecutionLogRepository {
    constructor(httpClient) {
        this.http = httpClient;
    }

    async getRunHistory(filters = {}) {
        // Prepare query params if needed
        const queryParams = new URLSearchParams(filters).toString();
        const url = queryParams ? `/api/execution/runs?${queryParams}` : '/api/execution/runs';
        return this.http.get(url);
    }

    async getRunDetail(runId) {
        if (!runId) throw new Error("runId is required");
        return this.http.get(`/api/execution/runs/${runId}`);
    }
}
