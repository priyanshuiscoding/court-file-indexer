import { api } from './client';
import type { IndexRow } from '../types';

export async function startIndexing(documentId: number, payload?: { start_page?: number; end_page?: number; reindex?: boolean }) {
  const { data } = await api.post(`/indexing/${documentId}/start`, payload || {});
  return data;
}

export async function manualScan(documentId: number, payload: { start_page: number; end_page: number }) {
  const { data } = await api.post(`/indexing/${documentId}/manual-scan`, payload);
  return data;
}

export async function getIndexRows(documentId: number) {
  const { data } = await api.get<IndexRow[]>(`/indexing/${documentId}/rows`);
  return data;
}

export async function createIndexRow(documentId: number, payload: Partial<IndexRow>) {
  const { data } = await api.post<IndexRow>(`/indexing/${documentId}/rows`, payload);
  return data;
}

export async function updateIndexRow(rowId: number, payload: Partial<IndexRow>) {
  const { data } = await api.put<IndexRow>(`/indexing/rows/${rowId}`, payload);
  return data;
}

export async function deleteIndexRow(rowId: number) {
  const { data } = await api.delete(`/indexing/rows/${rowId}`);
  return data;
}
