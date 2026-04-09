import { useEffect, useMemo, useState } from 'react';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import StatusBadge from '../common/StatusBadge';
import type { DocumentItem } from '../../types';
import { formatDateTime, formatText } from '../../utils/format';

type Props = {
  documents: DocumentItem[];
  selectedDocumentId?: number;
  onSelect: (document: DocumentItem) => void;
  onDeleteSingle: (document: DocumentItem) => Promise<void>;
  onDeleteMultiple: (documentIds: number[]) => Promise<void>;
  deleting?: boolean;
};

export default function DocumentLibrary({
  documents,
  selectedDocumentId,
  onSelect,
  onDeleteSingle,
  onDeleteMultiple,
  deleting = false,
}: Props) {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  useEffect(() => {
    const validIds = new Set(documents.map((doc) => doc.id));
    setSelectedIds((prev) => prev.filter((id) => validIds.has(id)));
  }, [documents]);

  const selectedCount = selectedIds.length;
  const hasSelection = selectedCount > 0;

  const selectedIdSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  const toggleRow = (documentId: number) => {
    setSelectedIds((prev) => {
      if (prev.includes(documentId)) {
        return prev.filter((id) => id !== documentId);
      }
      return [...prev, documentId];
    });
  };

  const handleDeleteSelected = async () => {
    if (!hasSelection) return;
    await onDeleteMultiple(selectedIds);
    setSelectedIds([]);
  };

  return (
    <Paper variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden', height: 340 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ p: 1.5, borderBottom: '1px solid #eee', bgcolor: '#fbfdff' }}
      >
        <Typography variant="subtitle1" fontWeight={800}>
          Saved PDF Library
        </Typography>

        <Stack direction="row" spacing={1} alignItems="center">
          <Chip size="small" label={`${documents.length} files`} variant="outlined" />
          <Button
            size="small"
            color="error"
            variant="outlined"
            disabled={!hasSelection || deleting}
            onClick={handleDeleteSelected}
          >
            Delete Selected ({selectedCount})
          </Button>
        </Stack>
      </Stack>

      <List sx={{ maxHeight: 286, overflow: 'auto', p: 0 }}>
        {documents.map((doc) => (
          <ListItemButton
            key={doc.id}
            selected={doc.id === selectedDocumentId}
            onClick={() => onSelect(doc)}
            divider
            sx={{
              alignItems: 'flex-start',
              py: 1.25,
              '&.Mui-selected': {
                bgcolor: '#eef5ff'
              }
            }}
          >
            <Checkbox
              size="small"
              checked={selectedIdSet.has(doc.id)}
              onClick={(e) => e.stopPropagation()}
              onChange={() => toggleRow(doc.id)}
              sx={{ p: 0.5, mt: 0.25, mr: 1 }}
            />

            <ListItemText
              primary={doc.cnr_number || doc.file_name}
              secondary={`${formatText(doc.batch_no)} - ${doc.page_count} pages - ${formatDateTime(doc.created_at)}`}
              primaryTypographyProps={{ fontWeight: 700, fontSize: 14 }}
              secondaryTypographyProps={{ fontSize: 12 }}
            />

            <Stack direction="row" alignItems="center" spacing={0.5}>
              <StatusBadge status={doc.status} />
              <Tooltip title="Delete this PDF">
                <span>
                  <IconButton
                    size="small"
                    color="error"
                    disabled={deleting}
                    onClick={(e) => {
                      e.stopPropagation();
                      void onDeleteSingle(doc);
                    }}
                  >
                    <DeleteOutlineRoundedIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
            </Stack>
          </ListItemButton>
        ))}
      </List>
    </Paper>
  );
}
