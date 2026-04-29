import { api } from './client';
import type {
  HighCourtImportItemResult,
  HighCourtImportJob,
  HighCourtJobListResponse,
  HighCourtResultResponse,
  HighCourtSchedulerStatus,
} from '../types';

export async function getHighCourtJobs(params?: { status?: string; limit?: number; offset?: number }) {
  const { data } = await api.get<HighCourtJobListResponse>('/high-court/import-jobs', { params });
  return data;
}

export async function triggerHighCourtImport(limit: number) {
  const { data } = await api.post('/high-court/import-pending', { limit });
  return data;
}

export async function syncHighCourtStatuses() {
  const { data } = await api.post('/high-court/import-jobs/sync-status');
  return data;
}

export async function retryHighCourtJob(batchNo: string) {
  const { data } = await api.post<HighCourtImportItemResult>('/high-court/import-jobs/retry', {
    batch_no: batchNo,
  });
  return data;
}

export async function getHighCourtResult(batchNo: string) {
  const { data } = await api.get<HighCourtResultResponse>(`/high-court/result/${batchNo}`);
  return data;
}

export async function markHighCourtCompleted(batchNo: string) {
  const { data } = await api.post('/high-court/mark-completed', { batch_no: batchNo });
  return data;
}

export async function getHighCourtSchedulerStatus() {
  const { data } = await api.get<HighCourtSchedulerStatus>('/high-court/scheduler/status');
  return data;
}

export async function runHighCourtImportNow() {
  const { data } = await api.post('/high-court/scheduler/run-import-now');
  return data;
}

export async function runHighCourtSyncNow() {
  const { data } = await api.post('/high-court/scheduler/run-sync-now');
  return data;
}

export async function runHighCourtMarkCompletedNow() {
  const { data } = await api.post('/high-court/scheduler/run-mark-completed-now');
  return data;
}

export async function getHighCourtJob(batchNo: string) {
  const { data } = await api.get<HighCourtImportJob>(`/high-court/import-jobs/${batchNo}`);
  return data;
}
