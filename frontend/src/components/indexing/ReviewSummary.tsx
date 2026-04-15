import Chip from '@mui/material/Chip';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { IndexRow } from '../../types';

type Props = {
  rows: IndexRow[];
};

export default function ReviewSummary({ rows }: Props) {
  const reviewCount = rows.filter((row) => row.status === 'REVIEW').length;
  const autoOkCount = rows.filter((row) => row.status === 'AUTO_OK').length;
  const generatedCount = rows.filter((row) => row.generated_from_content).length;

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={1.5}
        flexWrap="wrap"
        alignItems={{ xs: 'flex-start', sm: 'center' }}
      >
        <Typography fontWeight={700}>Review Summary</Typography>
        <Chip size="small" label={`Total Rows: ${rows.length}`} variant="outlined" />
        <Chip size="small" label={`Review: ${reviewCount}`} color="warning" variant="outlined" />
        <Chip size="small" label={`Auto OK: ${autoOkCount}`} color="success" variant="outlined" />
        <Chip size="small" label={`Generated Fallback: ${generatedCount}`} color="default" variant="outlined" />
      </Stack>
    </Paper>
  );
}
