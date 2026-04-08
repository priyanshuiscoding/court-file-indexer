import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

type Props = {
  pageNumber: number;
  totalPages: number;
  onPrev: () => void;
  onNext: () => void;
  canPrev?: boolean;
  canNext?: boolean;
};

export default function PdfToolbar({ pageNumber, totalPages, onPrev, onNext, canPrev = true, canNext = true }: Props) {
  return (
    <Box
      sx={{
        px: 1.5,
        py: 1,
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        bgcolor: '#0b1730'
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography color="#cbd5e1" fontSize={13}>
          PDF Preview
        </Typography>

        <Stack direction="row" spacing={1} alignItems="center">
          <Chip size="small" label={`Page ${pageNumber} / ${totalPages || 0}`} color="primary" variant="filled" />
          <Button size="small" variant="outlined" onClick={onPrev} disabled={!canPrev}>Prev</Button>
          <Button size="small" variant="outlined" onClick={onNext} disabled={!canNext}>Next</Button>
        </Stack>
      </Stack>
    </Box>
  );
}
