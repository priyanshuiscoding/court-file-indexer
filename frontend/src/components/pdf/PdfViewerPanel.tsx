import { useEffect, useMemo, useRef, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { Document, Page, pdfjs } from 'react-pdf';
import PdfToolbar from './PdfToolbar';
import Loader from '../common/Loader';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

type Props = {
  fileUrl?: string | null;
  jumpPage?: number | null;
  currentPage: number;
  onPageChange: (page: number) => void;
};

export default function PdfViewerPanel({ fileUrl, jumpPage, currentPage, onPageChange }: Props) {
  const [numPages, setNumPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [viewerWidth, setViewerWidth] = useState(720);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const pageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const rafRef = useRef<number | null>(null);
  const suppressScrollSyncUntilRef = useRef<number>(0);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    const resize = () => {
      const width = el.clientWidth;
      const padded = Math.max(280, width - 48);
      setViewerWidth(Math.min(760, padded));
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(el);

    return () => observer.disconnect();
  }, []);

  const clampPage = (page: number) => {
    if (numPages <= 0) return 1;
    return Math.max(1, Math.min(numPages, page));
  };

  const scrollToPage = (page: number, behavior: ScrollBehavior = 'smooth') => {
    const target = clampPage(page);
    const node = pageRefs.current[target];
    if (!node) return;

    suppressScrollSyncUntilRef.current = Date.now() + 400;
    node.scrollIntoView({ behavior, block: 'start' });
    onPageChange(target);
  };

  useEffect(() => {
    if (!jumpPage) return;
    scrollToPage(jumpPage, 'smooth');
  }, [jumpPage, numPages]);

  useEffect(() => {
    const root = scrollRef.current;
    if (!root || numPages === 0) return;

    const computeVisiblePage = () => {
      const rootTop = root.getBoundingClientRect().top;
      let bestPage = 1;
      let bestDistance = Number.POSITIVE_INFINITY;

      for (let page = 1; page <= numPages; page += 1) {
        const node = pageRefs.current[page];
        if (!node) continue;

        const top = node.getBoundingClientRect().top;
        const distance = Math.abs(top - rootTop - 12);
        if (distance < bestDistance) {
          bestDistance = distance;
          bestPage = page;
        }
      }

      return bestPage;
    };

    const onScroll = () => {
      if (Date.now() < suppressScrollSyncUntilRef.current) return;

      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }

      rafRef.current = requestAnimationFrame(() => {
        const page = computeVisiblePage();
        if (page !== currentPage) {
          onPageChange(page);
        }
      });
    };

    root.addEventListener('scroll', onScroll, { passive: true });

    return () => {
      root.removeEventListener('scroll', onScroll);
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [numPages, currentPage, onPageChange]);

  useEffect(() => {
    pageRefs.current = {};
    setNumPages(0);
  }, [fileUrl]);

  const pages = useMemo(() => Array.from({ length: numPages }, (_, i) => i + 1), [numPages]);

  return (
    <Box
      sx={{
        borderRadius: 3,
        overflow: 'hidden',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: '#0b1220'
      }}
    >
      <PdfToolbar
        pageNumber={clampPage(currentPage)}
        totalPages={numPages}
        onPrev={() => scrollToPage(currentPage - 1, 'smooth')}
        onNext={() => scrollToPage(currentPage + 1, 'smooth')}
        canPrev={currentPage > 1}
        canNext={numPages > 0 && currentPage < numPages}
      />

      <Box
        ref={scrollRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          px: 2,
          py: 2,
          bgcolor: '#081225'
        }}
      >
        {!fileUrl ? (
          <Typography color="#cbd5e1">Select a document to preview its PDF.</Typography>
        ) : (
          <Document
            file={fileUrl}
            onLoadSuccess={({ numPages: loadedPages }) => {
              setNumPages(loadedPages);
              setLoading(false);
              onPageChange(1);
            }}
            onLoadProgress={() => setLoading(true)}
            loading={<Loader />}
            error={<Typography color="#fecaca">Could not load PDF preview.</Typography>}
          >
            {loading ? <Loader /> : null}

            <Box display="flex" flexDirection="column" gap={2}>
              {pages.map((page) => (
                <Box
                  key={page}
                  ref={(node: HTMLDivElement | null) => {
                    pageRefs.current[page] = node;
                  }}
                  sx={{
                    display: 'flex',
                    justifyContent: 'center',
                    scrollMarginTop: '12px'
                  }}
                >
                  <Box
                    sx={{
                      borderRadius: 2,
                      overflow: 'hidden',
                      boxShadow: '0 12px 30px rgba(0,0,0,0.35)',
                      border: currentPage === page ? '2px solid #3b82f6' : '2px solid transparent',
                      background: '#fff',
                      transition: 'border-color 0.2s ease'
                    }}
                  >
                    <Page pageNumber={page} width={viewerWidth} renderTextLayer renderAnnotationLayer />
                  </Box>
                </Box>
              ))}
            </Box>
          </Document>
        )}
      </Box>
    </Box>
  );
}
