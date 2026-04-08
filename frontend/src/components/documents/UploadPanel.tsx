import { useState } from 'react';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

type Props = {
  onUpload: (file: File, cnr?: string, batchNo?: string) => Promise<void>;
  onBatchUpload?: (files: File[], batchNo?: string) => Promise<void>;
};

export default function UploadPanel({ onUpload, onBatchUpload }: Props) {
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

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
      <Typography variant="subtitle1" fontWeight={800} mb={1.5}>
        Upload PDF
      </Typography>

      <Stack spacing={1.5}>
        <Button variant="outlined" component="label" sx={{ textTransform: 'none', borderRadius: 2 }}>
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
        />

        <TextField
          label="Batch No"
          size="small"
          value={batchNo}
          onChange={(e) => setBatchNo(e.target.value)}
          helperText="Optional for batch upload. If empty, system will auto-generate one."
        />

        <Button
          variant="contained"
          disabled={!file || uploading}
          onClick={handleUpload}
          sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 700 }}
        >
          {uploading ? 'Uploading...' : 'Upload PDF'}
        </Button>

        {onBatchUpload ? (
          <>
            <Button variant="outlined" component="label" sx={{ textTransform: 'none', borderRadius: 2 }}>
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
              disabled={!batchFiles.length || uploading}
              onClick={handleBatchUpload}
              sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 700 }}
            >
              {uploading ? 'Uploading...' : 'Batch Upload'}
            </Button>
          </>
        ) : null}
      </Stack>
    </Paper>
  );
}
