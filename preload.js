const { contextBridge, ipcRenderer, webUtils } = require('electron');

contextBridge.exposeInMainWorld('kaboto', {
  min:         () => ipcRenderer.send('win:min'),
  max:         () => ipcRenderer.send('win:max'),
  close:       () => ipcRenderer.send('win:close'),
  defaultDir:  () => ipcRenderer.invoke('default-dir'),
  openFolder:  p => ipcRenderer.invoke('open-folder', p),
  chooseDir:   c => ipcRenderer.invoke('choose-dir', c),
  copyMods: (d, s) => ipcRenderer.invoke('copy-mods', d, s),
  pathForFile: f => webUtils.getPathForFile(f)
});
