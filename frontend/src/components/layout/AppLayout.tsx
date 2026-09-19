import React from 'react';
import { Outlet } from 'react-router-dom';
import { MainSidebar } from './MainSidebar';
import { SubSidebar } from './SubSidebar';
import { TopBar } from './TopBar';

export function AppLayout() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <MainSidebar />
      <SubSidebar />
      <div className="flex min-w-0 flex-col flex-1 overflow-hidden">
        <TopBar />
        <main id="main-workspace" className="app-workspace flex-1 overflow-auto p-6 max-md:p-4 max-[580px]:p-3">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
