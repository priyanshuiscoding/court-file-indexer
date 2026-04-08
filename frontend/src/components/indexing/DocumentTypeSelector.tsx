import { useEffect, useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import type { DocumentTypeOption } from '../../api/documentTypes';
import { getDocumentTypeHierarchy } from '../../api/documentTypes';

type Props = {
  documentCode?: string | null;
  subDocumentCode?: string | null;
  other?: string;
  onChange: (value: {
    document_code: string | null;
    sub_document_code: string | null;
    other: string;
  }) => void;
};

export default function DocumentTypeSelector({
  documentCode,
  subDocumentCode,
  other = '',
  onChange
}: Props) {
  const [options, setOptions] = useState<DocumentTypeOption[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getDocumentTypeHierarchy()
      .then((rows) => {
        if (active) setOptions(rows);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const selectedParent = useMemo(
    () => options.find((item) => item.code === documentCode) || null,
    [options, documentCode]
  );

  const subOptions = selectedParent?.children || [];

  return (
    <Box display="grid" gridTemplateColumns="1fr" gap={1.5}>
      <TextField
        select
        size="small"
        label="Document"
        value={documentCode || ''}
        onChange={(e) =>
          onChange({
            document_code: e.target.value || null,
            sub_document_code: null,
            other
          })
        }
        SelectProps={{
          MenuProps: {
            PaperProps: {
              style: {
                maxHeight: 380
              }
            }
          }
        }}
        disabled={loading}
      >
        <MenuItem value="">Select</MenuItem>
        {options.map((item) => (
          <MenuItem key={item.code} value={item.code}>
            {item.label} ({item.code})
          </MenuItem>
        ))}
      </TextField>

      <TextField
        select
        size="small"
        label="Sub Document"
        value={subDocumentCode || ''}
        onChange={(e) =>
          onChange({
            document_code: documentCode || null,
            sub_document_code: e.target.value || null,
            other
          })
        }
        disabled={!documentCode || loading}
        SelectProps={{
          MenuProps: {
            PaperProps: {
              style: {
                maxHeight: 380
              }
            }
          }
        }}
      >
        <MenuItem value="">Select</MenuItem>
        {subOptions.map((item) => (
          <MenuItem key={item.code} value={item.code}>
            {item.label} ({item.code})
          </MenuItem>
        ))}
      </TextField>

      <TextField
        size="small"
        label="Other"
        value={other}
        onChange={(e) =>
          onChange({
            document_code: documentCode || null,
            sub_document_code: subDocumentCode || null,
            other: e.target.value
          })
        }
        placeholder="Additional details..."
      />
    </Box>
  );
}
