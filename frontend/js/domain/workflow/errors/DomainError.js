export class DomainError extends Error {
    /**
     * @param {string} code - The string code representing the error type
     * @param {string} message - Human readable error message
     */
    constructor(code, message) {
        super(message);
        this.name = 'DomainError';
        this.code = code;
    }
}
