import { create } from 'zustand'

interface AppState {
  currentRunId: string | null;
  subSidebarCollapsed: boolean;
  theme: 'light' | 'dark' | 'system';
  setCurrentRunId: (id: string | null) => void;
  toggleSubSidebar: () => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentRunId: null,
  subSidebarCollapsed: false,
  theme: 'system',
  setCurrentRunId: (id) => set({ currentRunId: id }),
  toggleSubSidebar: () => set((state) => ({ subSidebarCollapsed: !state.subSidebarCollapsed })),
  setTheme: (theme) => set({ theme }),
}))
