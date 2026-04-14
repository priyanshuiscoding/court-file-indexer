import { useEffect } from 'react';
import { getDocument } from '../api/documents';
import { getIndexRows } from '../api/indexing';
import { getDocumentPages } from '../api/pages';
import { useAppStore } from '../store/useAppStore';

const ACTIVE_DOC_STATUSES = new Set([
  'UPLOADED',
  'OCR_RUNNING',
  'INDEX_SEARCH_RUNNING',
  'VECTORIZING',
  'VERIFYING',
  'FAST_INDEX_RUNNING',
  'INDEX_READY',
]);

export function useDocumentPolling(documentId?: number, documentStatus?: string) {
  const setSelectedDocument = useAppStore((s) => s.setSelectedDocument);
  const setIndexRows = useAppStore((s) => s.setIndexRows);
  const setDocumentPages = useAppStore((s) => s.setDocumentPages);

  useEffect(() => {
    if (!documentId) return;

    let mounted = true;

    const fetchData = async () => {
      try {
        const [doc, rows, pages] = await Promise.all([
          getDocument(documentId),
          getIndexRows(documentId),
          getDocumentPages(documentId)
        ]);

        if (!mounted) return;
        setSelectedDocument(doc);
        setIndexRows(rows);
        setDocumentPages(pages);
      } catch {
      }
    };

    fetchData();
    const normalizedStatus = (documentStatus || '').toUpperCase();
    const pollMs = ACTIVE_DOC_STATUSES.has(normalizedStatus) ? 5000 : 15000;
    const interval = setInterval(() => {
      // Avoid hammering API and UI rerenders when tab is not visible.
      if (typeof document !== 'undefined' && document.hidden) return;
      fetchData();
    }, pollMs);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [documentId, documentStatus, setSelectedDocument, setIndexRows, setDocumentPages]);
}
