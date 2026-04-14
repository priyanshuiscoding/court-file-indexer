import { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Drawer from '@mui/material/Drawer';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import type { IndexRow } from '../../types';
import DocumentTypeSelector from './DocumentTypeSelector';

type Props = {
  open: boolean;
  row: IndexRow | null;
  onClose: () => void;
  onSave: (payload: Partial<IndexRow>) => Promise<void>;
};

export default function IndexEditorDrawer({ open, row, onClose, onSave }: Props) {
  const [form, setForm] = useState<Partial<IndexRow>>({});
  const [docSelection, setDocSelection] = useState<{
    document_code: string | null;
    sub_document_code: string | null;
    other: string;
  }>({
    document_code: null,
    sub_document_code: null,
    other: ''
  });

  useEffect(() => {
    setForm(row || {});
    setDocSelection({
      document_code: row?.mapped_document_type || null,
      sub_document_code: row?.mapped_sub_document_type || null,
      other: ''
    });
  }, [row]);

  const updateField = (key: keyof IndexRow, value: string | number | null) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const parseNullableInt = (value: string): number | null => {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Number.parseInt(trimmed, 10);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const handleSave = async () => {
    const payload: Partial<IndexRow> = {
      ...form,
      mapped_document_type: docSelection.document_code || form.mapped_document_type || null,
      mapped_sub_document_type: docSelection.sub_document_code || form.mapped_sub_document_type || null,
    };

    if (docSelection.other.trim()) {
      payload.receiving_date = docSelection.other.trim();
    }

    await onSave(payload);
    onClose();
  };

  return (
    <Drawer anchor="left" open={open} onClose={onClose}>
      <Box sx={{ width: 420, p: 3 }}>
        <Typography variant="h6" fontWeight={700} mb={2}>Edit Index Row</Typography>
        <Stack spacing={2}>
          <TextField
            label="Serial No"
            type="number"
            value={form.row_no ?? ''}
            onChange={(e) => updateField('row_no', parseNullableInt(e.target.value))}
          />
          <TextField label="Description" multiline minRows={3} value={form.description_raw || ''} onChange={(e) => updateField('description_raw', e.target.value)} />
          <TextField label="Annexure No" value={form.annexure_no || ''} onChange={(e) => updateField('annexure_no', e.target.value)} />
          <Stack direction="row" spacing={2}>
            <TextField label="Page From" type="number" fullWidth value={form.page_from ?? ''} onChange={(e) => updateField('page_from', parseNullableInt(e.target.value))} />
            <TextField label="Page To" type="number" fullWidth value={form.page_to ?? ''} onChange={(e) => updateField('page_to', parseNullableInt(e.target.value))} />
          </Stack>

          <DocumentTypeSelector
            documentCode={docSelection.document_code}
            subDocumentCode={docSelection.sub_document_code}
            other={docSelection.other}
            onChange={setDocSelection}
          />

          <TextField label="Status" value={form.status || ''} onChange={(e) => updateField('status', e.target.value)} />
          <Stack direction="row" spacing={2}>
            <Button variant="outlined" fullWidth onClick={onClose}>Cancel</Button>
            <Button variant="contained" fullWidth onClick={handleSave}>Save</Button>
          </Stack>
        </Stack>
      </Box>
    </Drawer>
  );
}
