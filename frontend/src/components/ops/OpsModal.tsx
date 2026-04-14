import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Grid from '@mui/material/Grid2';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import type { OpsQueueItem, OpsStatus } from '../../types';

type Props = {
  open: boolean;
  onClose: () => void;
  status: OpsStatus | null;
  activeQueue: OpsQueueItem[];
  selectedDocumentId?: number;
  busy?: boolean;
  onStopSelected: () => void;
  onRestartSelected: () => void;
  onRecoverStale: () => void;
  onClearPending: () => void;
  onStopDocument: (documentId: number) => void;
};

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="h5" fontWeight={700}>{value}</Typography>
    </Paper>
  );
}

function queueTone(item: OpsQueueItem): 'default' | 'warning' | 'success' | 'error' | 'info' {
  if (item.is_stuck) return 'error';
  const s = item.status.toUpperCase();
  if (s === 'RUNNING') return 'info';
  if (s === 'PENDING') return 'warning';
  if (s === 'COMPLETED') return 'success';
  if (s === 'FAILED') return 'error';
  return 'default';
}

function queueLabel(item: OpsQueueItem): string {
  if (item.is_stuck) return 'STUCK';
  return item.status;
}

export default function OpsModal({
  open,
  onClose,
  status,
  activeQueue,
  selectedDocumentId,
  busy,
  onStopSelected,
  onRestartSelected,
  onRecoverStale,
  onClearPending,
  onStopDocument,
}: Props) {
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>Operations Panel</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} mt={0.5}>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><StatCard label="Indexed" value={status?.indexed_count || 0} /></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><StatCard label="Vectorized" value={status?.vectorized_count || 0} /></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><StatCard label="Pending Queue" value={status?.pending_queue_count || 0} /></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><StatCard label="Review Queue" value={status?.review_queue_count || 0} /></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><StatCard label="Failed" value={status?.failed_count || 0} /></Grid>
        </Grid>

        <Stack direction="row" spacing={1} mt={2.5} mb={2}>
          <Button variant="outlined" color="error" disabled={!selectedDocumentId || busy} onClick={onStopSelected}>
            Stop Selected
          </Button>
          <Button variant="outlined" disabled={!selectedDocumentId || busy} onClick={onRestartSelected}>
            Restart Selected
          </Button>
          <Button variant="outlined" color="info" disabled={busy} onClick={onRecoverStale}>
            Recover Stale
          </Button>
          <Button variant="outlined" color="warning" disabled={busy} onClick={onClearPending}>
            Clear Pending Queue
          </Button>
        </Stack>

        <Typography variant="subtitle2" fontWeight={700} mb={1}>
          Active Queue ({activeQueue.length})
        </Typography>
        <Paper variant="outlined" sx={{ p: 1.25, borderRadius: 2, maxHeight: 320, overflow: 'auto' }}>
          {activeQueue.length === 0 ? (
            <Typography variant="body2" color="text.secondary">No active tasks right now.</Typography>
          ) : (
            <Stack spacing={1}>
              {activeQueue.map((q) => (
                <Stack key={q.id} direction="row" justifyContent="space-between" alignItems="center">
                  <Stack>
                    <Typography variant="body2" fontWeight={600}>
                      {q.document_name || `Doc #${q.document_id}`} - {q.queue_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      DocStatus: {q.document_status || '-'} | Task: {q.task_id?.slice(0, 8) || '-'} | Attempts: {q.attempts} | Heartbeat age: {q.stale_seconds ?? '-'}s
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Chip size="small" label={queueLabel(q)} color={queueTone(q)} variant="outlined" />
                    <Button
                      size="small"
                      color="error"
                      variant="outlined"
                      disabled={busy}
                      onClick={() => onStopDocument(q.document_id)}
                    >
                      Stop This
                    </Button>
                  </Stack>
                </Stack>
              ))}
            </Stack>
          )}
        </Paper>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
