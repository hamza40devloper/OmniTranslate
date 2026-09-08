const { app, BrowserWindow, Menu, ipcMain, shell, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

// المجلد الحقيقي الافتراضي: AppData\.kaboto
const DEFAULT_DIR = path.join(app.getPath('appData'), '.kaboto');
let win = null;

function createWindow() {
  win = new BrowserWindow({
    width: 1240, height: 800, minWidth: 960, minHeight: 620,
    frame: false,                       // إطار ويندوز مختفي — عندنا شريطنا الخاص
    backgroundColor: '#0A0D0A',
    icon: path.join(__dirname, 'build', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  win.loadFile('index.html');

  win.webContents.on('did-finish-load', async () => {
    // جعل شريط العنوان قابلاً لسحب النافذة
    await win.webContents.insertCSS(
      '.titlebar{-webkit-app-region:drag}.titlebar button{-webkit-app-region:no-drag}'
    );
    // ربط الأزرار بالوظائف الحقيقية
    await win.webContents.executeJavaScript('(' + wirePage.toString() + ')()');
  });
}

/* يُنفَّذ داخل الصفحة بعد جاهزيتها */
function wirePage() {
  if (!window.kaboto) return;
  const byId = id => document.getElementById(id);

  // أزرار النافذة
  byId('winMin').onclick = () => kaboto.min();
  byId('winMax').onclick = () => kaboto.max();
  byId('winClose').onclick = () => kaboto.close();

  // استبدال المجلد التوضيحي بالمسار الحقيقي على القرص
  if (!state.gameDir || state.gameDir.includes('You')) {
    kaboto.defaultDir().then(d => {
      state.gameDir = d; byId('gameDir').value = d;
      save(); renderHome(); renderMods();
    });
  }

  // اختيار مجلد اللعبة من نافذة النظام
  byId('browseDir').onclick = async () => {
    const p = await kaboto.chooseDir(state.gameDir);
    if (p) {
      state.gameDir = p; byId('gameDir').value = p;
      save(); renderHome(); renderMods();
      toast('تم تعيين مجلد اللعبة: ' + p);
    }
  };

  // أي إشعار يقول "سيُفتح المجلد في نسخة EXE" → نفتحه فعلاً الآن
  const _toast = toast;
  toast = function (msg, type) {
    const m = String(msg);
    if (m.indexOf('EXE:') !== -1) {
      const p = m.split('EXE:')[1].trim();
      kaboto.openFolder(p).then(err => {
        if (err) _toast('تعذّر فتح المجلد: ' + err, 'warn');
        else _toast('فُتح المجلد: ' + p);
      });
      return;
    }
    _toast(msg, type);
  };

  // سحب وإفلات المودات → نسخ حقيقي إلى مجلد mods على القرص
  addMods = async function (fileList) {
    const uid = byId('modsVerSel').value;
    if (!uid) return;
    const v = findVer(uid);
    const files = [...fileList].filter(f => /\.(jar|zip)$/i.test(f.name));
    if (!files.length) return _toast('لا توجد ملفات .jar صالحة', 'warn');
    const dest = state.gameDir + '\\versions\\' + v.id + '\\mods';
    const srcs = files.map(f => kaboto.pathForFile(f));
    const n = await kaboto.copyMods(dest, srcs);
    if (n < 0) return _toast('فشل نسخ المودات — تحقق من مجلد اللعبة', 'warn');
    state.mods[uid] = state.mods[uid] || [];
    for (const f of files)
      state.mods[uid].push({ file: f.name, size: fmtSize(f.size), enabled: true });
    save(); renderMods(); renderHome();
    _toast('نُسخ ' + n + ' مود فعلياً إلى: ' + dest);
  };
}

/* ===== أعمال النظام ===== */
Menu.setApplicationMenu(null);

ipcMain.on('win:min', () => win.minimize());
ipcMain.on('win:max', () => (win.isMaximized() ? win.unmaximize() : win.maximize()));
ipcMain.on('win:close', () => win.close());

ipcMain.handle('default-dir', () => {
  fs.mkdirSync(DEFAULT_DIR, { recursive: true });
  return DEFAULT_DIR;
});

ipcMain.handle('open-folder', async (e, p) => {
  try {
    fs.mkdirSync(p, { recursive: true });   // أنشئه إن لم يكن موجوداً
    const err = await shell.openPath(p);
    return err || '';
  } catch (err) { return String(err.message || err); }
});

ipcMain.handle('choose-dir', async (e, cur) => {
  const r = await dialog.showOpenDialog(win, {
    properties: ['openDirectory'],
    defaultPath: cur || DEFAULT_DIR
  });
  return r.canceled ? null : r.filePaths[0];
});

ipcMain.handle('copy-mods', (e, dest, srcs) => {
  try {
    fs.mkdirSync(dest, { recursive: true });
    let n = 0;
    for (const s of srcs) { fs.copyFileSync(s, path.join(dest, path.basename(s))); n++; }
    return n;
  } catch (err) { return -1; }
});

app.whenReady().then(createWindow);
app.on('window-all-closed', () => app.quit());
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
