import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';

export function usePdfJump() {
  const jumpTarget = useAppStore((s) => s.pdfJumpTarget);
  const setCurrentPdfPage = useAppStore((s) => s.setCurrentPdfPage);

  useEffect(() => {
    if (jumpTarget) {
      setCurrentPdfPage(jumpTarget);
    }
  }, [jumpTarget, setCurrentPdfPage]);
}
