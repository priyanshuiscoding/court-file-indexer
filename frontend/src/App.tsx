import DashboardPage from './pages/DashboardPage';
import HighCourtImportPage from './pages/HighCourtImportPage';

export default function App() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/';
  if (path === '/high-court-import') {
    return <HighCourtImportPage />;
  }
  return <DashboardPage />;
}
