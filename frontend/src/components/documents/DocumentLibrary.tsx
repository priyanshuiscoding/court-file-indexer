import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import StatusBadge from '../common/StatusBadge';
import type { DocumentItem } from '../../types';
import { formatDateTime, formatText } from '../../utils/format';

type Props = {
  documents: DocumentItem[];
  selectedDocumentId?: number;
  onSelect: (document: DocumentItem) => void;
};

export default function DocumentLibrary({ documents, selectedDocumentId, onSelect }: Props) {
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
        <Chip size="small" label={`${documents.length} files`} variant="outlined" />
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
            <ListItemText
              primary={doc.cnr_number || doc.file_name}
              secondary={`${formatText(doc.batch_no)} • ${doc.page_count} pages • ${formatDateTime(doc.created_at)}`}
              primaryTypographyProps={{ fontWeight: 700, fontSize: 14 }}
              secondaryTypographyProps={{ fontSize: 12 }}
            />
            <StatusBadge status={doc.status} />
          </ListItemButton>
        ))}
      </List>
    </Paper>
  );
}
