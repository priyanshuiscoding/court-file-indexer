import { create } from 'zustand';
import type { ChatMessage, DocumentItem, DocumentPage, IndexRow, OpsStatus } from '../types';

type AppState = {
  documents: DocumentItem[];
  selectedDocument: DocumentItem | null;
  indexRows: IndexRow[];
  documentPages: DocumentPage[];
  opsStatus: OpsStatus | null;
  chatMessages: ChatMessage[];
  currentPdfPage: number;
  pdfJumpTarget: number | null;
  opsOpen: boolean;
  indexEditorOpen: boolean;
  activeRow: IndexRow | null;
  loadingDocuments: boolean;
  loadingRows: boolean;
  loadingPages: boolean;
  loadingChat: boolean;
  setDocuments: (documents: DocumentItem[]) => void;
  setSelectedDocument: (document: DocumentItem | null) => void;
  setIndexRows: (rows: IndexRow[]) => void;
  setDocumentPages: (pages: DocumentPage[]) => void;
  setOpsStatus: (status: OpsStatus | null) => void;
  setChatMessages: (messages: ChatMessage[]) => void;
  setCurrentPdfPage: (page: number) => void;
  setPdfJumpTarget: (page: number | null) => void;
  setOpsOpen: (open: boolean) => void;
  setIndexEditorOpen: (open: boolean) => void;
  setActiveRow: (row: IndexRow | null) => void;
  setLoadingDocuments: (value: boolean) => void;
  setLoadingRows: (value: boolean) => void;
  setLoadingPages: (value: boolean) => void;
  setLoadingChat: (value: boolean) => void;
  upsertRow: (row: IndexRow) => void;
};

export const useAppStore = create<AppState>((set) => ({
  documents: [],
  selectedDocument: null,
  indexRows: [],
  documentPages: [],
  opsStatus: null,
  chatMessages: [],
  currentPdfPage: 1,
  pdfJumpTarget: null,
  opsOpen: false,
  indexEditorOpen: false,
  activeRow: null,
  loadingDocuments: false,
  loadingRows: false,
  loadingPages: false,
  loadingChat: false,
  setDocuments: (documents) => set({ documents }),
  setSelectedDocument: (selectedDocument) => set({ selectedDocument }),
  setIndexRows: (indexRows) => set({ indexRows }),
  setDocumentPages: (documentPages) => set({ documentPages }),
  setOpsStatus: (opsStatus) => set({ opsStatus }),
  setChatMessages: (chatMessages) => set({ chatMessages }),
  setCurrentPdfPage: (currentPdfPage) => set({ currentPdfPage }),
  setPdfJumpTarget: (pdfJumpTarget) => set({ pdfJumpTarget }),
  setOpsOpen: (opsOpen) => set({ opsOpen }),
  setIndexEditorOpen: (indexEditorOpen) => set({ indexEditorOpen }),
  setActiveRow: (activeRow) => set({ activeRow }),
  setLoadingDocuments: (loadingDocuments) => set({ loadingDocuments }),
  setLoadingRows: (loadingRows) => set({ loadingRows }),
  setLoadingPages: (loadingPages) => set({ loadingPages }),
  setLoadingChat: (loadingChat) => set({ loadingChat }),
  upsertRow: (row) =>
    set((state) => {
      const exists = state.indexRows.some((r) => r.id === row.id);
      if (exists) {
        return { indexRows: state.indexRows.map((r) => (r.id === row.id ? row : r)) };
      }
      return { indexRows: [...state.indexRows, row].sort((a, b) => (a.row_no || 9999) - (b.row_no || 9999)) };
    })
}));
