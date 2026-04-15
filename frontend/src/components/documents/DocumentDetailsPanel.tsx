import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import StatusBadge from '../common/StatusBadge';
import type { DocumentItem } from '../../types';

type Props = {
  document: DocumentItem | null;
};

export default function DocumentDetailsPanel({ document }: Props) {
  if (!document) {
    return (
      <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
        <Typography color="text.secondary">Select a document to see its details.</Typography>
      </Paper>
    );
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
        <Box>
          <Typography variant="h6" fontWeight={800}>
            {document.cnr_number || document.file_name}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {document.file_name}
          </Typography>

          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" alignItems="center" sx={{ mt: 1.5 }}>
            <Chip size="small" label={`Batch: ${document.batch_no || '-'}`} variant="outlined" />
            <Chip size="small" label={`Pages: ${document.page_count}`} variant="outlined" />
            <Chip size="small" label={`Vectorized: ${document.is_vectorized ? 'Yes' : 'No'}`} variant="outlined" />
            <Chip size="small" label={`Chat Ready: ${document.chat_ready ? 'Yes' : 'No'}`} variant="outlined" />
          </Stack>

          <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
            Current step: {document.current_step || '-'}
          </Typography>
        </Box>

        <Stack spacing={1} alignItems="flex-end">
          <StatusBadge status={document.status} />
        </Stack>
      </Stack>
    </Paper>
  );
}
