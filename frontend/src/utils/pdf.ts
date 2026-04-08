import { BACKEND_BASE_URL } from '../api/client';

export function buildPdfUrl(documentPath?: string | null) {
  if (!documentPath) return null;
  if (documentPath.startsWith('http')) return documentPath;
  return null;
}

export function buildStaticFileUrl(path?: string | null) {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  return `${BACKEND_BASE_URL}${path}`;
}
