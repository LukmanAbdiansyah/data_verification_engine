import { ipcMain, dialog, shell, app } from 'electron';

ipcMain.handle('dialog:selectFolder', async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog({
    properties: ['openDirectory'],
  });
  if (canceled) return null;
  return filePaths[0];
});

ipcMain.handle('dialog:selectFile', async (_, options) => {
  const { canceled, filePaths } = await dialog.showOpenDialog({
    properties: ['openFile'],
    ...options,
  });
  if (canceled) return null;
  return filePaths[0];
});

ipcMain.handle('dialog:saveFile', async (_, options) => {
  const { canceled, filePath } = await dialog.showSaveDialog(options);
  if (canceled) return null;
  return filePath;
});

ipcMain.handle('shell:openInExplorer', async (_, filePath) => {
  shell.showItemInFolder(filePath);
});

ipcMain.handle('app:getVersion', () => {
  return app.getVersion();
});

ipcMain.handle('shell:openLogsFolder', () => {
  const logsPath = app.getPath('userData');
  shell.openPath(logsPath);
});
