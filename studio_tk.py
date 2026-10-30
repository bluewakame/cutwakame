"""カットワカメ: packaged timeline editor built on Tk."""
import io
import sys
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont

from PIL import Image, ImageTk
from aicut import binary

BG = "#151a22"
PANEL = "#202834"
INK = "#eef4f7"
MINT = "#52cda5"


class Studio:
    def __init__(self, project):
        self.project = project
        self.root = tk.Tk()
        self.root.title(f"カットワカメ — {project.data['name']}")
        self.root.geometry("1360x790")
        self.root.minsize(980, 650)
        self.selected = None
        self.preview_serial = 0
        self.playing = False
        self.source_time = 0.0
        self.image = None
        self.mtime = project.path.stat().st_mtime_ns if project.path.exists() else 0
        self.ui_font = tkfont.nametofont("TkDefaultFont").actual("family")
        self.style()
        self.layout()
        self.refresh()
        self.install_menu()
        self.root.after(1000, self.poll)

    def install_menu(self):
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="プロジェクトを開く…", command=self.open_project, accelerator="⌘O")
        file_menu.add_command(label="プロジェクトを別名で保存…", command=self.save_project_as, accelerator="⌘⇧S")
        file_menu.add_separator()
        file_menu.add_command(label="メディアを追加…", command=self.add_media)
        file_menu.add_command(label="MP4を書き出す…", command=self.export)
        menu.add_cascade(label="ファイル", menu=file_menu)
        self.root.configure(menu=menu)
        if sys.platform == "darwin":
            self.root.bind("<Command-o>", lambda event: self.open_project())
            self.root.bind("<Command-Shift-S>", lambda event: self.save_project_as())

    def open_project(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("カットワカメ", "*.aicut.json"), ("JSON", "*.json")])
        if not path:
            return
        def action():
            from aicut import Project
            project = Project(path)
            self.playing = False
            self.selected = None
            self.preview_serial += 1
            self.preview.delete("all")
            self.project = project
            self.root.title(f"カットワカメ — {project.data['name']}")
        self.attempt(action)

    def save_project_as(self):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".aicut.json", initialfile=self.project.path.name, filetypes=[("カットワカメ", "*.aicut.json")])
        if path:
            def action():
                from aicut import Project
                project = Project(path)
                project.data = self.project.summary()
                project.data.pop("project_path", None)
                project.data.pop("timeline_duration", None)
                project.save()
                self.project = project
            self.attempt(action)

    def style(self):
        self.root.configure(bg=BG)
        s = ttk.Style(self.root)
        s.theme_use("clam")
        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("TLabel", background=BG, foreground=INK, font=(self.ui_font, 10))
        s.configure("Panel.TLabel", background=PANEL, foreground=INK, font=(self.ui_font, 10))
        s.configure("Heading.TLabel", background=PANEL, foreground=INK, font=(self.ui_font, 13, "bold"))
        s.configure("Brand.TLabel", background=BG, foreground=MINT, font=(self.ui_font, 20, "bold"))
        s.configure("TButton", background="#344355", foreground=INK, padding=(9, 7), borderwidth=0)
        s.map("TButton", background=[("active", "#4b6077")])
        s.configure("Primary.TButton", background=MINT, foreground="#14221c", padding=(12, 8), borderwidth=0)
        s.map("Primary.TButton", background=[("active", "#80e1bf")])
        s.configure("Treeview", background="#111820", fieldbackground="#111820", foreground=INK, rowheight=30, borderwidth=0)
        s.map("Treeview", background=[("selected", "#2e7c67")])
        s.configure("TEntry", fieldbackground="#101720", foreground=INK)

    def label(self, parent, text, heading=False):
        return ttk.Label(parent, text=text, style="Heading.TLabel" if heading else "Panel.TLabel")

    def panel(self, parent, title):
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        self.label(frame, title, True).pack(anchor="w", pady=(0, 8))
        return frame

    def button(self, parent, text, command, primary=False):
        return ttk.Button(parent, text=text, command=command, style="Primary.TButton" if primary else "TButton")

    def layout(self):
        header = ttk.Frame(self.root, padding=(14, 12))
        header.pack(fill="x")
        ttk.Label(header, text="カットワカメ", style="Brand.TLabel").pack(side="left")
        ttk.Label(header, text="   EDIT  /  COMPOSE  /  EXPORT").pack(side="left")
        self.button(header, "書き出し", self.export, True).pack(side="right", padx=4)
        self.button(header, "＋ メディア追加", self.add_media).pack(side="right", padx=4)

        self.workspace = tk.PanedWindow(
            self.root, orient="vertical", bg=BG, sashwidth=9,
            sashrelief="raised", borderwidth=0, opaqueresize=True,
        )
        self.workspace.pack(fill="both", expand=True, padx=12, pady=4)
        top = ttk.Panedwindow(self.workspace, orient="horizontal")
        self.workspace.add(top, minsize=260, stretch="always")
        media = self.panel(top, "メディア")
        top.add(media, weight=2)
        self.media_tree = ttk.Treeview(media, columns=("length",), show="tree headings", selectmode="browse")
        self.media_tree.heading("#0", text="素材")
        self.media_tree.heading("length", text="長さ")
        self.media_tree.column("#0", width=205)
        self.media_tree.column("length", width=65, anchor="e")
        self.media_tree.pack(fill="both", expand=True)
        self.media_tree.bind("<<TreeviewSelect>>", self.pick_tree)
        self.label(media, "追加した順にタイムラインへ配置").pack(anchor="w", pady=6)

        center = self.panel(top, "プレビュー")
        top.add(center, weight=5)
        self.preview = tk.Canvas(center, bg="#070b11", highlightthickness=0, height=200)
        self.preview.pack(fill="both", expand=True)
        self.preview.create_text(300, 180, text="クリップを選択してください", fill="#93a4b4", font=(self.ui_font, 14))
        controls = ttk.Frame(center, style="Panel.TFrame")
        controls.pack(fill="x", pady=(8, 0))
        self.button(controls, "▶ / Ⅱ", self.toggle_play).pack(side="left")
        self.scrub = ttk.Scale(controls, from_=0, to=1, command=self.scrubbed)
        self.scrub.pack(side="left", fill="x", expand=True, padx=8)
        self.time_text = self.label(controls, "00:00 / 00:00")
        self.time_text.pack(side="right")
        self.label(center, "選択素材のフレームプレビュー（音声再生なし）").pack(anchor="w", pady=(5, 0))

        side = self.panel(top, "インスペクター")
        top.add(side, weight=2)
        tabs = ttk.Notebook(side)
        tabs.pack(fill="both", expand=True)
        clip_tab = ttk.Frame(tabs, style="Panel.TFrame", padding=8)
        text_tab = ttk.Frame(tabs, style="Panel.TFrame", padding=8)
        tabs.add(clip_tab, text="クリップ")
        tabs.add(text_tab, text="テキスト")
        side = clip_tab
        self.label(side, "選択クリップの範囲（秒）").pack(anchor="w")
        row = ttk.Frame(side, style="Panel.TFrame")
        row.pack(fill="x", pady=5)
        self.in_var = tk.StringVar(value="0.00")
        self.out_var = tk.StringVar(value="0.00")
        self.label(row, "IN").pack(side="left")
        ttk.Entry(row, textvariable=self.in_var, width=8).pack(side="left", padx=4)
        self.label(row, "OUT").pack(side="left")
        ttk.Entry(row, textvariable=self.out_var, width=8).pack(side="left", padx=4)
        self.button(side, "トリムを適用", self.trim).pack(fill="x", pady=3)
        actions = ttk.Frame(side, style="Panel.TFrame")
        actions.pack(fill="x", pady=3)
        for name, fn in (("✂ カット", self.split), ("複製", self.duplicate), ("削除", self.remove)):
            self.button(actions, name, fn).pack(side="left", expand=True, fill="x", padx=2)
        order = ttk.Frame(side, style="Panel.TFrame")
        order.pack(fill="x", pady=3)
        self.button(order, "← 前へ", lambda: self.move(-1)).pack(side="left", expand=True, fill="x", padx=2)
        self.button(order, "後ろへ →", lambda: self.move(1)).pack(side="left", expand=True, fill="x", padx=2)
        side = text_tab
        self.label(side, "テキストレイヤー").pack(anchor="w", pady=(16, 4))
        self.title_var = tk.StringVar()
        ttk.Entry(side, textvariable=self.title_var).pack(fill="x")
        times = ttk.Frame(side, style="Panel.TFrame")
        times.pack(fill="x", pady=5)
        self.start_var, self.end_var = tk.StringVar(value="0"), tk.StringVar(value="3")
        self.label(times, "開始").pack(side="left")
        ttk.Entry(times, textvariable=self.start_var, width=6).pack(side="left", padx=4)
        self.label(times, "終了").pack(side="left")
        ttk.Entry(times, textvariable=self.end_var, width=6).pack(side="left", padx=4)
        self.button(side, "＋ テキストを追加", self.add_title).pack(fill="x")
        self.title_list = tk.Listbox(side, height=4, bg="#111820", fg=INK, selectbackground="#765938", borderwidth=0)
        self.title_list.pack(fill="x", pady=5)
        self.button(side, "選択テキストを削除", self.remove_title).pack(fill="x")
        side = clip_tab
        self.label(side, "書き出しプリセット").pack(anchor="w", pady=(16, 4))
        self.preset = ttk.Combobox(side, state="readonly", values=["HD 720p", "Full HD 1080p", "縦動画 1080×1920"])
        self.preset.current(0)
        self.preset.pack(fill="x")
        self.preset.bind("<<ComboboxSelected>>", self.set_preset)

        timeline_box = self.panel(self.workspace, "タイムライン  ↕ 上の境界をドラッグして高さを変更")
        self.workspace.add(timeline_box, minsize=220, stretch="always")
        timeline_tools = ttk.Frame(timeline_box, style="Panel.TFrame")
        timeline_tools.pack(fill="x", pady=(0, 6))
        self.button(timeline_tools, "✂ カット", self.split, True).pack(side="left")
        self.label(timeline_tools, "選択クリップをプレビュー位置で分割").pack(side="left", padx=10)
        self.timeline = tk.Canvas(timeline_box, bg="#141c25", height=240, highlightthickness=0, xscrollincrement=20)
        self.timeline.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(timeline_box, orient="horizontal", command=self.timeline.xview)
        scrollbar.pack(fill="x")
        self.timeline.configure(xscrollcommand=scrollbar.set)
        self.timeline.bind("<Button-1>", self.pick_timeline)
        self.timeline.bind("<Configure>", lambda event: self.draw_timeline(self.project.summary()))
        self.root.after(150, self.initial_split)
        self.status = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status, padding=(12, 2)).pack(anchor="w")

    def initial_split(self):
        height = self.workspace.winfo_height()
        self.workspace.sash_place(0, 0, max(260, int(height * 0.60)))

    def attempt(self, fn):
        try:
            result = fn()
            self.refresh()
            return result
        except Exception as exc:
            messagebox.showerror("カットワカメ", str(exc), parent=self.root)

    def refresh(self):
        data = self.project.summary()
        self.media_tree.delete(*self.media_tree.get_children())
        for clip in data["clips"]:
            self.media_tree.insert("", "end", iid=clip["id"], text=Path(clip["path"]).name, values=(f"{clip['end']-clip['start']:.1f}s",))
        self.title_list.delete(0, "end")
        self.title_ids = []
        for title in data.get("titles", []):
            self.title_list.insert("end", f"{title['start']:.1f}–{title['end']:.1f}  {title['text']}")
            self.title_ids.append(title["id"])
        self.draw_timeline(data)
        self.status.set(f"{len(data['clips'])} クリップ  ·  {data['timeline_duration']:.1f}秒  ·  {self.project.path}")

    def draw_timeline(self, data):
        c = self.timeline
        c.delete("all")
        height = max(170, c.winfo_height())
        middle = 32 + (height - 32) // 2
        self.video_bottom = middle - 4
        width = max(c.winfo_width(), 1100, int(110 + data["timeline_duration"] * 65 + 80))
        c.configure(scrollregion=(0, 0, width, height))
        c.create_rectangle(0, 0, width, 30, fill="#232d39", outline="")
        c.create_rectangle(0, 32, 100, middle - 4, fill="#2b3947", outline="")
        c.create_rectangle(0, middle, 100, height - 4, fill="#2b3947", outline="")
        c.create_text(50, (32 + middle) / 2, text="VIDEO 1", fill=INK)
        c.create_text(50, (middle + height) / 2, text="TEXT 1", fill=INK)
        for sec in range(int(data["timeline_duration"]) + 2):
            x = 105 + sec * 65
            c.create_line(x, 30, x, height, fill="#354250")
            if sec % 5 == 0: c.create_text(x + 4, 15, anchor="w", text=f"{sec}s", fill="#abbcca")
        at = 0
        self.regions = []
        for clip in data["clips"]:
            x = 105 + at * 65
            length = max(12, (clip["end"] - clip["start"]) * 65)
            chosen = clip["id"] == self.selected
            c.create_rectangle(x + 2, 39, x + length - 2, middle - 9, fill="#438f79" if chosen else "#2e6e60", outline="#9df5d3" if chosen else MINT, width=2)
            c.create_text(x + 10, 58, anchor="w", text=Path(clip["path"]).name[:22], fill=INK)
            c.create_text(x + 10, 78, anchor="w", text=f"{clip['end']-clip['start']:.1f}s", fill="#c5eadd")
            self.regions.append((x, x + length, clip["id"]))
            at += clip["end"] - clip["start"]
        for title in data.get("titles", []):
            x = 105 + title["start"] * 65
            length = max(12, (title["end"] - title["start"]) * 65)
            c.create_rectangle(x + 2, middle + 6, x + length - 2, height - 10, fill="#72553a", outline="#f5bd77", width=2)
            c.create_text(x + 10, (middle + height) / 2, anchor="w", text=title["text"][:18], fill="#fff2de")

    def pick_timeline(self, event):
        x = self.timeline.canvasx(event.x)
        if 39 <= event.y <= self.video_bottom:
            for left, right, cid in self.regions:
                if left <= x < right:
                    self.select_clip(cid)
                    break

    def pick_tree(self, event):
        ids = self.media_tree.selection()
        if ids: self.select_clip(ids[0])

    def select_clip(self, cid):
        self.selected = cid
        _, clip = self.project.find(cid)
        self.in_var.set(f"{clip['start']:.2f}")
        self.out_var.set(f"{clip['end']:.2f}")
        self.source_time = clip["start"]
        self.scrub.configure(from_=clip["start"], to=clip["end"])
        self.scrub.set(clip["start"])
        self.refresh()
        self.request_frame()

    def request_frame(self):
        if not self.selected: return
        self.preview_serial += 1
        serial = self.preview_serial
        _, clip = self.project.find(self.selected)
        source, at = clip["path"], self.source_time
        def worker():
            try:
                cmd = [binary("ffmpeg"), "-v", "error", "-ss", str(at), "-i", source, "-frames:v", "1", "-vf", "scale=720:405:force_original_aspect_ratio=decrease,pad=720:405:(ow-iw)/2:(oh-ih)/2", "-f", "image2pipe", "-vcodec", "png", "pipe:1"]
                result = subprocess.run(cmd, capture_output=True, timeout=20, check=True)
                image = Image.open(io.BytesIO(result.stdout)).copy()
                self.root.after(0, lambda: self.show_frame(serial, image))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def show_frame(self, serial, image):
        if serial != self.preview_serial: return
        self.image = ImageTk.PhotoImage(image)
        self.preview.delete("all")
        self.preview.create_image(self.preview.winfo_width() // 2, self.preview.winfo_height() // 2, image=self.image)
        self.time_text.configure(text=f"{self.source_time:.2f}s")

    def scrubbed(self, value):
        if self.selected:
            self.source_time = float(value)
            if hasattr(self, "scrub_job"):
                self.root.after_cancel(self.scrub_job)
            self.scrub_job = self.root.after(130, self.request_frame)

    def toggle_play(self):
        self.playing = not self.playing
        if self.playing: self.play_step()

    def play_step(self):
        if not self.playing or not self.selected: return
        _, clip = self.project.find(self.selected)
        self.source_time += 0.2
        if self.source_time >= clip["end"]:
            self.playing = False
            return
        self.scrub.set(self.source_time)
        self.request_frame()
        self.root.after(200, self.play_step)

    def add_media(self):
        files = filedialog.askopenfilenames(parent=self.root, filetypes=[("動画", "*.mp4 *.mov *.mkv *.avi *.webm"), ("すべて", "*.*")])
        for path in files: self.attempt(lambda p=path: self.project.add(p))

    def trim(self):
        if self.selected:
            self.attempt(lambda: self.project.trim(self.selected, float(self.in_var.get()), float(self.out_var.get())))

    def split(self):
        if self.selected:
            self.attempt(lambda: self.project.split(self.selected, self.source_time))

    def duplicate(self):
        if self.selected: self.attempt(lambda: self.project.duplicate(self.selected))

    def remove(self):
        if self.selected:
            self.attempt(lambda: self.project.remove(self.selected))
            self.selected = None
            self.refresh()

    def move(self, delta):
        if self.selected:
            i, _ = self.project.find(self.selected)
            self.attempt(lambda: self.project.move(self.selected, max(0, min(len(self.project.data["clips"]) - 1, i + delta))))

    def add_title(self):
        text = self.title_var.get().strip()
        if text:
            self.attempt(lambda: self.project.add_title(text, float(self.start_var.get()), float(self.end_var.get())))
            self.title_var.set("")

    def remove_title(self):
        selected = self.title_list.curselection()
        if selected:
            self.attempt(lambda: self.project.remove_title(self.title_ids[selected[0]]))

    def set_preset(self, event=None):
        presets = [(1280, 720, 30, 20), (1920, 1080, 30, 20), (1080, 1920, 30, 20)]
        self.attempt(lambda: self.project.set_export(*presets[self.preset.current()]))

    def export(self):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if not path: return
        self.status.set("書き出し中…")
        def worker():
            try:
                self.project.export(path)
                self.root.after(0, lambda: (self.refresh(), messagebox.showinfo("書き出し完了", path, parent=self.root)))
            except Exception as exc:
                self.root.after(0, lambda e=str(exc): (self.refresh(), messagebox.showerror("書き出し失敗", e, parent=self.root)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        mtime = self.project.path.stat().st_mtime_ns if self.project.path.exists() else 0
        if mtime != self.mtime:
            self.project.reload()
            self.refresh()
            self.mtime = mtime
        self.root.after(1000, self.poll)

    def run(self):
        self.root.mainloop()


def launch(project):
    Studio(project).run()

