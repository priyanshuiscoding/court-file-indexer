import { api } from './client';
import type { OpsQueueItem, OpsStatus, QueueActionResult } from '../types';

export async function getOpsStatus() {
  const { data } = await api.get<OpsStatus>('/ops/status');
  return data;
}

export async function getActiveQueue() {
  const { data } = await api.get<OpsQueueItem[]>('/ops/queue/active');
  return data;
}

export async function stopDocumentProcessing(documentId: number) {
  const { data } = await api.post<QueueActionResult>(`/ops/documents/${documentId}/stop`);
  return data;
}

export async function restartDocumentProcessing(documentId: number) {
  const { data } = await api.post<QueueActionResult>(`/ops/documents/${documentId}/restart`);
  return data;
}

export async function clearPendingQueue() {
  const { data } = await api.post<QueueActionResult>('/ops/queue/clear-pending');
  return data;
}
