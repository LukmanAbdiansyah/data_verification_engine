import { apiService } from '../services/api';

export function useElectron() {
  const isElectron = Boolean(typeof window !== 'undefined' && (window as any).electronAPI);

  return {
    isElectron,
    selectFolder: async (): Promise<string | null> => {
      // 1. If running inside Electron desktop shell
      if (isElectron && (window as any).electronAPI?.selectFolder) {
        try {
          const electronPath = await (window as any).electronAPI.selectFolder();
          if (electronPath) return electronPath;
        } catch (e) {
          console.error('Electron folder picker error:', e);
        }
      }

      // 2. If running in Web Browser mode: ask backend to open Windows native folder dialog
      try {
        const res = await apiService.browseFolder();
        if (res && res.path) {
          return res.path;
        }
      } catch (e) {
        console.error('Backend folder dialog error:', e);
      }

      return null;
    },
    selectFile: async (options?: any): Promise<string | null> => {
      if (isElectron && (window as any).electronAPI?.selectFile) {
        try {
          const electronPath = await (window as any).electronAPI.selectFile(options);
          if (electronPath) return Array.isArray(electronPath) ? electronPath[0] : electronPath;
        } catch (e) {
          console.error('Electron file picker error:', e);
        }
      }

      try {
        const res = await apiService.browseVerificationFile();
        if (res && res.path) {
          return res.path;
        }
      } catch (e) {
        console.error('Backend file dialog error:', e);
      }

      return null;
    },
    selectFiles: async (options?: any): Promise<string[]> => {
      if (isElectron && (window as any).electronAPI?.selectFile) {
        try {
          const electronPath = await (window as any).electronAPI.selectFile({
            properties: ['openFile', 'multiSelections'],
            ...options,
          });
          if (electronPath) return Array.isArray(electronPath) ? electronPath : [electronPath];
        } catch (e) {
          console.error('Electron file picker error:', e);
        }
      }

      try {
        const res = await apiService.browseVerificationFile();
        if (res && res.paths && res.paths.length > 0) {
          return res.paths;
        } else if (res && res.path) {
          return [res.path];
        }
      } catch (e) {
        console.error('Backend file dialog error:', e);
      }

      return [];
    },
    saveFile: async (options?: any) => (isElectron ? (window as any).electronAPI.saveFile(options) : null),
    openInExplorer: async (path: string) => (isElectron ? (window as any).electronAPI.openInExplorer(path) : null),
    openLogsFolder: async () => (isElectron ? (window as any).electronAPI.openLogsFolder() : null),
  };
}
