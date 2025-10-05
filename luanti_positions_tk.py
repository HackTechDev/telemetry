#!/usr/bin/env python3
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import ThreadingMixIn
from typing import Dict, Tuple

import tkinter as tk
from tkinter import ttk, messagebox

HOST = "127.0.0.1"
PORT = 8080
ENDPOINT = "/collect"  # must match your Luanti mod

# ---------- Shared state ----------
positions_lock = threading.Lock()
# name -> (x, y, z, last_update_epoch)
positions: Dict[str, Tuple[float, float, float, float]] = {}

# ---------- HTTP server ----------
class CollectHandler(BaseHTTPRequestHandler):
    server_version = "LuantiCollect/1.0"

    def do_POST(self):
        if self.path != ENDPOINT:
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"invalid json")
            return

        # Expected: {type:"players_pos", data:[{name,x,y,z},...], t:epoch}
        if not isinstance(payload, dict) or payload.get("type") != "players_pos":
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"unexpected payload")
            return

        now = time.time()
        data = payload.get("data") or []
        if isinstance(data, list):
            with positions_lock:
                for item in data:
                    try:
                        name = str(item["name"])
                        x = float(item["x"])
                        y = float(item["y"])
                        z = float(item["z"])
                    except Exception:
                        continue
                    positions[name] = (x, y, z, now)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, fmt, *args):
        # Quiet the server; uncomment for debugging
        # sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt%args))
        return

def start_server_in_thread():
    httpd = ThreadingHTTPServer((HOST, PORT), CollectHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, t

# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Luanti - Positions des joueurs")
        self.geometry("820x560")
        self.minsize(700, 480)

        # Top frame: table + controls
        top = ttk.Frame(self, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)

        self.status_var = tk.StringVar(value=f"Écoute sur http://{HOST}:{PORT}{ENDPOINT}")
        ttk.Label(top, textvariable=self.status_var).pack(side=tk.LEFT)

        self.clear_btn = ttk.Button(top, text="Effacer inactifs (>60s)", command=self.clear_stale)
        self.clear_btn.pack(side=tk.RIGHT, padx=(8,0))

        # Middle: Treeview
        mid = ttk.Frame(self, padding=(8,0,8,8))
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        columns = ("name","x","y","z","age")
        self.tree = ttk.Treeview(mid, columns=columns, show="headings", height=6)
        self.tree.heading("name", text="Joueur")
        self.tree.heading("x", text="X")
        self.tree.heading("y", text="Y")
        self.tree.heading("z", text="Z")
        self.tree.heading("age", text="Âge (s)")
        self.tree.column("name", width=160, anchor=tk.W)
        for c in ("x","y","z","age"):
            self.tree.column(c, width=90, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        # Bottom: Canvas map (top-down X/Z)
        bottom = ttk.LabelFrame(self, text="Carte (vue de dessus X/Z)", padding=8)
        bottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(bottom, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Periodic updates
        self.after(200, self.refresh_ui)

    def clear_stale(self):
        cutoff = time.time() - 60.0
        removed = []
        with positions_lock:
            for k, (_, _, _, ts) in list(positions.items()):
                if ts < cutoff:
                    removed.append(k)
                    positions.pop(k, None)
        messagebox.showinfo("Nettoyage", f"{len(removed)} joueur(s) supprimé(s) pour inactivité.")

    def refresh_ui(self):
        # Update table
        with positions_lock:
            snapshot = dict(positions)

        existing = set(self.tree.get_children())
        # Map row id by player name for reuse
        row_by_name = {}
        for iid in existing:
            vals = self.tree.item(iid, "values")
            if vals:
                row_by_name[vals[0]] = iid

        # Insert/update rows
        now = time.time()
        seen = set()
        for name, (x,y,z,ts) in snapshot.items():
            age = max(0.0, now - ts)
            values = (name, f"{x:.1f}", f"{y:.1f}", f"{z:.1f}", f"{age:.1f}")
            if name in row_by_name:
                self.tree.item(row_by_name[name], values=values)
                seen.add(row_by_name[name])
            else:
                iid = self.tree.insert("", tk.END, values=values)
                seen.add(iid)

        # Remove rows not in snapshot
        for iid in list(existing - seen):
            self.tree.delete(iid)

        # Redraw map
        self.draw_map(snapshot)

        # schedule next
        self.after(500, self.refresh_ui)

    def draw_map(self, snapshot: Dict[str, Tuple[float,float,float,float]]):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return

        # axis margins
        margin = 40
        plot_w = max(10, w - 2*margin)
        plot_h = max(10, h - 2*margin)

        # compute bounds from X/Z
        xs = [v[0] for v in snapshot.values()]
        zs = [v[2] for v in snapshot.values()]
        if not xs or not zs:
            # draw axes
            self._draw_axes(margin, plot_w, margin, plot_h, w, h)
            self._canvas_text_center(w//2, h//2, "En attente de données...", fill="#cccccc")
            return

        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)
        # Expand bounds a bit
        pad_x = (max(5.0, (max_x - min_x) * 0.1))
        pad_z = (max(5.0, (max_z - min_z) * 0.1))
        min_x -= pad_x; max_x += pad_x
        min_z -= pad_z; max_z += pad_z

        # Avoid zero division
        span_x = max(1e-6, max_x - min_x)
        span_z = max(1e-6, max_z - min_z)

        # Helper to map world -> canvas
        def map_x(x): return margin + (x - min_x) / span_x * plot_w
        def map_z(z): return margin + (max_z - z) / span_z * plot_h  # invert so +Z is up

        # axes + grid
        self._draw_axes(margin, plot_w, margin, plot_h, w, h)

        # Draw players
        for name, (x,y,z,ts) in snapshot.items():
            cx = map_x(x)
            cz = map_z(z)
            r = 6
            self.canvas.create_oval(cx-r, cz-r, cx+r, cz+r, fill="#00d3ff", outline="")
            self.canvas.create_text(cx+10, cz, anchor="w", text=f"{name}  ({x:.0f},{z:.0f})", fill="#e8e8e8", font=("TkDefaultFont", 9))

        # Draw bounds text
        self.canvas.create_text(margin, h-margin+18, anchor="w", text=f"X: {min_x:.0f} .. {max_x:.0f}", fill="#aaaaaa")
        self.canvas.create_text(w-margin, margin-18, anchor="e", text=f"Z: {max_z:.0f} .. {min_z:.0f}", fill="#aaaaaa")

    def _draw_axes(self, mx, pw, my, ph, w, h):
        # Border
        self.canvas.create_rectangle(mx, my, mx+pw, my+ph, outline="#3a3a3a")
        # Center cross
        cx = mx + pw/2
        cy = my + ph/2
        self.canvas.create_line(cx, my, cx, my+ph, fill="#2b2b2b", dash=(3,3))
        self.canvas.create_line(mx, cy, mx+pw, cy, fill="#2b2b2b", dash=(3,3))
        # Labels
        self.canvas.create_text(mx+pw/2, my-12, text="X (est/ouest)", fill="#b0b0b0")
        self.canvas.create_text(mx-30, my+ph/2, text="Z (nord/sud)", fill="#b0b0b0", angle=90)

    def _canvas_text_center(self, x, y, text, **kwargs):
        # Petit helper pour écrire du texte centré sur le canvas
        self.canvas.create_text(x, y, text=text, anchor="center", **kwargs)

def main():
    httpd, thread = start_server_in_thread()
    app = App()

    def on_close():
        try:
            httpd.shutdown()
        except Exception:
            pass
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()

if __name__ == "__main__":
    main()
