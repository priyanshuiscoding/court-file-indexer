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
  const actionButtonSx = { textTransform: 'none', minHeight: 38, minWidth: 92 };

  return (
    <Box
      display="grid"
      gridTemplateColumns={{ xs: '1fr', md: '1.3fr 1fr auto auto' }}
      gap={1}
      alignItems="center"
    >
      <TextField
        label="Search by CNR / Filing No"
        size="small"
        value={cnr}
        onChange={(e) => setCnr(e.target.value)}
        sx={{ '& .MuiOutlinedInput-root': { bgcolor: '#f8fafc', minHeight: 38 } }}
      />
      <TextField
        label="Batch No"
        size="small"
        value={batchNo}
        onChange={(e) => setBatchNo(e.target.value)}
        sx={{ '& .MuiOutlinedInput-root': { bgcolor: '#f8fafc', minHeight: 38 } }}
      />
      <Button
        variant="outlined"
        size="small"
        onClick={() => onSearch({ cnr, batch_no: batchNo })}
        sx={actionButtonSx}
      >
        Search
      </Button>
      <Button
        variant="text"
        size="small"
        onClick={() => { setCnr(''); setBatchNo(''); onSearch({}); }}
        sx={actionButtonSx}
      >
        Reset
      </Button>
    </Box>
  );
}
