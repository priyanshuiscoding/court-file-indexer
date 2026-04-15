import { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

type Props = {
  onUpload: (file: File, cnr?: string, batchNo?: string) => Promise<void>;
  onBatchUpload?: (files: File[], batchNo?: string) => Promise<void>;
  compact?: boolean;
};

export default function UploadPanel({ onUpload, onBatchUpload, compact = false }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [batchFiles, setBatchFiles] = useState<File[]>([]);
  const [cnr, setCnr] = useState('');
  const [batchNo, setBatchNo] = useState('');
  const [uploading, setUploading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      await onUpload(file, cnr || undefined, batchNo || undefined);
      setFile(null);
      setCnr('');
      setBatchNo('');
    } finally {
      setUploading(false);
    }
  };

  const handleBatchUpload = async () => {
    if (!onBatchUpload || !batchFiles.length) return;
    setUploading(true);
    try {
      await onBatchUpload(batchFiles, batchNo || undefined);
      setBatchFiles([]);
      setBatchNo('');
    } finally {
      setUploading(false);
    }
  };

  const compactFieldSx = { '& .MuiOutlinedInput-root': { bgcolor: '#f8fafc', minHeight: 40 } };
  const actionButtonSx = { textTransform: 'none', borderRadius: 2, minHeight: 40, minWidth: 120, fontWeight: 700 };

  const content = (
    <Stack spacing={compact ? 1 : 1.5}>
      {!compact ? (
        <Typography variant="subtitle1" fontWeight={800} mb={0.5}>
          Upload PDF
        </Typography>
      ) : null}

      <Box
        display="grid"
        gridTemplateColumns={{
          xs: '1fr',
          md: compact ? '1fr 1fr' : '1fr',
          xl: compact ? '160px minmax(160px,1fr) minmax(150px,1fr) 130px 180px 130px' : '1fr'
        }}
        gap={1}
        alignItems="center"
      >
        <Button
          variant="outlined"
          component="label"
          size="small"
          sx={{ ...actionButtonSx, fontWeight: 600, minWidth: 150 }}
        >
          {file ? file.name : 'Choose PDF'}
          <input
            hidden
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </Button>

        <TextField
          label="CNR Number"
          size="small"
          value={cnr}
          onChange={(e) => setCnr(e.target.value)}
          sx={compact ? compactFieldSx : { minWidth: 160 }}
        />

        <TextField
          label="Batch No"
          size="small"
          value={batchNo}
          onChange={(e) => setBatchNo(e.target.value)}
          helperText={compact ? undefined : "Optional for batch upload. If empty, system will auto-generate one."}
          sx={compact ? compactFieldSx : { minWidth: 140 }}
        />

        <Button
          variant="contained"
          size="small"
          disabled={!file || uploading}
          onClick={handleUpload}
          sx={actionButtonSx}
        >
          {uploading ? 'Uploading...' : 'Upload PDF'}
        </Button>

        {onBatchUpload ? (
          <>
            <Button
              variant="outlined"
              component="label"
              size="small"
              sx={{ ...actionButtonSx, minWidth: 170, fontWeight: 600 }}
            >
              {batchFiles.length ? `${batchFiles.length} files selected` : 'Choose Batch PDFs'}
              <input
                hidden
                type="file"
                multiple
                accept="application/pdf"
                onChange={(e) => setBatchFiles(Array.from(e.target.files || []))}
              />
            </Button>
            <Button
              variant="contained"
              size="small"
              disabled={!batchFiles.length || uploading}
              onClick={handleBatchUpload}
              sx={actionButtonSx}
            >
              {uploading ? 'Uploading...' : 'Batch Upload'}
            </Button>
          </>
        ) : null}
      </Box>
      {!compact ? (
        <Typography variant="caption" color="text.secondary">
          Optional batch number groups uploads under one batch.
        </Typography>
      ) : null}
    </Stack>
  );

  if (compact) {
    return content;
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
      {content}
    </Paper>
  );
}
