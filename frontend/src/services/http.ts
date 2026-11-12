/** Same-origin session requests. Session credentials never enter localStorage. */
export function apiFetch(input: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers);
  const csrf = document.cookie.split('; ').find(part => part.startsWith('bb_csrf='))?.slice(8);
  if (csrf && !['GET', 'HEAD'].includes((options.method || 'GET').toUpperCase())) {
    headers.set('X-CSRF-Token', decodeURIComponent(csrf));
  }
  return fetch(input, {...options, headers, credentials:'same-origin'}).then(response => {
    if (response.status === 401 && !input.startsWith('/api/auth/')) {
      window.dispatchEvent(new Event('bhashabridge:session-expired'));
    }
    return response;
  });
}

export async function apiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check the form and retry.');
  return data;
}
