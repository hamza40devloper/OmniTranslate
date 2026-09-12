#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileForge | مِسبَكة الملفات
أداة سطح مكتب محلية 100% (بدون إنترنت ولا استضافة):
• إنشاء ملفات جديدة بأي امتداد (.txt .js .py .html ...)
• استيراد ملفات أو مجلدات كاملة (زر أو سحب وإفلات داخل النافذة)
• تغيير امتداد ملف محدد أو صيغة جميع الملفات بضغطة واحدة
• تغيير الامتداد لا يمس المحتوى: webm->mp4 ، jpg->txt ... كما تحب
• تحرير الملفات النصية والبرمجية وحفظها أو تصديرها بالصيغة الجديدة
• تصدير ملف واحد أو المجلد كاملًا مع الحفاظ على بنية المجلدات
"""

import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path, PurePosixPath
from tkinter import ttk, filedialog, messagebox

# سحب وإفلات — اختياري: إن لم تُثبَّت المكتبة تعمل الأداة بدونها
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_OK = True
except Exception:
    DND_OK = False

APP_TITLE = "FileForge | مِسبَكة الملفات"
MAX_TEXT_BYTES = 2 * 1024 * 1024  # حد تحميل النصوص تلقائيًا في المحرر

TEXT_EXTS = {
    '.txt', '.text', '.log', '.md', '.markdown', '.csv', '.tsv', '.ini', '.cfg', '.conf',
    '.env', '.properties', '.htaccess', '.gitignore',
    '.js', '.mjs', '.cjs', '.ts', '.jsx', '.tsx', '.json', '.jsonc', '.json5',
    '.py', '.pyw', '.rb', '.php', '.pl', '.lua', '.r',
    '.c', '.h', '.cpp', '.cc', '.cxx', '.hpp', '.hh', '.cs', '.java', '.kt', '.kts',
    '.swift', '.m', '.mm', '.go', '.rs', '.dart', '.scala', '.groovy', '.vb',
    '.html', '.htm', '.xhtml', '.css', '.scss', '.sass', '.less',
    '.xml', '.svg', '.xsl', '.xslt', '.dtd',
    '.yml', '.yaml', '.toml', '.sql',
    '.bat', '.cmd', '.ps1', '.psm1', '.sh', '.bash', '.zsh',
    '.srt', '.vtt', '.tex',
}

IGNORED_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv',
                '.idea', '.vscode', '__MACOSX', '.svn'}

BG       = '#f3eee1'
TOPBAR   = '#2b2520'
TOPFG    = '#f5efe2'
ACCENT   = '#b45309'
ACCENT_H = '#92400e'
FIELD    = '#fffdf6'
INK      = '#2c2721'


def human_size(n):
    f = float(n)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if f < 1024 or unit == 'GB':
            if unit == 'B':
                return f"{int(f)} B"
            return f"{f:,.1f} {unit}"
        f /= 1024.0


class FileForge:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry('1150x700')
        root.minsize(940, 560)
        root.configure(bg=BG)

        self.items = []            # عناصر القائمة
        self.items_by_id = {}
        self.current = None        # العنصر الظاهر في المحرر
        self.editor_editable = False
        self._counter = 0
        self._known = set()

        self._build_style()
        self._build_topbar()
        self._build_main()
        self._build_statusbar()

        if DND_OK:
            root.drop_target_register(DND_FILES)
            root.dnd_bind('<<Drop>>', self._on_drop)

        self.set_status("جاهز — استورد ملفات أو مجلدًا، أو أنشئ ملفًا جديدًا للبدء.")

    # ────────────────────────── الواجهة ──────────────────────────

    def _build_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('.', background=BG, foreground=INK, font=('Segoe UI', 10))
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG, foreground=INK)
        style.configure('TButton', padding=(12, 6))
        style.configure('Accent.TButton', background=ACCENT, foreground='#ffffff',
                        font=('Segoe UI', 10, 'bold'), padding=(14, 6))
        style.map('Accent.TButton',
                  background=[('active', ACCENT_H), ('disabled', '#c9b18d')],
                  foreground=[('disabled', '#f4efe6')])
        style.configure('TLabelframe', background=BG)
        style.configure('TLabelframe.Label', background=BG, foreground=ACCENT,
                        font=('Segoe UI', 10, 'bold'))
        style.configure('Treeview', background=FIELD, fieldbackground=FIELD, foreground=INK,
                        rowheight=26, font=('Segoe UI', 10),
                        bordercolor='#d8cfba', borderwidth=1)
        style.configure('Treeview.Heading', background='#e2d8c0', foreground=INK,
                        font=('Segoe UI', 10, 'bold'), padding=(6, 6))
        style.map('Treeview', background=[('selected', '#e3c9a0')],
                  foreground=[('selected', INK)])
        style.configure('TEntry', fieldbackground=FIELD, padding=4)
        style.configure('TCombobox', fieldbackground=FIELD, padding=4)
        style.configure('Status.TLabel', background=BG, foreground='#6b6152')

    def _build_topbar(self):
        top = tk.Frame(self.root, bg=TOPBAR)
        top.pack(fill='x')
        tk.Label(top, text="FileForge · مِسبَكة الملفات", bg=TOPBAR, fg=TOPFG,
                 font=('Segoe UI', 13, 'bold')).pack(side='right', padx=(4, 14), pady=10)
        btns = tk.Frame(top, bg=TOPBAR)
        btns.pack(side='right')
        ttk.Button(btns, text="ملف جديد", command=self.new_file_dialog).pack(side='right', padx=3, pady=8)
        ttk.Button(btns, text="استيراد ملفات…", command=self.import_files).pack(side='right', padx=3)
        ttk.Button(btns, text="استيراد مجلد…", style='Accent.TButton',
                   command=self.import_folder).pack(side='right', padx=3)
        ttk.Button(btns, text="إزالة المحدد", command=self.remove_selected).pack(side='right', padx=3)
        ttk.Button(btns, text="تفريغ القائمة", command=self.clear_all).pack(side='right', padx=(3, 10))
        hint = "اسحب الملفات أو المجلدات وأفلتها داخل النافذة" if DND_OK else "استخدم أزرار الاستيراد أعلاه"
        tk.Label(top, text=hint, bg=TOPBAR, fg='#a89d8a',
                 font=('Segoe UI', 9)).pack(side='left', padx=14)

    def _build_main(self):
        pane = ttk.PanedWindow(self.root, orient='horizontal')
        pane.pack(fill='both', expand=True, padx=10, pady=8)

        # ── لوحة المحرر ──
        ed = ttk.Labelframe(pane, text=' محرر الملفات النصية والبرمجية ')
        self.editor_info_var = tk.StringVar(value="لا يوجد ملف محدد")
        ttk.Label(ed, textvariable=self.editor_info_var,
                  style='Status.TLabel').pack(fill='x', padx=10, pady=(6, 0))

        wrap = tk.Frame(ed, bg=BG)
        wrap.pack(fill='both', expand=True, padx=10, pady=6)
        self.editor = tk.Text(wrap, font=('Consolas', 11), wrap='none', undo=True,
                              bg=FIELD, fg=INK, insertbackground=INK,
                              relief='flat', padx=10, pady=8, spacing1=2, spacing3=2)
        ysb = ttk.Scrollbar(wrap, orient='vertical', command=self.editor.yview)
        xsb = ttk.Scrollbar(wrap, orient='horizontal', command=self.editor.xview)
        self.editor.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.editor.grid(row=0, column=0, sticky='nsew')
        ysb.grid(row=0, column=1, sticky='ns')
        xsb.grid(row=1, column=0, sticky='ew')
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        self.editor.bind('<Control-s>', self.save_text_buffer)
        self.editor.bind('<Control-S>', self.save_text_buffer)

        row = tk.Frame(ed, bg=BG)
        row.pack(fill='x', padx=10, pady=(0, 10))
        ttk.Button(row, text="حفظ النص (Ctrl+S)",
                   command=self.save_text_buffer).pack(side='right', padx=3)
        ttk.Button(row, text="فتح موقع الملف",
                   command=self.open_location).pack(side='right', padx=3)
        ttk.Button(row, text="كتابة على الملف الأصلي", style='Accent.TButton',
                   command=self.save_to_source).pack(side='right', padx=3)

        # ── لوحة القائمة ──
        lst = ttk.Labelframe(pane, text=' قائمة الملفات ')
        lst.columnconfigure(0, weight=1)
        lst.rowconfigure(0, weight=1)

        twrap = tk.Frame(lst, bg=BG)
        twrap.grid(row=0, column=0, sticky='nsew', padx=10, pady=6)
        cols = ('file', 'orig', 'new', 'size', 'state')
        headers = {'file': 'الملف (بالصيغة الجديدة)', 'orig': 'الأصل', 'new': 'الجديد',
                   'size': 'الحجم', 'state': 'الحالة'}
        widths = {'file': 330, 'orig': 70, 'new': 70, 'size': 90, 'state': 110}
        anchors = {'file': 'w', 'orig': 'center', 'new': 'center', 'size': 'e', 'state': 'center'}
        self.tree = ttk.Treeview(twrap, columns=cols, show='headings', selectmode='extended')
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor=anchors[c], stretch=(c == 'file'))
        ysb2 = ttk.Scrollbar(twrap, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb2.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        ysb2.grid(row=0, column=1, sticky='ns')
        twrap.rowconfigure(0, weight=1)
        twrap.columnconfigure(0, weight=1)
        self.tree.tag_configure('new', foreground='#0f766e')
        self.tree.tag_configure('edited', foreground=ACCENT)
        self.tree.tag_configure('renamed', foreground='#3f5f8f')
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.tree.bind('<Delete>', lambda e: self.remove_selected())

        tools = ttk.Frame(lst)
        tools.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 2))
        tools.columnconfigure(1, weight=1)

        ttk.Label(tools, text="صيغة المحدد:").grid(row=0, column=0, sticky='e', padx=(0, 6))
        self.ext_var = tk.StringVar()
        ext_ent = ttk.Entry(tools, textvariable=self.ext_var, width=18)
        ext_ent.grid(row=0, column=1, sticky='w', padx=(0, 6))
        ext_ent.bind('<KeyRelease>', self._on_ext_typed)
        ext_ent.bind('<Return>', lambda e: self.apply_ext_selected())
        ttk.Button(tools, text="تطبيق على المحدد",
                   command=self.apply_ext_selected).grid(row=0, column=2, padx=3)

        ttk.Label(tools, text="صيغة الجميع:").grid(row=1, column=0, sticky='e',
                                                   padx=(0, 6), pady=(6, 0))
        self.all_ext_var = tk.StringVar()
        all_ent = ttk.Entry(tools, textvariable=self.all_ext_var, width=18)
        all_ent.grid(row=1, column=1, sticky='w', padx=(0, 6), pady=(6, 0))
        all_ent.bind('<Return>', lambda e: self.apply_ext_all())
        ttk.Button(tools, text="تغيير صيغة جميع الملفات", style='Accent.TButton',
                   command=self.apply_ext_all).grid(row=1, column=2, padx=3, pady=(6, 0))

        ttk.Label(tools, text="اكتب الامتداد مع النقطة أو بدونها — مثل: mp4 ، js ، png ، txt",
                  style='Status.TLabel').grid(row=2, column=0, columnspan=3, sticky='e', pady=(4, 0))

        exp = ttk.Frame(lst)
        exp.grid(row=2, column=0, sticky='ew', padx=10, pady=(6, 10))
        ttk.Button(exp, text="تصدير المحدد باسم…",
                   command=self.export_selected).pack(side='right', padx=3)
        ttk.Button(exp, text="تصدير / حفظ الكل في مجلد…", style='Accent.TButton',
                   command=self.export_all).pack(side='right', padx=3)
        ttk.Label(exp, text="التصدير يكتب نسخة بالاسم والصيغة الجديدة — الأصل لا يُمس",
                  style='Status.TLabel').pack(side='left')

        pane.add(ed, weight=1)
        pane.add(lst, weight=1)

    def _build_statusbar(self):
        ttk.Separator(self.root).pack(fill='x', padx=10)
        bar = ttk.Frame(self.root)
        bar.pack(fill='x', padx=10, pady=(4, 8))
        self.status_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.status_var, style='Status.TLabel').pack(side='right')
        self.count_var = tk.StringVar(value="الملفات: 0")
        ttk.Label(bar, textvariable=self.count_var, style='Status.TLabel').pack(side='left')

    # ────────────────────────── أدوات عامة ──────────────────────────

    def set_status(self, msg):
        self.status_var.set(msg)

    def _update_count(self):
        self.count_var.set(f"الملفات: {len(self.items)}")

    def _new_id(self):
        self._counter += 1
        return f"i{self._counter}"

    @staticmethod
    def _norm_ext(e):
        e = (e or '').strip().lower().replace(' ', '')
        if not e:
            return ''
        if not e.startswith('.'):
            e = '.' + e
        return e

    def _center_over(self, win):
        win.update_idletasks()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        w, h = win.winfo_width(), win.winfo_height()
        win.geometry(f"+{rx + (rw - w) // 2}+{ry + (rh - h) // 3}")

    # ────────────────────────── الاستيراد ──────────────────────────

    def import_files(self):
        paths = filedialog.askopenfilenames(title="اختر ملفًا أو أكثر")
        self._import_paths(paths)

    def import_folder(self):
        d = filedialog.askdirectory(title="اختر المجلد (سيُستورد بكل محتوياته ومجلداته الفرعية)")
        if d:
            self._import_paths([d])

    def _on_drop(self, event):
        try:
            paths = self.root.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]
        self._import_paths([str(p) for p in paths if str(p).strip()])

    def _import_paths(self, paths):
        before = len(self.items)
        for p in paths:
            self._import_one(Path(p))
        added = len(self.items) - before
        if added:
            self._update_count()
            self.set_status(f"تم استيراد {added} ملف.")
        elif paths:
            self.set_status("لم يُضف أي ملف جديد (ربما كانت مستوردة مسبقًا).")

    def _import_one(self, p):
        if p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = sorted(d for d in dirs
                                 if d not in IGNORED_DIRS and not d.startswith('.'))
                for f in sorted(files):
                    fp = Path(root) / f
                    self._add_file(fp, fp.relative_to(p).as_posix())
        elif p.is_file():
            self._add_file(p, '')

    def _add_file(self, fp, rel):
        key = (os.path.abspath(str(fp)), rel)
        if key in self._known:
            return
        self._known.add(key)
        try:
            size = fp.stat().st_size
        except OSError:
            size = 0
        ext = fp.suffix.lower()
        it = {'id': self._new_id(), 'src': str(fp), 'rel': rel,
              'base': fp.stem or fp.name, 'orig_ext': ext, 'new_ext': ext,
              'size': size, 'content': None, 'loaded_text': None, 'is_new': False}
        self._insert_item(it)

    # ────────────────────────── القائمة ──────────────────────────

    def _insert_item(self, it):
        self.items.append(it)
        self.items_by_id[it['id']] = it
        self.tree.insert('', 'end', iid=it['id'],
                         values=self._row_values(it), tags=(self._tag_for(it),))

    def _row_values(self, it):
        disp = ''
        if it['rel']:
            parent = PurePosixPath(it['rel']).parent
            if str(parent) not in ('.', ''):
                disp = parent.as_posix() + '/'
        disp += it['base'] + (it['new_ext'] or '')
        size = '—' if it['is_new'] else human_size(it['size'])
        return (disp, it['orig_ext'] or '—', it['new_ext'] or '—',
                size, self._state_text(it))

    def _state_text(self, it):
        if it['is_new']:
            return 'جديد'
        if it['content'] is not None:
            return 'نص محفوظ'
        if it['new_ext'] != it['orig_ext']:
            return 'أُعيدت الصيغة'
        return '—'

    def _tag_for(self, it):
        if it['is_new']:
            return 'new'
        if it['content'] is not None:
            return 'edited'
        if it['new_ext'] != it['orig_ext']:
            return 'renamed'
        return ''

    def _refresh_row(self, it):
        if self.tree.exists(it['id']):
            self.tree.item(it['id'], values=self._row_values(it), tags=(self._tag_for(it),))

    def remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            self.set_status("حدّد عنصرًا أو أكثر للإزالة من القائمة.")
            return
        for iid in sel:
            self.tree.delete(iid)
            it = self.items_by_id.pop(iid, None)
            if it is not None:
                if it in self.items:
                    self.items.remove(it)
                if it['src']:
                    self._known.discard((os.path.abspath(it['src']), it['rel']))
        if self.current is not None and self.current['id'] not in self.items_by_id:
            self.current = None
            self._reset_editor()
        self._update_count()
        self.set_status(f"أُزيل {len(sel)} عنصر من القائمة (الملفات على القرص لم تُمس).")

    def clear_all(self):
        if not self.items:
            return
        if not messagebox.askyesno(APP_TITLE, "تفريغ القائمة بالكامل؟\n(الملفات على القرص لن تُمس)"):
            return
        self._stash_editor()
        for iid in list(self.tree.get_children()):
            self.tree.delete(iid)
        self.items.clear()
        self.items_by_id.clear()
        self._known.clear()
        self.current = None
        self._reset_editor()
        self._update_count()
        self.set_status("تم تفريغ القائمة.")

    # ────────────────────────── ملف جديد ──────────────────────────

    def new_file_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("ملف جديد")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        frm = ttk.Frame(win, padding=18)
        frm.pack(fill='both', expand=True)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="اسم الملف:").grid(row=0, column=0, sticky='e', pady=6, padx=(0, 8))
        name_ev = ttk.Entry(frm, width=30)
        name_ev.grid(row=0, column=1, sticky='ew', pady=6)

        ttk.Label(frm, text="الامتداد:").grid(row=1, column=0, sticky='e', pady=(0, 6), padx=(0, 8))
        ext_cb = ttk.Combobox(frm, width=27, values=[
            '.txt', '.js', '.py', '.html', '.css', '.json', '.c', '.cpp', '.h',
            '.md', '.csv', '.xml', '.bat', '.sh', '.java', '.log'])
        ext_cb.set('.txt')
        ext_cb.grid(row=1, column=1, sticky='ew', pady=(0, 6))

        ttk.Label(frm, text="يمكنك كتابة الامتداد ضمن الاسم (index.html) وسيُفصل تلقائيًا.",
                  style='Status.TLabel').grid(row=2, column=0, columnspan=2, sticky='e')

        def create(event=None):
            name = name_ev.get().strip()
            base, ext = name, self._norm_ext(ext_cb.get())
            if '.' in name:
                b, e = os.path.splitext(name)
                if b:
                    base = b
                if e:
                    ext = self._norm_ext(e) or ext
            if not base:
                messagebox.showwarning(APP_TITLE, "اكتب اسم الملف أولًا.", parent=win)
                return
            if not ext:
                ext = '.txt'
            it = {'id': self._new_id(), 'src': None, 'rel': '', 'base': base,
                  'orig_ext': ext, 'new_ext': ext, 'size': 0,
                  'content': '', 'loaded_text': '', 'is_new': True}
            self._insert_item(it)
            self._update_count()
            win.destroy()
            self.tree.selection_set(it['id'])
            self.tree.see(it['id'])
            self.set_status(f"أُنشئ «{base}{ext}» — اكتب محتواه ثم صدّره لحفظه على القرص.")

        ttk.Button(frm, text="إنشاء", style='Accent.TButton',
                   command=create).grid(row=3, column=0, columnspan=2, pady=(14, 0))
        name_ev.bind('<Return>', create)
        name_ev.focus_set()
        self._center_over(win)

    # ────────────────────────── المحرر ──────────────────────────

    def _on_tree_select(self, event=None):
        self._stash_editor()
        sel = self.tree.selection()
        if not sel:
            return
        it = self.items_by_id.get(sel[0])
        if it is None:
            return
        self.current = it
        self.ext_var.set(it['new_ext'].lstrip('.'))
        self._load_editor(it)

    def _load_editor(self, it):
        self.editor.configure(state='normal')
        self.editor.delete('1.0', 'end')

        readable = it['is_new'] or it['orig_ext'] in TEXT_EXTS or it['new_ext'] in TEXT_EXTS
        if it['content'] is not None:
            self.editor.insert('1.0', it['content'])
            it['loaded_text'] = it['content']
            self.editor_editable = True
        elif it['is_new']:
            it['content'] = ''
            it['loaded_text'] = ''
            self.editor_editable = True
        elif not readable:
            self.editor.insert('1.0',
                "ملف ثنائي (صورة / فيديو / صوت / برنامج …).\n\n"
                "المحرر لا يعرض محتواه، لكن يمكنك:\n"
                "  • تغيير امتداده من حقل «صيغة المحدد» — المحتوى لا يتأثر إطلاقًا.\n"
                "  • تصديره بالصيغة الجديدة من «تصدير المحدد باسم…» أو «تصدير الكل».")
            self.editor_editable = False
        elif it['size'] > MAX_TEXT_BYTES:
            self.editor.insert('1.0',
                f"الملف نصي لكن حجمه ({human_size(it['size'])}) أكبر من حد التحميل التلقائي (2.0 MB).\n"
                "يمكنك تغيير امتداده وتصديره طبيعيًا دون مشكلة.")
            self.editor_editable = False
        else:
            try:
                text = Path(it['src']).read_text(encoding='utf-8', errors='replace')
            except Exception as e:
                self.editor.insert('1.0', f"تعذّرت قراءة الملف:\n{e}")
                self.editor_editable = False
            else:
                self.editor.insert('1.0', text)
                it['loaded_text'] = text
                self.editor_editable = True

        self.editor.configure(state='normal' if self.editor_editable else 'disabled')
        self.editor.edit_reset()
        a = it['orig_ext'] or 'بدون'
        b = it['new_ext'] or 'بدون'
        self.editor_info_var.set(f"الملف: {it['base']}{it['new_ext'] or ''}    ({a} ← {b})")

    def _stash_editor(self):
        """يحفظ ما في المحرر بالذاكرة تلقائيًا قبل التنقل — لا يضيع تعديل أبدًا."""
        it = self.current
        if it is None or not self.editor_editable:
            return
        text = self.editor.get('1.0', 'end-1c')
        if it['content'] is not None:
            if text != it['content']:
                it['content'] = text
                self._refresh_row(it)
        elif text != it['loaded_text']:
            it['content'] = text
            self._refresh_row(it)

    def save_text_buffer(self, event=None):
        if self.current is None:
            self.set_status("حدّد ملفًا من القائمة أولًا.")
            return 'break'
        if not self.editor_editable:
            self.set_status("الملف الحالي غير قابل للتحرير كنص.")
            return 'break'
        self.current['content'] = self.editor.get('1.0', 'end-1c')
        self._refresh_row(self.current)
        self.set_status("تم حفظ النص — سيُكتب في الملف عند التصدير.")
        return 'break'

    def save_to_source(self):
        it = self.current
        if it is None:
            self.set_status("حدّد ملفًا أولًا.")
            return
        if it['src'] is None:
            messagebox.showinfo(APP_TITLE,
                "هذا ملف جديد لم يُحفظ بعد.\nاستخدم «تصدير المحدد باسم…» لاختيار مكان حفظه.")
            return
        if not self.editor_editable:
            messagebox.showinfo(APP_TITLE, "الملف الحالي غير قابل للتحرير كنص داخل المحرر.")
            return
        if not messagebox.askyesno(APP_TITLE,
                f"سيتم استبدال محتوى الملف الأصلي:\n\n{it['src']}\n\nهل تريد المتابعة؟"):
            return
        text = self.editor.get('1.0', 'end-1c')
        try:
            Path(it['src']).write_text(text, encoding='utf-8')
            it['content'] = text
            it['loaded_text'] = text
            it['size'] = len(text.encode('utf-8'))
            self._refresh_row(it)
            self.set_status("تم حفظ النص على الملف الأصلي.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"فشل الحفظ:\n{e}")

    def open_location(self):
        it = self.current
        if it is None or it['src'] is None:
            messagebox.showinfo(APP_TITLE, "لا يوجد ملف أصلي على القرص لهذا العنصر.")
            return
        folder = str(Path(it['src']).parent)
        try:
            if sys.platform.startswith('win'):
                os.startfile(folder)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', folder])
            else:
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"تعذّر فتح الموقع:\n{e}")

    def _reset_editor(self):
        self.editor.configure(state='normal')
        self.editor.delete('1.0', 'end')
        self.editor.configure(state='disabled')
        self.editor_editable = False
        self.editor_info_var.set("لا يوجد ملف محدد")

    # ────────────────────────── تغيير الصيغة ──────────────────────────

    def _on_ext_typed(self, event=None):
        """تحديث فوري: تكتب الامتداد فيرى الاسم الجديد في القائمة لحظيًا."""
        ext = self._norm_ext(self.ext_var.get())
        for iid in self.tree.selection():
            it = self.items_by_id.get(iid)
            if it and it['new_ext'] != ext:
                it['new_ext'] = ext
                self._refresh_row(it)

    def apply_ext_selected(self):
        sel = self.tree.selection()
        if not sel:
            self.set_status("حدّد ملفًا أو أكثر من القائمة أولًا.")
            return
        self._stash_editor()
        ext = self._norm_ext(self.ext_var.get())
        for iid in sel:
            it = self.items_by_id.get(iid)
            if it:
                it['new_ext'] = ext
                self._refresh_row(it)
        if self.current and self.current['id'] in sel:
            self._load_editor(self.current)
        self.set_status(f"تم تطبيق الصيغة «{ext or 'بدون'}» على {len(sel)} ملف.")

    def apply_ext_all(self):
        if not self.items:
            self.set_status("القائمة فارغة — استورد ملفات أولًا.")
            return
        self._stash_editor()
        ext = self._norm_ext(self.all_ext_var.get())
        for it in self.items:
            it['new_ext'] = ext
            self._refresh_row(it)
        if self.current:
            self._load_editor(self.current)
        self.set_status(f"تم تغيير صيغة جميع الملفات ({len(self.items)}) إلى «{ext or 'بدون'}».")

    # ────────────────────────── التصدير ──────────────────────────

    def export_selected(self):
        sel = self.tree.selection()
        if not sel:
            self.set_status("حدّد ملفًا أولًا.")
            return
        self._stash_editor()
        it = self.items_by_id.get(sel[0])
        if it is None:
            return
        suggested = it['base'] + (it['new_ext'] or '')
        path = filedialog.asksaveasfilename(
            title="حفظ الملف باسم", initialfile=suggested,
            defaultextension=(it['new_ext'] or None))
        if not path:
            return
        try:
            self._write_item(it, Path(path))
            self.set_status(f"تم الحفظ: {path}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"فشل الحفظ:\n{e}")

    def export_all(self):
        if not self.items:
            messagebox.showinfo(APP_TITLE,
                "القائمة فارغة — استورد ملفات أو أنشئ ملفًا جديدًا أولًا.")
            return
        self._stash_editor()
        target = filedialog.askdirectory(
            title="اختر مجلد التصدير (ستُحفظ كل الملفات بالصيغ الجديدة)")
        if not target:
            return
        target = Path(target)
        replace = None
        made, errors = 0, []
        for it in self.items:
            sub = PurePosixPath('')
            if it['rel']:
                parent = PurePosixPath(it['rel']).parent
                if str(parent) != '.':
                    sub = parent
            dst = target.joinpath(*sub.parts) / (it['base'] + (it['new_ext'] or ''))
            try:
                if dst.exists():
                    if replace is None:
                        replace = messagebox.askyesno(APP_TITLE,
                            "توجد ملفات بنفس الاسم في مجلد التصدير.\n\n"
                            "«نعم» = استبدال الموجودة\n«لا» = إضافة رقم بين قوسين بدل الاستبدال")
                    if not replace:
                        i = 1
                        while True:
                            if dst.suffix:
                                cand = dst.with_name(f"{dst.stem} ({i}){dst.suffix}")
                            else:
                                cand = dst.with_name(f"{dst.stem} ({i})")
                            if not cand.exists():
                                dst = cand
                                break
                            i += 1
                self._write_item(it, dst)
                made += 1
            except Exception as e:
                errors.append(f"• {dst.name}: {e}")
        if errors:
            messagebox.showwarning(APP_TITLE,
                f"تم حفظ {made} ملف، وفشل:\n" + "\n".join(errors[:10]))
        else:
            messagebox.showinfo(APP_TITLE, f"تم حفظ {made} ملف في:\n{target}")
        self.set_status(f"التصدير انتهى — {made} ملف.")

    def _write_item(self, it, dst):
        dst.parent.mkdir(parents=True, exist_ok=True)
        if it['content'] is not None or it['src'] is None:
            dst.write_text(it['content'] or '', encoding='utf-8')
        else:
            shutil.copy2(it['src'], dst)  # نسخ البايتات كما هي — المحتوى لا يتغير


def main():
    if DND_OK:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    FileForge(root)
    root.mainloop()


if __name__ == '__main__':
    main()
