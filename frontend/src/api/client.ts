export class ApiError extends Error {
  constructor(
    message: string,
    public status = 0,
    public code = 'network_error',
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(
  /\/+$/,
  '',
);
let accessToken: string | null = null;
export function setAccessToken(token: string | null) {
  accessToken = token;
}
type Options = Omit<RequestInit, 'body'> & { body?: unknown; timeout?: number };
export async function request<T>(path: string, options: Options = {}): Promise<T> {
  const { body, timeout = 30000, signal, ...rest } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new Error('timeout')), timeout);
  const combined = signal ? AbortSignal.any([signal, controller.signal]) : controller.signal;
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      signal: combined,
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...rest.headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status === 204) return undefined as T;
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 401 && accessToken)
        window.dispatchEvent(new Event('session-expired'));
      const validation = Array.isArray(payload?.error?.details)
        ? payload.error.details
            .map(
              (item: { loc?: string[]; msg?: string }) =>
                `${item.loc?.slice(1).join('.') || 'Input'}: ${item.msg || 'invalid'}`,
            )
            .join('; ')
        : '';
      throw new ApiError(
        validation ||
          payload?.error?.message ||
          (typeof payload?.detail === 'string' ? payload.detail : '') ||
          (response.status === 429
            ? 'Market data is temporarily rate limited. Please try again shortly.'
            : `The server returned an error (${response.status}).`),
        response.status,
        payload?.error?.code,
      );
    }
    if (payload === null)
      throw new ApiError(
        'The server returned an unreadable response.',
        response.status,
        'invalid_response',
      );
    return payload as T;
  } catch (error) {
    if (signal?.aborted) throw error;
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted)
      throw new ApiError('The request took too long. Please try again.', 0, 'timeout');
    throw new ApiError('Unable to reach the analysis server. Check your connection and try again.');
  } finally {
    clearTimeout(timer);
  }
}
export const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.';
