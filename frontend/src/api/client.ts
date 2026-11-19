import axios from 'axios';

export const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
export const BACKEND_URL = API_BASE_URL.replace(/\/api\/v1\/?$/, '');

/**
 * Resolves a media attachment path (e.g. `/static/uploads/uuid.png`) into a fully qualified,
 * browser-accessible URL against the active backend server host.
 */
export function resolveMediaUrl(path?: string | null): string {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:') || path.startsWith('blob:')) {
    return path;
  }
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${BACKEND_URL}${cleanPath}`;
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('dirs_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
