import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { modules, settingsNav, findActiveModule } from '@/config/navigationConfig';
import { cn } from '@/lib/utils';
import dvMark from '@/assets/dv-mark.svg';

export function MainSidebar() {
  const location = useLocation();
  const activeModule = findActiveModule(location.pathname);

  return (
    <div className="app-rail flex flex-col h-full w-16 max-[580px]:w-14 bg-card border-r shrink-0">
      {/* App Logo / Title */}
      <div className="flex items-center justify-center h-[52px] border-b">
        <img src={dvMark} alt="Data Verificator" className="h-10 w-10" />
      </div>

      {/* Module Icons */}
      <nav aria-label="Modul aplikasi" className="flex-1 flex flex-col items-center gap-1 py-3 px-1.5 overflow-y-auto">
        {modules.map((mod) => {
          const isActive = activeModule?.id === mod.id;
          return (
            <NavLink
              key={mod.id}
              to={mod.basePath}
              className={cn(
                "flex flex-col items-center justify-center gap-0.5 w-full py-2 px-1 rounded-lg transition-colors group relative",
                isActive
                  ? "bg-[#14213D] text-white shadow-sm"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
              title={mod.label}
              aria-current={isActive ? 'page' : undefined}
            >
              <mod.icon size={22} className="shrink-0" />
              <span className="text-[10px] font-medium leading-tight text-center truncate w-full">
                {mod.shortLabel}
              </span>
            </NavLink>
          );
        })}
      </nav>

      {/* Settings at bottom */}
      <div className="p-1.5 border-t">
        <NavLink
          to={settingsNav.path}
          className={({ isActive }) =>
            cn(
              "flex flex-col items-center justify-center gap-0.5 w-full py-2 px-1 rounded-lg transition-colors",
              isActive
                ? "bg-[#14213D] text-white"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )
          }
          title={settingsNav.label}
        >
          <settingsNav.icon size={22} className="shrink-0" />
          <span className="text-[10px] font-medium leading-tight">{settingsNav.label}</span>
        </NavLink>
      </div>
    </div>
  );
}
