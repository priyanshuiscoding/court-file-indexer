import { useEffect, useMemo, useRef, useState } from 'react';
import Alert from '@mui/material/Alert';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import Snackbar from '@mui/material/Snackbar';
import Stack from '@mui/material/Stack';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Toolbar from '@mui/material/Toolbar';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import Drawer from '@mui/material/Drawer';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import UploadFileRoundedIcon from '@mui/icons-material/UploadFileRounded';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import TableRowsRoundedIcon from '@mui/icons-material/TableRowsRounded';
import PictureAsPdfRoundedIcon from '@mui/icons-material/PictureAsPdfRounded';
import SettingsRoundedIcon from '@mui/icons-material/SettingsRounded';
import ChatRoundedIcon from '@mui/icons-material/ChatRounded';

import { BACKEND_BASE_URL } from '../api/client';
import { deleteDocument, deleteDocumentsBulk, getDocument, listDocuments, uploadDocument, uploadDocumentBatch } from '../api/documents';
import { createIndexRow, deleteIndexRow, getIndexRows, manualScan, startIndexing, updateIndexRow } from '../api/indexing';
import { clearPendingQueue, getActiveQueue, getOpsStatus, recoverStaleQueue, restartDocumentProcessing, stopDocumentProcessing } from '../api/ops';
import { getDocumentPages } from '../api/pages';

import DocumentLibrary from '../components/documents/DocumentLibrary';
import DocumentDetailsPanel from '../components/documents/DocumentDetailsPanel';
import UploadPanel from '../components/documents/UploadPanel';
import SearchBar from '../components/documents/SearchBar';
import ManualScanPanel from '../components/indexing/ManualScanPanel';
import ReviewSummary from '../components/indexing/ReviewSummary';
import IndexRowTable from '../components/indexing/IndexRowTable';
import IndexEditorDrawer from '../components/indexing/IndexEditorDrawer';
import PdfViewerPanel from '../components/pdf/PdfViewerPanel';
import ChatPanel from '../components/chat/ChatPanel';
import OpsModal from '../components/ops/OpsModal';

import { useAppStore } from '../store/useAppStore';
import { useDocumentPolling } from '../hooks/useDocumentPolling';
import type { DocumentItem, IndexRow, OpsQueueItem } from '../types';

function statusTone(status?: string) {
  const s = (status || '').toUpperCase();
  if (s.includes('FAILED')) return 'error';
  if (s.includes('REVIEW')) return 'warning';
  if (s.includes('OCR') || s.includes('RUNNING') || s.includes('INDEXING')) return 'info';
  if (s.includes('INDEX') || s.includes('DONE') || s.includes('PARSED') || s.includes('READY')) return 'success';
  return 'default';
}

function extractApiError(error: unknown, fallback: string): string {
  const anyErr = error as any;
  return anyErr?.response?.data?.detail || anyErr?.message || fallback;
}

