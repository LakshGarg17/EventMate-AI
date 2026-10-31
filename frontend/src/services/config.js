/**
 * EventMate AI Frontend API Configuration
 * Enforces production base URL requirements and strips trailing slashes.
 */

const rawUrl = import.meta.env.VITE_API_BASE_URL;

let isMissingProdUrl = false;
let resolvedUrl = '';

if (import.meta.env.DEV) {
  resolvedUrl = (rawUrl && rawUrl.trim()) ? rawUrl.trim().replace(/\/+$/, '') : 'http://localhost:8000';
} else {
  if (!rawUrl || !rawUrl.trim()) {
    isMissingProdUrl = true;
    resolvedUrl = '';
  } else {
    resolvedUrl = rawUrl.trim().replace(/\/+$/, '');
  }
}

export const API_BASE_URL = resolvedUrl;
export const IS_MISSING_PROD_API_URL = isMissingProdUrl;

