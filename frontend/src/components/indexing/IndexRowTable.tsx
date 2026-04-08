import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import type { IndexRow } from '../../types';
import { formatPercent, formatText } from '../../utils/format';

type Props = {
  rows: IndexRow[];
  onJump: (pageNo: number) => void;
  onEdit: (row: IndexRow) => void;
  onDelete?: (row: IndexRow) => void;
};

function statusColor(status: string) {
  return status === 'REVIEW' ? 'warning' : 'success';
}

export default function IndexRowTable({ rows, onJump, onEdit, onDelete }: Props) {
  return (
    <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3, maxHeight: 560 }}>
      <Table stickyHeader size="small">
        <TableHead>
          <TableRow>
            <TableCell>#</TableCell>
            <TableCell>Description</TableCell>
            <TableCell>Annexure</TableCell>
            <TableCell>Pages</TableCell>
            <TableCell>Mapped Type</TableCell>
            <TableCell>Ext</TableCell>
            <TableCell>Ver</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Action</TableCell>
          </TableRow>
        </TableHead>

        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={9}>
                <Typography color="text.secondary">No index rows available yet.</Typography>
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => {
              const pageLabel =
                row.page_from != null
                  ? `${row.page_from}${row.page_to != null ? `-${row.page_to}` : ''}`
                  : '-';

              const jumpPage = row.page_from || row.source_page_no || 1;

              return (
                <TableRow
                  key={row.id}
                  hover
                  onClick={() => onJump(jumpPage)}
                  sx={{ cursor: 'pointer', '&:hover': { bgcolor: '#f8fbff' } }}
                >
                  <TableCell>{row.row_no || '-'}</TableCell>

                  <TableCell sx={{ maxWidth: 380 }}>
                    <Tooltip title={row.description_raw || '-'}>
                      <Typography variant="body2" sx={{ whiteSpace: 'normal' }}>
                        {row.description_raw || '-'}
                      </Typography>
                    </Tooltip>
                  </TableCell>

                  <TableCell>{formatText(row.annexure_no)}</TableCell>
                  <TableCell>{pageLabel}</TableCell>
                  <TableCell>{formatText(row.mapped_document_type)}</TableCell>
                  <TableCell>{formatPercent(row.extraction_confidence)}</TableCell>
                  <TableCell>{formatPercent(row.verification_confidence)}</TableCell>

                  <TableCell>
                    <Chip
                      size="small"
                      label={row.status}
                      color={statusColor(row.status) as any}
                      variant={row.status === 'REVIEW' ? 'filled' : 'outlined'}
                    />
                  </TableCell>

                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Button size="small" variant="text" onClick={() => onJump(jumpPage)} sx={{ mr: 1 }}>
                      Jump
                    </Button>
                    <Button size="small" variant="outlined" onClick={() => onEdit(row)} sx={{ mr: 1 }}>
                      Edit
                    </Button>
                    {onDelete ? (
                      <Button size="small" color="error" variant="text" onClick={() => onDelete(row)}>
                        Delete
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
