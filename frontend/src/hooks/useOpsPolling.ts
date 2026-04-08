import { useEffect } from 'react';
import { getOpsStatus } from '../api/ops';
import { useAppStore } from '../store/useAppStore';

export function useOpsPolling() {
  const setOpsStatus = useAppStore((s) => s.setOpsStatus);

  useEffect(() => {
    let mounted = true;
    const fetchData = async () => {
      try {
        const data = await getOpsStatus();
        if (mounted) setOpsStatus(data);
      } catch {
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 6000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [setOpsStatus]);
}
