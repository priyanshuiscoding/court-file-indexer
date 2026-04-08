import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';

type Props = {
  title: string;
  subtitle?: string;
};

export default function EmptyState({ title, subtitle }: Props) {
  return (
    <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
      <Typography variant="subtitle1" fontWeight={600}>{title}</Typography>
      {subtitle ? <Typography variant="body2" color="text.secondary" mt={1}>{subtitle}</Typography> : null}
    </Paper>
  );
}
