export class Result {
    /**
     * Creates a successful Result with optional data.
     * @param {*} data 
     * @returns {Result}
     */
    static ok(data) {
        return new Result({ ok: true, data });
    }

    /**
     * Creates a failed Result with an error message or object.
     * @param {*} error 
     * @returns {Result}
     */
    static fail(error) {
        return new Result({ ok: false, error });
    }

    constructor({ ok, data, error }) {
        this.ok = ok;
        this.data = data;
        this.error = error;

        // Frozen to prevent mutation (functional pattern)
        Object.freeze(this);
    }
}
