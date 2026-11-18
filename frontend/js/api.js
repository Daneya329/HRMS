/* Small fetch wrapper for the JSON API. Throws ApiError with field errors on failure. */
class ApiError extends Error {
    constructor(status, message, errors) {
        super(message);
        this.status = status;
        this.errors = errors || {};
    }
}

async function api(method, url, body) {
    const options = { method, headers: { Accept: 'application/json' }, credentials: 'same-origin' };
    if (body !== undefined) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }
    let response;
    try {
        response = await fetch(url, options);
    } catch (e) {
        throw new ApiError(0, 'Cannot reach the server. Is the application running?');
    }
    let data = {};
    try { data = await response.json(); } catch (e) { /* empty body */ }
    const onLoginPage = ['/', '/login'].includes(window.location.pathname);
    if (response.status === 401 && !onLoginPage) {
        window.location.href = '/login';
        throw new ApiError(401, data.message || 'Please sign in');
    }
    if (!response.ok) {
        throw new ApiError(response.status, data.message || 'Request failed', data.errors);
    }
    return data;
}

let rulesCache = null;
async function loadRules() {
    if (!rulesCache) rulesCache = await api('GET', '/api/rules');
    return rulesCache;
}
