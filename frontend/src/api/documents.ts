import { api } from './client';
import type { DocumentItem } from '../types';

export async function listDocuments(params?: { cnr?: string; batch_no?: string }) {
  const { data } = await api.get<DocumentItem[]>('/documents', { params });
  return data;
}

export async function getDocument(documentId: number) {
  const { data } = await api.get<DocumentItem>(`/documents/${documentId}`);
  return data;
}

export async function uploadDocument(file: File, cnr_number?: string, batch_no?: string) {
  const formData = new FormData();
  formData.append('file', file);
  if (cnr_number) formData.append('cnr_number', cnr_number);
  if (batch_no) formData.append('batch_no', batch_no);

  const { data } = await api.post<DocumentItem>('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return data;
}

export async function uploadDocumentBatch(files: File[], batchNo?: string) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  if (batchNo && batchNo.trim()) formData.append('batch_no', batchNo.trim());

  const { data } = await api.post('/documents/batch-upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600000,
  });
  return data;
}
