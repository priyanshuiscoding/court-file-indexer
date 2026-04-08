import { api as client } from './client';

export type ChatHistoryMessage = {
  id: number;
  role: 'user' | 'assistant';
  message: string;
  created_at?: string | null;
};

export type ChatSource = {
  page_no: number;
  text: string;
  score?: number;
};

export type ChatAnswer = {
  answer: string;
  sources: ChatSource[];
};

export async function getChatHistory(documentId: number): Promise<ChatHistoryMessage[]> {
  const { data } = await client.get(`/chat/${documentId}/history`);
  return data;
}

export async function askChat(documentId: number, question: string): Promise<ChatAnswer> {
  const { data } = await client.post(`/chat/${documentId}/ask`, { question });
  return data;
}

// Backward compatibility
export async function askDocumentChat(documentId: number, question: string): Promise<ChatAnswer> {
  return askChat(documentId, question);
}

export async function getChatStatus(documentId: number) {
  const { data } = await client.get<{ document_id: number; ready: boolean }>(`/chat/${documentId}/status`);
  return data;
}
