import Chip from '@mui/material/Chip';

type Props = {
  status: string;
};

function getColor(status: string): 'default' | 'success' | 'warning' | 'error' | 'info' {
  const value = status.toUpperCase();
  if (['APPROVED', 'VECTORIZED', 'OCR_DONE', 'INDEX_PARSED'].includes(value)) return 'success';
  if (['REVIEW_REQUIRED', 'REVIEW', 'PENDING'].includes(value)) return 'warning';
  if (['FAILED'].includes(value)) return 'error';
  if (['OCR_RUNNING', 'VERIFYING', 'INDEX_SEARCH_RUNNING', 'VECTORIZING', 'UPLOADED'].includes(value)) return 'info';
  return 'default';
}

export default function StatusBadge({ status }: Props) {
  return <Chip label={status} color={getColor(status)} size="small" />;
}