export default function DashboardPage() {
  const {
    documents,
    selectedDocument,
    indexRows,
    opsStatus,
    currentPdfPage,
    pdfJumpTarget,
    opsOpen,
    indexEditorOpen,
    activeRow,
    setDocuments,
    setSelectedDocument,
    setIndexRows,
    setDocumentPages,
    setOpsStatus,
    setCurrentPdfPage,
    setPdfJumpTarget,
    setOpsOpen,
    setIndexEditorOpen,
    setActiveRow,
    upsertRow
  } = useAppStore();

  const [loadingPage, setLoadingPage] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [opsBusy, setOpsBusy] = useState(false);
  const [activeQueue, setActiveQueue] = useState<OpsQueueItem[]>([]);
  const [leftTab, setLeftTab] = useState<'index' | 'chat'>('index');
  const [mobileLibraryOpen, setMobileLibraryOpen] = useState(false);
  const reviewWorkspaceRef = useRef<HTMLDivElement | null>(null);
  const hasOpsSnapshotRef = useRef(false);
  const prevQueueByIdRef = useRef<Map<number, OpsQueueItem>>(new Map());
  const prevFailedCountRef = useRef<number>(0);

  const [toast, setToast] = useState<{
    open: boolean;
    type: 'success' | 'error' | 'info';
    message: string;
  }>({
    open: false,
    type: 'success',
    message: ''
  });

  const selectedDocumentId = selectedDocument?.id;

  useDocumentPolling(selectedDocumentId, selectedDocument?.status);

  const selectedDocActiveJobs = useMemo(
    () =>
      activeQueue.filter(
        (q) =>
          q.document_id === selectedDocumentId &&
          (q.status === 'PENDING' || q.status === 'RUNNING') &&
          !q.is_stuck
      ),
    [activeQueue, selectedDocumentId]
  );

  const indexingCompleted = useMemo(() => {
    const s = (selectedDocument?.status || '').toUpperCase();
    return ['CHAT_READY', 'COMPLETED', 'APPROVED', 'REVIEW_REQUIRED'].includes(s);
  }, [selectedDocument?.status]);

  const indexStartDisabledReason = useMemo(() => {
    if (!selectedDocument) return 'Select a PDF first.';
    if (selectedDocActiveJobs.length > 0) return 'Indexing is already running for this PDF. Please wait or stop it from Operations.';
    if (indexingCompleted) return 'Indexing is already completed for this PDF.';
    return undefined;
  }, [selectedDocument, selectedDocActiveJobs.length, indexingCompleted]);

  const pdfUrl = useMemo(() => {
    if (!selectedDocumentId) return null;
    return `${BACKEND_BASE_URL}/api/v1/documents/${selectedDocumentId}/file`;
  }, [selectedDocumentId]);

  const showToast = (type: 'success' | 'error' | 'info', message: string) => {
    setToast({ open: true, type, message });
  };

  const refreshAll = async (keepDocumentId?: number) => {
    setLoadingPage(true);
    try {
      const [docs, ops, queue] = await Promise.all([listDocuments(), getOpsStatus(), getActiveQueue()]);
      setDocuments(docs);
      setOpsStatus(ops);
      setActiveQueue(queue);

      const targetId = keepDocumentId ?? selectedDocumentId ?? docs[0]?.id;
      if (targetId) {
        const [doc, rows, pages] = await Promise.all([
          getDocument(targetId),
          getIndexRows(targetId),
          getDocumentPages(targetId)
        ]);
        setSelectedDocument(doc);
        setIndexRows(rows);
        setDocumentPages(pages);
      } else {
        setSelectedDocument(null);
        setIndexRows([]);
        setDocumentPages([]);
      }
    } catch {
      showToast('error', 'Failed to refresh dashboard data.');
    } finally {
      setLoadingPage(false);
    }
  };

  const refreshOpsQueue = async () => {
    try {
      const [ops, queue] = await Promise.all([getOpsStatus(), getActiveQueue()]);
      setOpsStatus(ops);
      setActiveQueue(queue);
    } catch {
      showToast('error', 'Failed to refresh operations queue.');
    }
  };

  useEffect(() => {
    refreshAll();
  }, []);

  useEffect(() => {
    const fetchOpsAndQueue = async () => {
      try {
        const [ops, queue] = await Promise.all([getOpsStatus(), getActiveQueue()]);
        setOpsStatus(ops);
        setActiveQueue(queue);

        const currentById = new Map(queue.map((item) => [item.id, item]));
        if (!hasOpsSnapshotRef.current) {
          hasOpsSnapshotRef.current = true;
          prevQueueByIdRef.current = currentById;
          prevFailedCountRef.current = ops.failed_count;
          return;
        }

        const previousById = prevQueueByIdRef.current;
        const newlyStuck = queue.filter((item) => item.is_stuck && !previousById.get(item.id)?.is_stuck);
        const recovered = Array.from(previousById.values()).filter(
          (item) => item.is_stuck && !currentById.get(item.id)?.is_stuck
        );
        const retries = queue.filter((item) => {
          const prev = previousById.get(item.id);
          return !!prev && item.attempts > prev.attempts && item.status.toUpperCase() === 'RUNNING';
        });

        if (newlyStuck.length > 0) {
          showToast('error', `${newlyStuck.length} task(s) became stuck. Auto-recovery will attempt shortly.`);
        } else if (recovered.length > 0) {
          showToast('success', `${recovered.length} previously stuck task(s) recovered.`);
        } else if (retries.length > 0) {
          showToast('info', `${retries.length} task(s) auto-retried by queue recovery.`);
        } else if (ops.failed_count > prevFailedCountRef.current) {
          const delta = ops.failed_count - prevFailedCountRef.current;
          showToast('error', `${delta} document(s) moved to FAILED during recovery.`);
        }

        prevQueueByIdRef.current = currentById;
        prevFailedCountRef.current = ops.failed_count;
      } catch {
      }
    };

    fetchOpsAndQueue();
    const interval = setInterval(fetchOpsAndQueue, 12000);
    return () => clearInterval(interval);
  }, [setOpsStatus]);

  useEffect(() => {
    if (opsOpen) {
      refreshOpsQueue();
    }
  }, [opsOpen]);

  const handleSelectDocument = async (doc: DocumentItem) => {
    setSelectedDocument(doc);
    setCurrentPdfPage(1);
    setPdfJumpTarget(1);

    try {
      const [freshDoc, rows, pages] = await Promise.all([
        getDocument(doc.id),
        getIndexRows(doc.id),
        getDocumentPages(doc.id),
      ]);
      setSelectedDocument(freshDoc);
      setIndexRows(rows);
      setDocumentPages(pages);

      // If index exists, keep index workspace visible and jump PDF to first index page.
      if (rows.length > 0) {
        setLeftTab('index');
        const firstJumpPage = rows
          .map((r) => r.page_from || r.source_page_no || 1)
          .sort((a, b) => a - b)[0];
        setPdfJumpTarget(firstJumpPage);
        setCurrentPdfPage(firstJumpPage);

        setTimeout(() => {
          reviewWorkspaceRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 0);
      }
    } catch {
      showToast('error', 'Could not load selected document.');
    }
  };

  const handleUpload = async (file: File, cnr?: string, batchNo?: string) => {
    setActionBusy(true);
    try {
      const created = await uploadDocument(file, cnr, batchNo);
      await refreshAll(created.id);
      showToast('success', 'PDF uploaded successfully.');
    } catch {
      showToast('error', 'Upload failed.');
    } finally {
      setActionBusy(false);
    }
  };

  const handleBatchUpload = async (files: File[], batchNo?: string) => {
    setActionBusy(true);
    try {
      await uploadDocumentBatch(files, batchNo);
      await refreshAll();
      showToast('success', `Batch upload queued (${files.length} files).`);
    } catch (error) {
      showToast('error', extractApiError(error, 'Batch upload failed.'));
    } finally {
      setActionBusy(false);
    }
  };

  const handleDeleteSingleDocument = async (document: DocumentItem) => {
    const confirmed = window.confirm(`Delete ${document.file_name}? This will remove indexed rows, chat history, and vectors for this PDF.`);
    if (!confirmed) return;

    setActionBusy(true);
    try {
      await deleteDocument(document.id);
      const keepId = selectedDocumentId === document.id ? undefined : selectedDocumentId;
      await refreshAll(keepId);
      showToast('success', 'PDF deleted successfully.');
    } catch (error) {
      showToast('error', extractApiError(error, 'Failed to delete PDF.'));
    } finally {
      setActionBusy(false);
    }
  };

  const handleDeleteMultipleDocuments = async (documentIds: number[]) => {
    if (documentIds.length === 0) return;
    const confirmed = window.confirm(`Delete ${documentIds.length} selected PDF(s)? This cannot be undone.`);
    if (!confirmed) return;

    setActionBusy(true);
    try {
      const result = await deleteDocumentsBulk(documentIds);
      const selectedDeleted = selectedDocumentId != null && result.deleted_document_ids.includes(selectedDocumentId);
      await refreshAll(selectedDeleted ? undefined : selectedDocumentId);

      const activeCount = result.active_document_ids.length;
      if (activeCount > 0) {
        showToast('info', `Deleted ${result.deleted_count} PDF(s). ${activeCount} active PDF(s) were skipped.`);
      } else {
        showToast('success', `Deleted ${result.deleted_count} PDF(s).`);
      }
    } catch (error) {
      showToast('error', extractApiError(error, 'Failed to delete selected PDFs.'));
    } finally {
      setActionBusy(false);
    }
  };

  const handleSearch = async (params: { cnr?: string; batch_no?: string }) => {
    setLoadingPage(true);
    try {
      const docs = await listDocuments(params);
      setDocuments(docs);

      if (docs.length > 0) {
        await handleSelectDocument(docs[0]);
      } else {
        setSelectedDocument(null);
        setIndexRows([]);
        setDocumentPages([]);
        showToast('info', 'No matching documents found.');
      }
    } catch {
      showToast('error', 'Search failed.');
    } finally {
      setLoadingPage(false);
    }
  };

  const handleStartDefault = async () => {
    if (!selectedDocument) return;
    if (indexStartDisabledReason) {
      showToast('info', indexStartDisabledReason);
      return;
    }

    setActionBusy(true);
    try {
      await startIndexing(selectedDocument.id, { start_page: 1, end_page: 10 });
      showToast('success', 'Strict indexing started.');
      await refreshAll(selectedDocument.id);
    } catch (error) {
      showToast('error', extractApiError(error, 'Failed to start indexing.'));
    } finally {
      setActionBusy(false);
    }
  };

  const handleManualScan = async (startPage: number, endPage: number) => {
    if (!selectedDocument) return;
    if (indexStartDisabledReason) {
      showToast('info', indexStartDisabledReason);
      return;
    }

    setActionBusy(true);
    try {
      await manualScan(selectedDocument.id, { start_page: startPage, end_page: endPage });
      showToast('success', `Manual scan started for pages ${startPage}-${endPage}.`);
      await refreshAll(selectedDocument.id);
    } catch (error) {
      showToast('error', extractApiError(error, 'Manual scan failed.'));
    } finally {
      setActionBusy(false);
    }
  };

  const handleJump = (pageNo: number) => {
    setPdfJumpTarget(pageNo);
    setCurrentPdfPage(pageNo);
  };

  const handleEdit = (row: IndexRow) => {
    setActiveRow(row);
    setIndexEditorOpen(true);
  };

  const handleSaveRow = async (payload: Partial<IndexRow>) => {
    try {
      if (activeRow?.id && activeRow.id !== 0) {
        const updated = await updateIndexRow(activeRow.id, payload);
        upsertRow(updated);
      } else if (selectedDocument) {
        const created = await createIndexRow(selectedDocument.id, payload);
        upsertRow(created);
      }
      showToast('success', 'Row saved.');
    } catch {
      showToast('error', 'Failed to save row.');
    }
  };

  const handleDeleteRow = async (row: IndexRow) => {
    try {
      await deleteIndexRow(row.id);
      setIndexRows(indexRows.filter((r) => r.id !== row.id));
      showToast('success', 'Row deleted.');
    } catch {
      showToast('error', 'Failed to delete row.');
    }
  };

  const handleReorderRows = async (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return;

    const reordered = [...indexRows];
    const [movedRow] = reordered.splice(fromIndex, 1);
    reordered.splice(toIndex, 0, movedRow);

    const previousRowNoById = new Map(indexRows.map((row) => [row.id, row.row_no]));
    const normalizedRows = reordered.map((row, index) => ({ ...row, row_no: index + 1 }));

    setIndexRows(normalizedRows);

    try {
      const changedRows = normalizedRows.filter((row) => previousRowNoById.get(row.id) !== row.row_no);
      await Promise.all(changedRows.map((row) => updateIndexRow(row.id, { row_no: row.row_no })));
      showToast('success', 'Index row order updated.');
    } catch {
      showToast('error', 'Failed to persist row order. Reloading latest rows.');
      if (selectedDocument) {
        const freshRows = await getIndexRows(selectedDocument.id);
        setIndexRows(freshRows);
      }
    }
  };

  const handleStopSelected = async () => {
    if (!selectedDocument) return;
    setOpsBusy(true);
    try {
      await stopDocumentProcessing(selectedDocument.id);
      showToast('success', 'Stopped selected document processing.');
      await refreshAll(selectedDocument.id);
    } catch {
      showToast('error', 'Failed to stop selected document.');
    } finally {
      setOpsBusy(false);
    }
  };

  const handleRestartSelected = async () => {
    if (!selectedDocument) return;
    setOpsBusy(true);
    try {
      await restartDocumentProcessing(selectedDocument.id);
      showToast('success', 'Restarted selected document processing.');
      await refreshAll(selectedDocument.id);
    } catch {
      showToast('error', 'Failed to restart selected document.');
    } finally {
      setOpsBusy(false);
    }
  };

  const handleClearPendingQueue = async () => {
    setOpsBusy(true);
    try {
      const result = await clearPendingQueue();
      showToast('success', `Cleared ${result.affected} pending tasks.`);
      await refreshOpsQueue();
    } catch {
      showToast('error', 'Failed to clear pending queue.');
    } finally {
      setOpsBusy(false);
    }
  };

  const handleRecoverStaleQueue = async () => {
    setOpsBusy(true);
    try {
      const result = await recoverStaleQueue();
      showToast('info', result.message || 'Stale queue recovery triggered.');
      await refreshOpsQueue();
    } catch {
      showToast('error', 'Failed to trigger stale recovery.');
    } finally {
      setOpsBusy(false);
    }
  };

  const handleStopDocumentFromQueue = async (documentId: number) => {
    setOpsBusy(true);
    try {
      await stopDocumentProcessing(documentId);
      showToast('success', `Stopped document #${documentId}.`);
      await refreshAll(selectedDocumentId);
    } catch {
      showToast('error', `Failed to stop document #${documentId}.`);
    } finally {
      setOpsBusy(false);
    }
  };

  const reviewCount = indexRows.filter((r) => r.status === 'REVIEW').length;
  const autoOkCount = indexRows.filter((r) => r.status === 'AUTO_OK').length;
  const nextRowNo = useMemo(() => {
    if (indexRows.length === 0) return 1;
    return Math.max(...indexRows.map((r) => r.row_no ?? 0)) + 1;
  }, [indexRows]);

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f4f7fb' }}>
      <AppBar
        position="sticky"
        elevation={0}
        color="inherit"
        sx={{
          borderBottom: '1px solid #e5e7eb',
          bgcolor: 'rgba(255,255,255,0.92)',
          backdropFilter: 'blur(10px)'
        }}
      >
        <Toolbar sx={{ gap: 2, minHeight: 72 }}>
          <Stack direction="row" alignItems="center" spacing={1.5} sx={{ minWidth: 220 }}>
            <Box
              sx={{
                width: 38,
                height: 38,
                borderRadius: 2,
                bgcolor: '#e8f0ff',
                color: '#2f6bff',
                display: 'grid',
                placeItems: 'center',
                fontWeight: 800
              }}
            >
              CF
            </Box>
            <Box>
              <Typography variant="h6" fontWeight={800} lineHeight={1.1}>
                Court File Indexer
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Queue + review dashboard
              </Typography>
            </Box>
          </Stack>

          <Box sx={{ flex: 1 }} />

          <Stack direction="row" spacing={1} alignItems="center">
            {opsStatus ? (
              <>
                <Chip size="small" label={`Indexed ${opsStatus.indexed_count}`} color="success" variant="outlined" />
                <Chip size="small" label={`Review ${opsStatus.review_queue_count}`} color="warning" variant="outlined" />
                <Chip size="small" label={`Pending ${opsStatus.pending_queue_count}`} color="info" variant="outlined" />
              </>
            ) : null}

            <Button
              variant="outlined"
              startIcon={<SettingsRoundedIcon />}
              onClick={() => setOpsOpen(true)}
              sx={{ textTransform: 'none', borderRadius: 2 }}
            >
              Operations
            </Button>

            <Tooltip title="Refresh dashboard">
              <span>
                <IconButton onClick={() => refreshAll()} disabled={loadingPage || actionBusy}>
                  {loadingPage ? <CircularProgress size={18} /> : <RefreshRoundedIcon />}
                </IconButton>
              </span>
            </Tooltip>
          </Stack>
        </Toolbar>
      </AppBar>

      <Container maxWidth={false} sx={{ py: 2.5, px: { xs: 2, lg: 3 } }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', xl: 'minmax(0, 3fr) minmax(0, 2fr)' },
            gap: 2,
            height: { xl: 'calc(100vh - 120px)' },
            overflow: { xl: 'hidden' }
          }}
        >
          <Box
            sx={{
              minWidth: 0,
              height: { xl: 'calc(100vh - 120px)' },
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
              overflowY: { xl: 'auto' },
              pr: { xl: 1 }
            }}
          >
            <Paper
              variant="outlined"
              sx={{
                borderRadius: 3,
                p: 2,
                display: 'flex',
                flexDirection: 'column',
                gap: 2
              }}
            >
              <Box
                sx={{
                  p: 1.25,
                  borderRadius: 2,
                  border: '1px solid #e5e7eb',
                  bgcolor: '#f8fafc',
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr', xl: 'minmax(0, 1fr) minmax(0, 1fr)' },
                  gap: 1.5,
                  alignItems: 'start'
                }}
              >
                <Stack spacing={1} minWidth={0}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <UploadFileRoundedIcon fontSize="small" color="primary" />
                    <Typography fontWeight={700}>Upload</Typography>
                  </Stack>
                  <UploadPanel compact onUpload={handleUpload} onBatchUpload={handleBatchUpload} />
                </Stack>

                <Stack spacing={1} minWidth={0}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <SearchRoundedIcon fontSize="small" color="primary" />
                    <Typography fontWeight={700}>PDF Search</Typography>
                  </Stack>
                  <SearchBar onSearch={handleSearch} />
                </Stack>
              </Box>

              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr', xl: 'minmax(0, 1.35fr) minmax(0, 1fr)' },
                  gap: 2,
                  alignItems: 'stretch',
                  minHeight: { xl: 360 },
                }}
              >
                <Stack sx={{ minHeight: { xs: 340, xl: 360 } }}>
                  <DocumentLibrary
                    documents={documents}
                    selectedDocumentId={selectedDocument?.id}
                    onSelect={handleSelectDocument}
                    onDeleteSingle={handleDeleteSingleDocument}
                    onDeleteMultiple={handleDeleteMultipleDocuments}
                    deleting={actionBusy}
                    height="100%"
                  />
                </Stack>

                <Stack spacing={2}>
                  <ManualScanPanel
                    disabled={!selectedDocument || actionBusy || !!indexStartDisabledReason}
                    disabledReason={indexStartDisabledReason}
                    onStartDefault={handleStartDefault}
                    onManualScan={handleManualScan}
                  />
                  <ReviewSummary rows={indexRows} />
                  <DocumentDetailsPanel document={selectedDocument} />
                </Stack>
              </Box>
            </Paper>

            <Paper
              variant="outlined"
              ref={reviewWorkspaceRef}
              sx={{
                borderRadius: 3,
                overflow: 'hidden',
                bgcolor: 'background.paper',
                display: 'flex',
                flexDirection: 'column',
                minHeight: { xl: 460 },
                flexShrink: 0
              }}
            >
              <Box sx={{ px: 2, pt: 1.5, pb: 1 }}>
                <Stack
                  direction={{ xs: 'column', md: 'row' }}
                  justifyContent="space-between"
                  alignItems={{ xs: 'flex-start', md: 'center' }}
                  spacing={1}
                  mb={1}
                >
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <TableRowsRoundedIcon fontSize="small" color="primary" />
                    <Typography fontWeight={700}>Review workspace</Typography>
                  </Stack>

                  <Stack direction="row" spacing={1} alignItems="center">
                    <Chip size="small" label={`AUTO_OK ${autoOkCount}`} color="success" variant="outlined" />
                    <Chip size="small" label={`REVIEW ${reviewCount}`} color="warning" variant="outlined" />
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => {
                        if (!selectedDocument) return;
                        setActiveRow({
                          id: 0,
                          document_id: selectedDocument.id,
                          row_no: nextRowNo,
                          description_raw: '',
                          extraction_confidence: 0,
                          verification_confidence: 0,
                          status: 'REVIEW',
                          created_at: new Date().toISOString(),
                        } as IndexRow);
                        setIndexEditorOpen(true);
                      }}
                    >
                      Add Row
                    </Button>
                  </Stack>
                </Stack>

                <Tabs
                  value={leftTab}
                  onChange={(_, value) => setLeftTab(value)}
                  sx={{ minHeight: 40 }}
                >
                  <Tab value="index" label="Index Table" sx={{ textTransform: 'none', minHeight: 40 }} />
                  <Tab
                    value="chat"
                    icon={<ChatRoundedIcon sx={{ fontSize: 18 }} />}
                    iconPosition="start"
                    label="Document Chat"
                    sx={{ textTransform: 'none', minHeight: 40 }}
                  />
                </Tabs>
              </Box>

              <Divider />

              <Box sx={{ p: 2, overflowY: 'auto', minHeight: 0 }}>
                {leftTab === 'index' ? (
                  <IndexRowTable rows={indexRows} onJump={handleJump} onEdit={handleEdit} onDelete={handleDeleteRow} onReorder={handleReorderRows} />
                ) : (
                  <ChatPanel
                    documentId={selectedDocument?.id}
                    onJumpToPage={(page) => {
                      setPdfJumpTarget(page);
                      setCurrentPdfPage(page);
                    }}
                  />
                )}
              </Box>
            </Paper>
          </Box>

          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              borderRadius: 3,
              minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
              height: { xs: '70vh', xl: 'calc(100vh - 120px)' }
            }}
          >
            <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ px: 1, pb: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center">
                <PictureAsPdfRoundedIcon fontSize="small" color="primary" />
                <Typography fontWeight={700}>PDF preview</Typography>
              </Stack>

              {selectedDocument ? (
                <Stack direction="row" spacing={1} alignItems="center">
                  <Chip size="small" label={selectedDocument.file_name} variant="outlined" />
                  <Chip
                    size="small"
                    label={selectedDocument.status}
                    color={statusTone(selectedDocument.status) as any}
                  />
                </Stack>
              ) : null}
            </Stack>

            <Divider sx={{ mb: 1.5 }} />

            <Box sx={{ flex: 1, minHeight: 0 }}>
              <PdfViewerPanel
                fileUrl={pdfUrl}
                jumpPage={pdfJumpTarget}
                currentPage={currentPdfPage}
                onPageChange={setCurrentPdfPage}
              />
            </Box>
          </Paper>
        </Box>
      </Container>

      <IndexEditorDrawer
        open={indexEditorOpen}
        row={activeRow}
        onClose={() => {
          setIndexEditorOpen(false);
          setActiveRow(null);
        }}
        onSave={handleSaveRow}
      />

      <OpsModal
        open={opsOpen}
        onClose={() => setOpsOpen(false)}
        status={opsStatus}
        activeQueue={activeQueue}
        selectedDocumentId={selectedDocument?.id}
        busy={opsBusy}
        onStopSelected={handleStopSelected}
        onRestartSelected={handleRestartSelected}
        onRecoverStale={handleRecoverStaleQueue}
        onClearPending={handleClearPendingQueue}
        onStopDocument={handleStopDocumentFromQueue}
      />

      <Snackbar
        open={toast.open}
        autoHideDuration={3500}
        onClose={() => setToast((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setToast((prev) => ({ ...prev, open: false }))}
          severity={toast.type}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {toast.message}
        </Alert>
      </Snackbar>

      <Drawer
        anchor="left"
        open={mobileLibraryOpen}
        onClose={() => setMobileLibraryOpen(false)}
        sx={{ display: { xs: 'block', xl: 'none' } }}
      >
        <Box sx={{ width: 360, p: 2 }}>
          <DocumentLibrary
            documents={documents}
            selectedDocumentId={selectedDocument?.id}
            onSelect={(doc) => {
              handleSelectDocument(doc);
              setMobileLibraryOpen(false);
            }}
            onDeleteSingle={handleDeleteSingleDocument}
            onDeleteMultiple={handleDeleteMultipleDocuments}
            deleting={actionBusy}
          />
        </Box>
      </Drawer>
    </Box>
  );
}





