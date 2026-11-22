export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly requestId?: string) {
    super(message);
  }
}

/** Send credentials and the CSRF header only to this application's API. */
export async function apiFetch(input: string, options: RequestInit = {}) {
  if (!input.startsWith('/api/')) throw new Error('Invalid API path.');
  const method = (options.method || 'GET').toUpperCase();
  const read = method === 'GET' || method === 'HEAD';
  const headers = new Headers(options.headers);
  const csrf = document.cookie.split('; ').find(part => part.startsWith('bb_csrf='))?.slice(8);
  if (csrf && !read && /^[A-Za-z0-9_-]+$/.test(csrf)) {
    headers.set('X-CSRF-Token', decodeURIComponent(csrf));
  }
  const slowRead = input.startsWith('/api/arcade/stats/') || input === '/api/auth/export';
  const timeout = AbortSignal.timeout(read ? (slowRead ? 30_000 : 15_000) : 65_000);
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
  const canRetry = read && input !== '/api/auth/export';
  for (let attempt = 0; ; attempt++) {
    try {
      const response = await fetch(input, {...options, headers, signal, credentials:'same-origin', redirect:'error'});
      if (canRetry && attempt === 0 && [502, 503, 504].includes(response.status) &&
          !response.headers.has('Retry-After')) {
        await response.body?.cancel();
        continue;
      }
      const expectedAuthFailure = ['/api/auth/me', '/api/auth/login', '/api/auth/register', '/api/auth/account'].includes(input);
      if (response.status === 401 && !expectedAuthFailure) {
        window.dispatchEvent(new Event('bhashabridge:session-expired'));
      }
      return response;
    } catch (error) {
      if (options.signal?.aborted) throw error;
      if (timeout.aborted) throw new ApiError('The request timed out. Please retry.', 0);
      if (!canRetry || attempt > 0) throw new ApiError('Unable to reach the server. Please retry.', 0);
    }
  }
}

export async function apiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, options);
  const requestId = response.headers.get('X-Request-ID') ?? undefined;
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(
    typeof data?.detail === 'string' ? data.detail : 'The server could not complete the request.',
    response.status,
    requestId,
  );
  if (data === null) throw new ApiError('The server returned an invalid response. Please retry.', response.status, requestId);
  return data as T;
}
