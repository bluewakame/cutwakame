"""AI-friendly local video editor: shared project model, GUI, and MCP server."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
import tempfile
from pathlib import Path

APP = "カットワカメ"
VERSION = "0.2.0"


def binary(name):
    bundled = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "bin" / (name + ".exe")
    return str(bundled) if bundled.exists() else (shutil.which(name) or name)


def probe(path):
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise ValueError(f"Media file not found: {p}")
    result = subprocess.run([binary("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(p)], capture_output=True, text=True, check=True)
    duration = float(json.loads(result.stdout)["format"]["duration"])
    if duration <= 0:
        raise ValueError("Media duration must be positive")
    return str(p), duration


class Project:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        self.data = {"version": 2, "name": self.path.stem, "clips": [], "titles": [], "export": {"width": 1280, "height": 720, "fps": 30, "crf": 20}}
        self.lock = threading.RLock()
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.validate()

    def validate(self):
        if self.data.get("version") not in (1, 2) or not isinstance(self.data.get("clips"), list):
            raise ValueError("Unsupported project format")
        self.data.setdefault("titles", [])
        self.data.setdefault("export", {"width": 1280, "height": 720, "fps": 30, "crf": 20})
        for clip in self.data["clips"]:
            if not 0 <= clip["start"] < clip["end"] <= clip["duration"] + 0.01:
                raise ValueError(f"Invalid trim for clip {clip.get('id')}")

    def reload(self):
        with self.lock:
            if self.path.exists():
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
                self.validate()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def summary(self):
        with self.lock:
            return {**self.data, "project_path": str(self.path), "timeline_duration": round(sum(c["end"] - c["start"] for c in self.data["clips"]), 3)}

    def add(self, path, start=0, end=None, index=None):
        source, duration = probe(path)
        end = duration if end is None else float(end)
        start = float(start)
        if not 0 <= start < end <= duration + 0.01:
            raise ValueError("Trim must be within source duration")
        clip = {"id": uuid.uuid4().hex[:12], "path": source, "duration": duration, "start": start, "end": min(end, duration)}
        with self.lock:
            clips = self.data["clips"]
            if index is None:
                clips.append(clip)
            elif 0 <= int(index) <= len(clips):
                clips.insert(int(index), clip)
            else:
                raise ValueError("Index out of range")
            self.save()
        return clip

    def find(self, clip_id):
        for i, clip in enumerate(self.data["clips"]):
            if clip["id"] == clip_id:
                return i, clip
        raise ValueError(f"Clip not found: {clip_id}")

    def trim(self, clip_id, start, end):
        with self.lock:
            _, clip = self.find(clip_id)
            start, end = float(start), float(end)
            if not 0 <= start < end <= clip["duration"] + 0.01:
                raise ValueError("Trim must be within source duration")
            clip.update(start=start, end=min(end, clip["duration"]))
            self.save()
            return clip

    def remove(self, clip_id):
        with self.lock:
            i, clip = self.find(clip_id)
            self.data["clips"].pop(i)
            self.save()
            return clip

    def move(self, clip_id, index):
        with self.lock:
            i, clip = self.find(clip_id)
            index = int(index)
            if not 0 <= index < len(self.data["clips"]):
                raise ValueError("Index out of range")
            self.data["clips"].pop(i)
            self.data["clips"].insert(index, clip)
            self.save()
            return clip

    def split(self, clip_id, at):
        with self.lock:
            i, clip = self.find(clip_id)
            at = float(at)
            if not clip["start"] < at < clip["end"]:
                raise ValueError("Split point must be inside the clip")
            right = dict(clip)
            right["id"] = uuid.uuid4().hex[:12]
            right["start"] = at
            clip["end"] = at
            self.data["clips"].insert(i + 1, right)
            self.save()
            return {"left": clip, "right": right}

    def duplicate(self, clip_id):
        with self.lock:
            i, clip = self.find(clip_id)
            copy = dict(clip)
            copy["id"] = uuid.uuid4().hex[:12]
            self.data["clips"].insert(i + 1, copy)
            self.save()
            return copy

    def add_title(self, text, start, end, x=0.5, y=0.82, size=52, color="#ffffff"):
        start, end, x, y, size = float(start), float(end), float(x), float(y), int(size)
        if not text or not 0 <= start < end or not 0 <= x <= 1 or not 0 <= y <= 1 or not 12 <= size <= 150:
            raise ValueError("Invalid title text, timing, position, or size")
        if len(color) != 7 or not color.startswith("#"):
            raise ValueError("Color must be #RRGGBB")
        int(color[1:], 16)
        title = {"id": uuid.uuid4().hex[:12], "text": text, "start": start, "end": end, "x": x, "y": y, "size": size, "color": color}
        with self.lock:
            self.data["titles"].append(title)
            self.save()
        return title

    def remove_title(self, title_id):
        with self.lock:
            for i, title in enumerate(self.data["titles"]):
                if title["id"] == title_id:
                    self.data["titles"].pop(i)
                    self.save()
                    return title
        raise ValueError(f"Title not found: {title_id}")

    def set_export(self, width=1280, height=720, fps=30, crf=20):
        width, height, fps, crf = int(width), int(height), int(fps), int(crf)
        if not (320 <= width <= 3840 and 240 <= height <= 2160 and width % 2 == 0 and height % 2 == 0 and 15 <= fps <= 60 and 15 <= crf <= 30):
            raise ValueError("Invalid export settings")
        with self.lock:
            self.data["export"] = {"width": width, "height": height, "fps": fps, "crf": crf}
            self.save()
        return self.data["export"]

    def export(self, output):
        with self.lock:
            clips = [dict(c) for c in self.data["clips"]]
            titles = [dict(t) for t in self.data["titles"]]
            settings = dict(self.data["export"])
        if not clips:
            raise ValueError("Add a clip before export")
        out = Path(output).expanduser().resolve()
        if out.suffix.lower() != ".mp4":
            raise ValueError("Output must be an .mp4 file")
        if any(out == Path(c["path"]) for c in clips):
            raise ValueError("Output cannot overwrite source media")
        out.parent.mkdir(parents=True, exist_ok=True)
        total = sum(c["end"] - c["start"] for c in clips)
        w, h, fps, crf = (settings[k] for k in ("width", "height", "fps", "crf"))
        with tempfile.TemporaryDirectory(dir=out.parent) as temp:
            args = [binary("ffmpeg"), "-hide_banner", "-y"]
            for c in clips:
                args += ["-ss", str(c["start"]), "-t", str(c["end"] - c["start"]), "-i", c["path"]]
            active_titles = [t for t in titles if t["start"] < total and t["end"] > 0]
            if active_titles:
                from PIL import Image, ImageDraw, ImageFont
                fonts = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "meiryo.ttc", Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf", Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
                font_path = next((p for p in fonts if p.exists()), None)
                for i, title in enumerate(active_titles):
                    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(image)
                    font = ImageFont.truetype(str(font_path), title["size"]) if font_path else ImageFont.load_default()
                    draw.text((int(w * title["x"]), int(h * title["y"])), title["text"], anchor="mm", font=font, fill=title["color"], stroke_width=3, stroke_fill="#10141c")
                    png = Path(temp) / f"title{i}.png"
                    image.save(png)
                    args += ["-loop", "1", "-framerate", str(fps), "-i", str(png)]
            filters = []
            for i in range(len(clips)):
                filters += [f"[{i}:v:0]fps={fps},scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{i}]"]
            # Missing audio is handled by creating a silent track for that input.
                info = subprocess.run([binary("ffprobe"), "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", clips[i]["path"]], capture_output=True, text=True, check=True)
                if info.stdout.strip():
                    filters += [f"[{i}:a:0]aresample=48000,asetpts=PTS-STARTPTS[a{i}]"]
                else:
                    filters += [f"anullsrc=r=48000:cl=stereo,atrim=duration={clips[i]['end']-clips[i]['start']}[a{i}]"]
            filters += ["".join(f"[v{i}][a{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=1[base][a]"]
            last = "base"
            for i, title in enumerate(active_titles):
                nxt = f"t{i}"
                filters += [f"[{last}][{len(clips)+i}:v]overlay=0:0:enable='between(t,{max(0,title['start'])},{min(total,title['end'])})':shortest=1[{nxt}]"]
                last = nxt
            args += ["-filter_complex", ";".join(filters), "-map", f"[{last}]", "-map", "[a]", "-t", str(total), "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr[-3000:])
        return {"output": str(out), "duration": total}


TOOLS = [
    ("get_project", "Read project and timeline", {}),
    ("add_clip", "Add a source video to timeline", {"path": "string", "start": "number", "end": "number", "index": "integer"}),
    ("trim_clip", "Set source in and out times", {"clip_id": "string", "start": "number", "end": "number"}),
    ("remove_clip", "Remove clip from timeline", {"clip_id": "string"}),
    ("move_clip", "Move clip to zero-based timeline index", {"clip_id": "string", "index": "integer"}),
    ("split_clip", "Split a clip at a source timestamp", {"clip_id": "string", "at": "number"}),
    ("duplicate_clip", "Duplicate a clip", {"clip_id": "string"}),
    ("add_title", "Place a timed text overlay on the composition", {"text": "string", "start": "number", "end": "number", "x": "number", "y": "number", "size": "integer", "color": "string"}),
    ("remove_title", "Remove a title overlay", {"title_id": "string"}),
    ("set_export", "Set composition width, height, frame rate and quality", {"width": "integer", "height": "integer", "fps": "integer", "crf": "integer"}),
    ("export_video", "Render timeline to MP4", {"output": "string"}),
]


def tool_specs():
    required = {"add_clip": ["path"], "trim_clip": ["clip_id", "start", "end"], "remove_clip": ["clip_id"], "move_clip": ["clip_id", "index"], "split_clip": ["clip_id", "at"], "duplicate_clip": ["clip_id"], "add_title": ["text", "start", "end"], "remove_title": ["title_id"], "export_video": ["output"]}
    return [{"name": name, "description": desc, "inputSchema": {"type": "object", "properties": {key: {"type": typ} for key, typ in fields.items()}, "required": required.get(name, [])}} for name, desc, fields in TOOLS]


def call(project, name, args):
    methods = {"get_project": lambda: project.summary(), "add_clip": lambda: project.add(**args), "trim_clip": lambda: project.trim(**args), "remove_clip": lambda: project.remove(**args), "move_clip": lambda: project.move(**args), "split_clip": lambda: project.split(**args), "duplicate_clip": lambda: project.duplicate(**args), "add_title": lambda: project.add_title(**args), "remove_title": lambda: project.remove_title(**args), "set_export": lambda: project.set_export(**args), "export_video": lambda: project.export(**args)}
    if name not in methods:
        raise ValueError(f"Unknown tool: {name}")
    return methods[name]()


def serve(project):
    for line in sys.stdin:
        try:
            msg = json.loads(line)
            if "id" not in msg:
                continue
            method = msg.get("method")
            if method == "initialize":
                result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "cutwakame", "version": VERSION}}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": tool_specs()}
            elif method == "tools/call":
                try:
                    p = msg.get("params", {})
                    value = call(project, p["name"], p.get("arguments", {}))
                    result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}
                except Exception as exc:
                    result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
            else:
                raise ValueError(f"Unknown method: {method}")
            reply = {"jsonrpc": "2.0", "id": msg["id"], "result": result}
        except Exception as exc:
            reply = {"jsonrpc": "2.0", "id": msg.get("id") if 'msg' in locals() else None, "error": {"code": -32603, "message": str(exc)}}
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def gui(project):
    from studio_tk import launch
    return launch(project)
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
    root = tk.Tk()
    root.title(f"{APP} — {project.data['name']}")
    root.geometry("900x550")
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Timeline", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    columns = ("source", "in", "out", "length")
    tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
    for c, title, width in zip(columns, ("Source", "In", "Out", "Length"), (550, 70, 70, 80)):
        tree.heading(c, text=title)
        tree.column(c, width=width)
    tree.pack(fill="both", expand=True, pady=10)
    status = tk.StringVar()
    ttk.Label(frame, textvariable=status).pack(anchor="w")

    def refresh():
        tree.delete(*tree.get_children())
        data = project.summary()
        for c in data["clips"]:
            tree.insert("", "end", iid=c["id"], values=(Path(c["path"]).name, f"{c['start']:.2f}", f"{c['end']:.2f}", f"{c['end']-c['start']:.2f}"))
        status.set(f"{len(data['clips'])} clips  •  {data['timeline_duration']:.2f} seconds  •  {project.path}")

    def selected():
        ids = tree.selection()
        return ids[0] if ids else None

    def action(fn):
        try:
            fn()
            refresh()
        except Exception as exc:
            messagebox.showerror(APP, str(exc))

    bar = ttk.Frame(frame)
    bar.pack(fill="x")

    def add():
        files = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All files", "*.*")])
        for path in files:
            project.add(path)

    def trim():
        cid = selected()
        if not cid: return
        _, c = project.find(cid)
        start = simpledialog.askfloat("Trim", "In (seconds)", initialvalue=c["start"], minvalue=0)
        if start is None: return
        end = simpledialog.askfloat("Trim", "Out (seconds)", initialvalue=c["end"], minvalue=0)
        if end is not None: project.trim(cid, start, end)

    def move(delta):
        cid = selected()
        if cid:
            i, _ = project.find(cid)
            project.move(cid, max(0, min(len(project.data["clips"])-1, i+delta)))
            refresh()
            tree.selection_set(cid)

    def export():
        path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 video", "*.mp4")])
        if not path: return
        status.set("Rendering video…")
        def worker():
            try:
                result = project.export(path)
                root.after(0, lambda: (refresh(), messagebox.showinfo(APP, f"Saved: {result['output']}")))
            except Exception as exc:
                root.after(0, lambda e=str(exc): (refresh(), messagebox.showerror(APP, e)))
        threading.Thread(target=worker, daemon=True).start()

    for label, fn in (("Add videos", add), ("Trim", trim), ("Remove", lambda: project.remove(selected()) if selected() else None), ("Move up", lambda: move(-1)), ("Move down", lambda: move(1)), ("Export MP4", export)):
        ttk.Button(bar, text=label, command=lambda f=fn: action(f) if f != export else f()).pack(side="left", padx=3)
    refresh()
    last_mtime = [project.path.stat().st_mtime_ns if project.path.exists() else 0]
    def poll():
        mtime = project.path.stat().st_mtime_ns if project.path.exists() else 0
        if mtime != last_mtime[0]:
            project.reload()
            refresh()
            last_mtime[0] = mtime
        root.after(1000, poll)
    root.after(1000, poll)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=APP)
    parser.add_argument("--project", default=str(Path.home() / "Documents" / "カットワカメ" / "Untitled.aicut.json"))
    parser.add_argument("--mcp", action="store_true", help="Run MCP stdio server")
    args = parser.parse_args()
    project = Project(args.project)
    if args.mcp: serve(project)
    else: gui(project)


if __name__ == "__main__":
    main()


