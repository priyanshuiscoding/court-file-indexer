import { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';

type Props = {
  onSearch: (params: { cnr?: string; batch_no?: string }) => void;
};

export default function SearchBar({ onSearch }: Props) {
  const [cnr, setCnr] = useState('');
  const [batchNo, setBatchNo] = useState('');

  return (
    <Box display="grid" gridTemplateColumns={{ xs: '1fr', md: '1fr 1fr auto auto' }} gap={1.5}>
      <TextField
        label="Search by CNR / Filing No"
        size="small"
        value={cnr}
        onChange={(e) => setCnr(e.target.value)}
      />
      <TextField
        label="Batch No"
        size="small"
        value={batchNo}
        onChange={(e) => setBatchNo(e.target.value)}
      />
      <Button variant="outlined" onClick={() => onSearch({ cnr, batch_no: batchNo })} sx={{ textTransform: 'none' }}>
        Search
      </Button>
      <Button variant="text" onClick={() => { setCnr(''); setBatchNo(''); onSearch({}); }} sx={{ textTransform: 'none' }}>
        Reset
      </Button>
    </Box>
  );
}
