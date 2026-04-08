import { useEffect } from 'react';
import { getDocument } from '../api/documents';
import { getIndexRows } from '../api/indexing';
import { getDocumentPages } from '../api/pages';
import { useAppStore } from '../store/useAppStore';

export function useDocumentPolling(documentId?: number) {
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
    const interval = setInterval(fetchData, 5000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [documentId, setSelectedDocument, setIndexRows, setDocumentPages]);
}
