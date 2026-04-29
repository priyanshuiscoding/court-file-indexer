import { useEffect, useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Link from '@mui/material/Link';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Snackbar from '@mui/material/Snackbar';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import dayjs from 'dayjs';

import { BACKEND_BASE_URL } from '../api/client';
import {
  getHighCourtJobs,
  getHighCourtResult,
  getHighCourtSchedulerStatus,
  markHighCourtCompleted,
  retryHighCourtJob,
  runHighCourtImportNow,
  runHighCourtMarkCompletedNow,
  runHighCourtSyncNow,
  syncHighCourtStatuses,
  triggerHighCourtImport,
} from '../api/highCourt';
import type { HighCourtImportJob, HighCourtResultResponse, HighCourtSchedulerStatus } from '../types';

const STATUS_OPTIONS = [
  'ALL',
  'DISCOVERED',
  'PDF_FOUND',
  'QUEUED',
  'PROCESSING',
  'INDEX_READY',
  'CHAT_READY',
  'REVIEW_REQUIRED',
  'FAILED',
  'PDF_NOT_FOUND',
  'DOCUMENT_FAILED',
  'EXTERNAL_UPDATE_FAILED',
  'EXTERNAL_COMPLETED',
  'SKIPPED_DUPLICATE',
];

function statusColor(status: string): 'default' | 'error' | 'warning' | 'info' | 'success' | 'secondary' {
  const s = (status || '').toUpperCase();
  if (['FAILED', 'PDF_NOT_FOUND', 'DOCUMENT_FAILED', 'EXTERNAL_UPDATE_FAILED'].includes(s)) return 'error';
  if (s === 'QUEUED') return 'warning';
  if (s === 'PROCESSING' || s === 'PDF_FOUND') return 'info';
  if (['INDEX_READY', 'CHAT_READY', 'EXTERNAL_COMPLETED'].includes(s)) return 'success';
  if (s === 'REVIEW_REQUIRED') return 'secondary';
  return 'default';
}

function toErrorMessage(error: unknown, fallback: string): string {
  const e = error as any;
  return e?.response?.data?.detail || e?.message || fallback;
}

export default function HighCourtImportPage() {
  const [jobs, setJobs] = useState<HighCourtImportJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [limit, setLimit] = useState(100);
  const [scheduler, setScheduler] = useState<HighCourtSchedulerStatus | null>(null);
  const [schedulerOpen, setSchedulerOpen] = useState(false);
  const [jsonOpen, setJsonOpen] = useState(false);
  const [jsonPayload, setJsonPayload] = useState<HighCourtResultResponse | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<{ open: boolean; message: string; type: 'success' | 'error' | 'info' }>({
    open: false,
    message: '',
    type: 'info',
  });

  const showToast = (type: 'success' | 'error' | 'info', message: string) => setToast({ open: true, type, message });

  const loadJobs = async () => {
    setLoading(true);
    try {
      const data = await getHighCourtJobs({
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        limit,
        offset: 0,
      });
      setJobs(data.jobs || []);
    } catch (error) {
      showToast('error', toErrorMessage(error, 'Failed to load jobs'));
    } finally {
      setLoading(false);
    }
  };

  const loadScheduler = async () => {
    try {
      const data = await getHighCourtSchedulerStatus();
      setScheduler(data);
    } catch (error) {
      showToast('error', toErrorMessage(error, 'Failed to load scheduler status'));
    }
  };

  useEffect(() => {
    loadJobs();
    loadScheduler();
  }, [statusFilter, limit]);

  const counts = useMemo(() => {
    const c = {
      total: jobs.length,
      queued: 0,
      processing: 0,
      ready: 0,
      failed: 0,
      pdfNotFound: 0,
      externalCompleted: 0,
    };
    for (const job of jobs) {
      const s = (job.status || '').toUpperCase();
      if (s === 'QUEUED') c.queued += 1;
      if (s === 'PROCESSING') c.processing += 1;
      if (['INDEX_READY', 'CHAT_READY', 'REVIEW_REQUIRED'].includes(s)) c.ready += 1;
      if (['FAILED', 'DOCUMENT_FAILED', 'EXTERNAL_UPDATE_FAILED'].includes(s)) c.failed += 1;
      if (s === 'PDF_NOT_FOUND') c.pdfNotFound += 1;
      if (s === 'EXTERNAL_COMPLETED') c.externalCompleted += 1;
    }
    return c;
  }, [jobs]);

  const runAction = async (key: string, fn: () => Promise<void>) => {
    setActionLoading(key);
    try {
      await fn();
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <Container maxWidth={false} sx={{ py: 3 }}>
      <Stack spacing={2}>
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }}>
          <Typography variant="h5" fontWeight={800}>High Court Import Dashboard</Typography>
          <Link href="/" underline="hover">Back to Main Dashboard</Link>
        </Stack>

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(7, 1fr)' }, gap: 1.5 }}>
          {[
            ['Total Loaded', counts.total],
            ['Queued', counts.queued],
            ['Processing', counts.processing],
            ['Ready', counts.ready],
            ['Failed', counts.failed],
            ['PDF Not Found', counts.pdfNotFound],
            ['External Completed', counts.externalCompleted],
          ].map(([label, value]) => (
            <Card key={String(label)} variant="outlined">
              <CardContent sx={{ py: 1.5 }}>
                <Typography variant="caption" color="text.secondary">{label}</Typography>
                <Typography variant="h6">{value}</Typography>
              </CardContent>
            </Card>
          ))}
        </Box>

        <Paper variant="outlined" sx={{ p: 1.5 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.2}>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>Status</InputLabel>
              <Select value={statusFilter} label="Status" onChange={(e) => setStatusFilter(e.target.value)}>
                {STATUS_OPTIONS.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Limit</InputLabel>
              <Select value={limit} label="Limit" onChange={(e) => setLimit(Number(e.target.value))}>
                {[25, 50, 100, 200, 500].map((n) => <MenuItem key={n} value={n}>{n}</MenuItem>)}
              </Select>
            </FormControl>

            <Button variant="outlined" disabled={!!actionLoading} onClick={() => loadJobs()}>Refresh</Button>
            <Button
              variant="contained"
              disabled={!!actionLoading}
              onClick={() => runAction('import', async () => {
                const res = await triggerHighCourtImport(limit);
                showToast('info', `Import triggered. fetched=${res.fetched ?? 0}, queued=${res.queued ?? 0}`);
                await loadJobs();
              })}
            >
              {actionLoading === 'import' ? <CircularProgress size={18} /> : 'Import Pending'}
            </Button>
            <Button
              variant="contained"
              color="secondary"
              disabled={!!actionLoading}
              onClick={() => runAction('sync', async () => {
                const res = await syncHighCourtStatuses();
                showToast('info', `Sync done. checked=${res.checked ?? 0}, updated=${res.updated ?? 0}`);
                await loadJobs();
              })}
            >
              {actionLoading === 'sync' ? <CircularProgress size={18} /> : 'Sync Status'}
            </Button>
            <Button variant="outlined" disabled={!!actionLoading} onClick={() => setSchedulerOpen(true)}>Scheduler Status</Button>
            <Button
              variant="outlined"
              disabled={!!actionLoading}
              onClick={() => runAction('import-now', async () => {
                const res = await runHighCourtImportNow();
                showToast('success', `Import task queued: ${res.task_id}`);
              })}
            >
              Run Import Now
            </Button>
            <Button
              variant="outlined"
              disabled={!!actionLoading}
              onClick={() => runAction('sync-now', async () => {
                const res = await runHighCourtSyncNow();
                showToast('success', `Sync task queued: ${res.task_id}`);
              })}
            >
              Run Sync Now
            </Button>
            <Button
              variant="outlined"
              disabled={!!actionLoading}
              onClick={() => runAction('mark-now', async () => {
                const res = await runHighCourtMarkCompletedNow();
                showToast('info', res.task_id ? `Mark-completed task queued: ${res.task_id}` : 'Mark-completed request sent');
              })}
            >
              Run Mark Completed Now
            </Button>
          </Stack>
        </Paper>

        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Batch No</TableCell>
                <TableCell>Fil No</TableCell>
                <TableCell>External Row ID</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Document ID</TableCell>
                <TableCell>Attempts</TableCell>
                <TableCell>Source PDF Path</TableCell>
                <TableCell>Error</TableCell>
                <TableCell>Updated At</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={10}><Stack alignItems="center" py={2}><CircularProgress size={24} /></Stack></TableCell></TableRow>
              ) : jobs.length === 0 ? (
                <TableRow><TableCell colSpan={10}><Typography py={2} textAlign="center" color="text.secondary">No jobs found</Typography></TableCell></TableRow>
              ) : jobs.map((job) => {
                const st = (job.status || '').toUpperCase();
                const canRetry = ['FAILED', 'PDF_NOT_FOUND'].includes(st);
                const canView = ['INDEX_READY', 'CHAT_READY', 'REVIEW_REQUIRED', 'EXTERNAL_COMPLETED'].includes(st);
                const canMark = ['INDEX_READY', 'CHAT_READY', 'REVIEW_REQUIRED'].includes(st);
                return (
                  <TableRow key={job.id} hover>
                    <TableCell>{job.batch_no}</TableCell>
                    <TableCell>{job.fil_no || '-'}</TableCell>
                    <TableCell>{job.external_row_id || '-'}</TableCell>
                    <TableCell><Chip size="small" color={statusColor(job.status)} label={job.status} /></TableCell>
                    <TableCell>{job.document_id ?? '-'}</TableCell>
                    <TableCell>{job.import_attempts}</TableCell>
                    <TableCell sx={{ maxWidth: 260 }}>
                      {job.source_pdf_path ? (
                        <Tooltip title={job.source_pdf_path}>
                          <Typography noWrap variant="body2">{job.source_pdf_path}</Typography>
                        </Tooltip>
                      ) : '-'}
                    </TableCell>
                    <TableCell sx={{ maxWidth: 220 }}>
                      {job.error_message ? (
                        <Tooltip title={job.error_message}>
                          <Typography noWrap color="error.main" variant="body2">{job.error_message}</Typography>
                        </Tooltip>
                      ) : '-'}
                    </TableCell>
                    <TableCell>{dayjs(job.updated_at).format('YYYY-MM-DD HH:mm:ss')}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        <Button
                          size="small"
                          disabled={!canRetry || !!actionLoading}
                          onClick={() => runAction(`retry-${job.id}`, async () => {
                            const res = await retryHighCourtJob(job.batch_no);
                            showToast('info', `Retry status: ${res.status}`);
                            await loadJobs();
                          })}
                        >
                          Retry
                        </Button>
                        <Button
                          size="small"
                          disabled={!canView || !!actionLoading}
                          onClick={() => runAction(`view-${job.id}`, async () => {
                            const res = await getHighCourtResult(job.batch_no);
                            setJsonPayload(res);
                            setJsonOpen(true);
                          })}
                        >
                          View JSON
                        </Button>
                        <Button
                          size="small"
                          color="secondary"
                          disabled={!canMark || !!actionLoading}
                          onClick={() => runAction(`mark-${job.id}`, async () => {
                            const ok = window.confirm(`Mark batch ${job.batch_no} as completed in external MySQL?`);
                            if (!ok) return;
                            const res = await markHighCourtCompleted(job.batch_no);
                            showToast(res.ok ? 'success' : 'info', `${res.local_status || res.status}: ${res.mysql?.message || res.message || ''}`);
                            await loadJobs();
                          })}
                        >
                          Mark Completed
                        </Button>
                        {job.document_id ? (
                          <Button
                            size="small"
                            component={Link}
                            href={`${BACKEND_BASE_URL}/api/v1/documents/${job.document_id}/file`}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Open Document
                          </Button>
                        ) : null}
                      </Stack>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Stack>

      <Dialog open={schedulerOpen} onClose={() => setSchedulerOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Scheduler Status</DialogTitle>
        <DialogContent>
          {!scheduler ? (
            <Typography>Unable to load scheduler status.</Typography>
          ) : (
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {JSON.stringify(scheduler, null, 2)}
            </pre>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSchedulerOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={jsonOpen} onClose={() => setJsonOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>Result JSON</DialogTitle>
        <DialogContent>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {JSON.stringify(jsonPayload, null, 2)}
          </pre>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setJsonOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

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
    </Container>
  );
}
