import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';

type Props = {
  onOpenOps: () => void;
};

export default function AppHeader({ onOpenOps }: Props) {
  return (
    <AppBar position="static" color="inherit" elevation={0} sx={{ borderBottom: '1px solid #e5e7eb' }}>
      <Toolbar sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="h6" fontWeight={700}>Court File Indexer</Typography>
          <Typography variant="body2" color="text.secondary">High Court PDF indexing, review, vectorization and chat</Typography>
        </Box>
        <Button variant="contained" onClick={onOpenOps}>Operations Panel</Button>
      </Toolbar>
    </AppBar>
  );
}
