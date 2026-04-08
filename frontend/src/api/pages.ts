import { api } from './client';
import type { DocumentPage } from '../types';

export async function getDocumentPages(documentId: number) {
  const { data } = await api.get<DocumentPage[]>(`/pages/${documentId}`);
  return data;
}
