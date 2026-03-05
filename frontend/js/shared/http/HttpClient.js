export class HttpClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
    }

    async _request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;

        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                },
            });

            // Check if response is JSON
            const contentType = response.headers.get("content-type");
            const isJson = contentType && contentType.includes("application/json");

            const data = isJson ? await response.json() : await response.text();

            if (!response.ok) {
                // Return an error object that our repositories can handle
                return {
                    ok: false,
                    status: response.status,
                    error: isJson ? data : new Error(data || response.statusText)
                };
            }

            return { ok: true, data };
        } catch (error) {
            console.error(`[HttpClient] Request failed: ${url}`, error);
            return { ok: false, error };
        }
    }

    async get(endpoint, options = {}) {
        return this._request(endpoint, { ...options, method: 'GET' });
    }

    async post(endpoint, body, options = {}) {
        return this._request(endpoint, {
            ...options,
            method: 'POST',
            body: JSON.stringify(body),
        });
    }

    async put(endpoint, body, options = {}) {
        return this._request(endpoint, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(body),
        });
    }

    async delete(endpoint, options = {}) {
        return this._request(endpoint, { ...options, method: 'DELETE' });
    }
}
