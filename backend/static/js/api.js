const BASE = '/api/v1';

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details || {};
  }
}

async function request(method, path, { params, body } = {}) {
  const url = new URL(BASE + path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v);
    });
  }

  const options = {
    method,
    credentials: 'same-origin',
    headers: { 'Accept': 'application/json' },
  };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(url, options);
  } catch (networkError) {
    throw new ApiError('Could not reach the server. Check your connection.', 0);
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch (_) {
  }

  if (!response.ok) {
    const err = payload && payload.error;
    if (response.status === 401) {
      throw new ApiError('Your session has expired. Please sign in again.', 401);
    }
    throw new ApiError(
      (err && err.message) || `Request failed (${response.status}).`,
      response.status,
      err && err.details
    );
  }
  return payload;
}

export const api = {
  get:   (path, params)     => request('GET', path, { params }),
  post:  (path, body)       => request('POST', path, { body }),
  patch: (path, body)       => request('PATCH', path, { body }),
};

export async function getPage(path, params) {
  return request('GET', path, { params });
}
