import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAppStore } from '@/stores/appStore';
import { useValidationStore } from '@/stores/validationStore';
import { Sun, Moon, Monitor, Settings } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { useTheme } from '@/hooks/useTheme';
import { findActiveModule } from '@/config/navigationConfig';

export function TopBar() {
  const { currentRunId, theme, setTheme } = useAppStore();
  const { isScanning, isValidating } = useValidationStore();
  const location = useLocation();
  useTheme(); // Apply theme

  const activeModule = findActiveModule(location.pathname);

  let status = 'IDLE';
  if (isScanning) status = 'SCANNING';
  else if (isValidating) status = 'VALIDATING';
  else if (currentRunId) status = 'COMPLETED';

  return (
    <header className="app-topbar min-h-[52px] border-b bg-card flex items-center justify-between gap-3 px-6 max-md:px-3 max-md:py-2 shrink-0">
      <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        {activeModule && <span className="topbar-module border-r pr-4 text-[13px] font-semibold">{activeModule.label}</span>}
        {activeModule && (
          <span className="font-semibold text-foreground">Current Run</span>
        )}
        {!activeModule && (
          <span className="font-semibold text-foreground">Settings</span>
        )}
        {activeModule && currentRunId ? (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">{currentRunId}</span>
            <Badge variant="outline">{status}</Badge>
          </div>
        ) : activeModule ? (
          <span className="flex items-center gap-2 text-xs text-muted-foreground"><span className="h-1.5 w-1.5 rounded-full bg-slate-400" aria-hidden="true" />No active run</span>
        ) : null}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <div className="flex bg-muted rounded-md p-1">
          <button 
            onClick={() => setTheme('light')} 
            className={`p-1.5 rounded-sm ${theme === 'light' ? 'bg-background shadow' : 'text-muted-foreground'}`}
            title="Light Mode"
            aria-label="Light Mode"
            aria-pressed={theme === 'light'}
          >
            <Sun size={16} />
          </button>
          <button 
            onClick={() => setTheme('dark')} 
            className={`p-1.5 rounded-sm ${theme === 'dark' ? 'bg-background shadow' : 'text-muted-foreground'}`}
            title="Dark Mode"
            aria-label="Dark Mode"
            aria-pressed={theme === 'dark'}
          >
            <Moon size={16} />
          </button>
          <button 
            onClick={() => setTheme('system')} 
            className={`p-1.5 rounded-sm ${theme === 'system' ? 'bg-background shadow' : 'text-muted-foreground'}`}
            title="System Theme"
            aria-label="System Theme"
            aria-pressed={theme === 'system'}
          >
            <Monitor size={16} />
          </button>
        </div>
        <Link to="/settings" aria-label="Settings" className="p-2 text-muted-foreground hover:bg-accent rounded-md">
          <Settings size={20} />
        </Link>
      </div>
    </header>
  );
}
