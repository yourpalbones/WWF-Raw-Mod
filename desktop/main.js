const { app, BrowserWindow, dialog, shell } = require('electron');
const path = require('node:path');
let window;
app.whenReady().then(() => {
  window = new BrowserWindow({
    width: 1280, height: 950, minWidth: 760, minHeight: 600,
    title: 'WrestleEdit', autoHideMenuBar: true,
    webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true }
  });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event, url) => {
    event.preventDefault();
    if (url.startsWith('https://github.com/yourpalbones/WWF-Raw-Mod/')) shell.openExternal(url);
  });
  window.webContents.session.on('will-download', (event, item) => {
    item.setSaveDialogOptions({ title: 'Save your WrestleEdit file', defaultPath: path.join(app.getPath('downloads'), item.getFilename()) });
    item.on('done', (_event, state) => {
      if (state !== 'completed' && state !== 'cancelled') dialog.showErrorBox('Could not save file', 'Choose a writable folder and try saving again.');
    });
  });
  window.loadFile(path.join(__dirname, 'gear-workshop.html'));
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (window && !window.isDestroyed()) window.show(); });
