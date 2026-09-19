import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { findActiveModule } from '@/config/navigationConfig';
import { cn } from '@/lib/utils';

export function SubSidebar() {
  const location = useLocation();
  const { subSidebarCollapsed, toggleSubSidebar } = useAppStore();
  const activeModule = findActiveModule(location.pathname);

  // Don't render sub-sidebar if no module is active (e.g. on /settings)
  if (!activeModule) return null;

  if (subSidebarCollapsed) {
    return (
      <div className="flex flex-col h-full w-10 bg-card border-r shrink-0">
        <div className="flex items-center justify-center h-[52px] border-b">
          <button
            onClick={toggleSubSidebar}
            className="p-1 hover:bg-accent rounded-md text-muted-foreground"
            title="Expand sidebar"
            aria-label="Expand sidebar"
            aria-expanded={false}
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="module-sidebar flex flex-col h-full w-[208px] max-md:w-[168px] max-[580px]:w-11 bg-card border-r shrink-0">
      {/* Module Name + Collapse Toggle */}
      <div className="flex items-center h-[52px] border-b px-3 justify-between">
        <div className="min-w-0"><p className="font-bold text-[14px] tracking-tight text-foreground">Data Verificator</p><p className="text-[9px] uppercase tracking-[0.12em] text-muted-foreground">Technical data workstation</p></div>
        <button
          onClick={toggleSubSidebar}
          className="p-1 hover:bg-accent rounded-md text-muted-foreground shrink-0"
          title="Collapse sidebar"
          aria-label="Collapse sidebar"
          aria-expanded={true}
        >
          <ChevronLeft size={18} />
        </button>
      </div>

      {/* Navigation Items */}
      <nav aria-label={activeModule.label} className="flex-1 overflow-y-auto py-4 flex flex-col gap-1 px-2">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">{activeModule.label}</p>
        {activeModule.navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            aria-label={item.label}
            title={item.label}
            end={item.path === activeModule.basePath}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm",
                isActive
                  ? "bg-[var(--dv-blue-soft)] text-[var(--dv-blue)] font-semibold"
                  : "hover:bg-accent hover:text-accent-foreground text-muted-foreground"
              )
            }
          >
            <item.icon size={18} className="shrink-0" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
