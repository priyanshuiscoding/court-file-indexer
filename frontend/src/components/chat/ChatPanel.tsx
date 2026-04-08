import { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import { askChat, getChatHistory, getChatStatus, type ChatHistoryMessage, type ChatSource } from '../../api/chat';

type Props = {
  documentId?: number | null;
  onJumpToPage?: (page: number) => void;
};

function extractApiError(error: unknown, fallback: string): string {
  const anyErr = error as any;
  return anyErr?.response?.data?.detail || anyErr?.message || fallback;
}

export default function ChatPanel({ documentId, onJumpToPage }: Props) {
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState<ChatHistoryMessage[]>([]);
  const [sources, setSources] = useState<ChatSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) {
      setHistory([]);
      setSources([]);
      setReady(false);
      setErrorMessage(null);
      return;
    }

    let active = true;
    Promise.all([getChatHistory(documentId), getChatStatus(documentId)])
      .then(([rows, status]) => {
        if (!active) return;
        setHistory(rows);
        setReady(Boolean(status?.ready));
      })
      .catch(() => {
        if (!active) return;
        setHistory([]);
        setReady(false);
      });

    return () => {
      active = false;
    };
  }, [documentId]);

  const handleAsk = async () => {
    if (!documentId || !question.trim()) return;

    setLoading(true);
    setErrorMessage(null);
    try {
      const result = await askChat(documentId, question.trim());
      const freshHistory = await getChatHistory(documentId);
      setHistory(freshHistory);
      setSources(result.sources || []);
      setQuestion('');
    } catch (error) {
      setErrorMessage(extractApiError(error, 'Chat request failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
      <Stack spacing={2}>
        <Typography variant="subtitle1" fontWeight={800}>
          Case File Chatbot
        </Typography>

        {!ready ? (
          <Alert severity="info">Document chat is not ready yet. Complete indexing/vectorization first.</Alert>
        ) : null}

        {errorMessage ? <Alert severity="error">{errorMessage}</Alert> : null}

        <TextField
          multiline
          minRows={3}
          label="Ask anything about this case file"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Example: Give me a short summary of the case file"
        />

        <Button
          variant="contained"
          onClick={handleAsk}
          disabled={!documentId || !ready || loading || !question.trim()}
          sx={{ alignSelf: 'flex-start' }}
        >
          {loading ? 'Asking...' : 'Ask'}
        </Button>

        <Box>
          <Typography variant="subtitle2" fontWeight={700} mb={1}>
            Conversation
          </Typography>

          <Stack spacing={1.2}>
            {history.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No chat history yet.
              </Typography>
            ) : (
              history.map((msg) => (
                <Paper
                  key={msg.id}
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    bgcolor: msg.role === 'user' ? '#f8fbff' : '#ffffff',
                    borderColor: msg.role === 'user' ? '#dbe7ff' : '#e5e7eb'
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    {msg.role === 'user' ? 'You' : 'Assistant'}
                  </Typography>
                  <Typography variant="body2" whiteSpace="pre-wrap">
                    {msg.message}
                  </Typography>
                </Paper>
              ))
            )}
          </Stack>
        </Box>

        <Box>
          <Typography variant="subtitle2" fontWeight={700} mb={1}>
            Sources
          </Typography>

          <Stack spacing={1}>
            {sources.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No sources yet.
              </Typography>
            ) : (
              sources.map((src, idx) => (
                <Paper key={`${src.page_no}-${idx}`} variant="outlined" sx={{ p: 1.5 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                    <Chip
                      label={`Page ${src.page_no}`}
                      size="small"
                      color="primary"
                      variant="outlined"
                      onClick={() => onJumpToPage?.(src.page_no)}
                    />
                    {typeof src.score === 'number' ? (
                      <Typography variant="caption" color="text.secondary">
                        score: {src.score.toFixed(3)}
                      </Typography>
                    ) : null}
                  </Stack>

                  <Typography variant="body2" color="text.secondary">
                    {src.text}
                  </Typography>
                </Paper>
              ))
            )}
          </Stack>
        </Box>
      </Stack>
    </Paper>
  );
}
