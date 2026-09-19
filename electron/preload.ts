import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  selectFolder: () => ipcRenderer.invoke('dialog:selectFolder'),
  selectFile: (options: any) => ipcRenderer.invoke('dialog:selectFile', options),
  saveFile: (options: any) => ipcRenderer.invoke('dialog:saveFile', options),
  openInExplorer: (filePath: string) => ipcRenderer.invoke('shell:openInExplorer', filePath),
  getAppVersion: () => ipcRenderer.invoke('app:getVersion'),
  openLogsFolder: () => ipcRenderer.invoke('shell:openLogsFolder'),
});
