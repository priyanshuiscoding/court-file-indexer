import { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

type Props = {
  disabled?: boolean;
  disabledReason?: string;
  onStartDefault: () => Promise<void>;
  onManualScan: (startPage: number, endPage: number) => Promise<void>;
};

export default function ManualScanPanel({ disabled, disabledReason, onStartDefault, onManualScan }: Props) {
  const [startPage, setStartPage] = useState(1);
  const [endPage, setEndPage] = useState(10);
  const [loading, setLoading] = useState(false);

  const handleDefault = async () => {
    setLoading(true);
    try {
      await onStartDefault();
    } finally {
      setLoading(false);
    }
  };

  const handleManual = async () => {
    if (startPage < 1 || endPage < startPage) return;
    setLoading(true);
    try {
      await onManualScan(startPage, endPage);
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = !!disabled || loading;

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        borderRadius: 3,
        bgcolor: '#f8fbff',
        borderColor: '#dbe7ff'
      }}
    >
      <Typography variant="subtitle1" fontWeight={800} mb={1}>
        Index scan controls
      </Typography>

      <Typography variant="body2" color="text.secondary" mb={disabledReason ? 0.75 : 2}>
        Default scan starts strict indexing for the first 10 pages. Manual scan lets you choose a page window.
      </Typography>

      {disabledReason ? (
        <Typography variant="body2" color="error" mb={2}>
          {disabledReason}
        </Typography>
      ) : null}

      <Stack spacing={1.5}>
        <Button
          variant="contained"
          size="large"
          disabled={isDisabled}
          onClick={handleDefault}
          sx={{ borderRadius: 2, textTransform: 'none', fontWeight: 700 }}
        >
          {loading ? 'Starting…' : 'Start Strict Indexing (Pages 1–10)'}
        </Button>

        <Box display="grid" gridTemplateColumns={{ xs: '1fr', md: '1fr 1fr auto' }} gap={1.5}>
          <TextField
            type="number"
            size="small"
            label="Start Page"
            value={startPage}
            onChange={(e) => setStartPage(Number(e.target.value))}
            disabled={isDisabled}
          />
          <TextField
            type="number"
            size="small"
            label="End Page"
            value={endPage}
            onChange={(e) => setEndPage(Number(e.target.value))}
            disabled={isDisabled}
          />
          <Button
            variant="outlined"
            disabled={isDisabled}
            onClick={handleManual}
            sx={{ borderRadius: 2, textTransform: 'none', fontWeight: 700 }}
          >
            Manual Scan
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
}
