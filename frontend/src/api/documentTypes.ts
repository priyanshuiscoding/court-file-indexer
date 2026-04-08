import { api } from './client';

export type SubDocumentTypeOption = {
  code: string;
  label: string;
};

export type DocumentTypeOption = {
  code: string;
  label: string;
  children: SubDocumentTypeOption[];
};

export async function getDocumentTypeHierarchy(): Promise<DocumentTypeOption[]> {
  const { data } = await api.get('/document-types/hierarchy');
  return data;
}
