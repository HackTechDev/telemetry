#!/usr/bin/env python3
import json, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Tuple
import tkinter as tk
from tkinter import ttk, messagebox

HOST, PORT, ENDPOINT = "127.0.0.1", 8080, "/collect"
positions_lock = threading.Lock()
positions: Dict[str, Tuple[float,float,float,float]] = {}

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != ENDPOINT:
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get('Content-Length','0'))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode('utf-8'))
        except Exception:
            self.send_response(400); self.end_headers(); self.wfile.write(b'invalid json'); return
        if not isinstance(payload, dict) or payload.get('type') != 'players_pos':
            self.send_response(400); self.end_headers(); self.wfile.write(b'unexpected payload'); return
        now = time.time()
        for item in payload.get('data') or []:
            try:
                name = str(item['name']); x=float(item['x']); y=float(item['y']); z=float(item['z'])
            except Exception: continue
            with positions_lock:
                positions[name] = (x,y,z,now)
        self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
    def log_message(self, *a, **k): return

def start_server():
    httpd = ThreadingHTTPServer((HOST, PORT), H)
    t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()
    return httpd

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Luanti - TK (boussole + grille)'); self.geometry('900x640'); self.minsize(760,520)
        top=ttk.Frame(self,padding=8); top.pack(side=tk.TOP, fill=tk.X)
        self.status=tk.StringVar(value=f'Écoute sur http://{HOST}:{PORT}{ENDPOINT}')
        ttk.Label(top,textvariable=self.status).pack(side=tk.LEFT)
        ttk.Button(top,text='Effacer inactifs (>60s)', command=self.clear_stale).pack(side=tk.RIGHT, padx=(8,0))
        mid=ttk.Frame(self,padding=(8,0,8,8)); mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        cols=('name','x','y','z','age'); self.tree=ttk.Treeview(mid, columns=cols, show='headings', height=6)
        for c,lbl in zip(cols,['Joueur','X','Y','Z','Âge (s)']): self.tree.heading(c,text=lbl)
        self.tree.column('name', width=180, anchor=tk.W)
        for c in ('x','y','z','age'): self.tree.column(c, width=90, anchor=tk.CENTER)
        vs=ttk.Scrollbar(mid,orient='vertical',command=self.tree.yview); self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); vs.pack(side=tk.LEFT, fill=tk.Y)
        bottom=ttk.LabelFrame(self,text='Carte X/Z',padding=8); bottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.cv=tk.Canvas(bottom, bg='#0e121a', highlightthickness=0); self.cv.pack(fill=tk.BOTH, expand=True)
        self.after(200, self.tick)

    def clear_stale(self):
        cutoff=time.time()-60
        removed=[]
        with positions_lock:
            for k,(_,_,_,ts) in list(positions.items()):
                if ts < cutoff: positions.pop(k,None); removed.append(k)
        messagebox.showinfo('Nettoyage', f'{len(removed)} joueur(s) supprimé(s).')

    def tick(self):
        with positions_lock: snap=dict(positions)
        # table
        now=time.time(); have=set(); byname={}
        for iid in self.tree.get_children():
            v=self.tree.item(iid,'values')
            if v: byname[v[0]]=iid
        for name,(x,y,z,ts) in snap.items():
            age=max(0, now-ts); vals=(name,f'{x:.1f}',f'{y:.1f}',f'{z:.1f}',f'{age:.1f}')
            if name in byname: self.tree.item(byname[name], values=vals); have.add(byname[name])
            else: have.add(self.tree.insert('', tk.END, values=vals))
        for iid in set(self.tree.get_children())-have: self.tree.delete(iid)
        # map
        self.draw_map(snap)
        self.after(500, self.tick)

    def draw_map(self, snap):
        cv=self.cv; cv.delete('all'); w=cv.winfo_width(); h=cv.winfo_height()
        if w<10 or h<10: return
        margin=50; plot_w=max(10,w-2*margin); plot_h=max(10,h-2*margin)
        xs=[v[0] for v in snap.values()]; zs=[v[2] for v in snap.values()]
        # frame + fine grid + crosshair
        self._frame_grid(margin,plot_w,margin,plot_h)
        if not xs or not zs:
            cv.create_text(w//2,h//2,text='En attente de données...',fill='#cbd5e1')
            self._compass(w,h,margin); return
        min_x,max_x=min(xs),max(xs); min_z,max_z=min(zs),max(zs)
        pad_x=max(5,(max_x-min_x)*0.1); pad_z=max(5,(max_z-min_z)*0.1)
        min_x-=pad_x; max_x+=pad_x; min_z-=pad_z; max_z+=pad_z
        span_x=max(1e-6,max_x-min_x); span_z=max(1e-6,max_z-min_z)
        map_x=lambda x: margin+(x-min_x)/span_x*plot_w
        map_z=lambda z: margin+(max_z-z)/span_z*plot_h
        for name,(x,y,z,ts) in snap.items():
            cx,cz=map_x(x),map_z(z); r=6
            cv.create_oval(cx-r,cz-r,cx+r,cz+r,fill='#00d3ff',outline='')
            cv.create_text(cx+10,cz,anchor='w',text=f'{name}  ({x:.0f},{z:.0f})',fill='#e5e7eb',font=('TkDefaultFont',9))
        cv.create_text(margin+plot_w/2, margin-18, text='X (est/ouest)', fill='#aab2c5')
        cv.create_text(margin-24, margin+plot_h/2, text='Z (nord/sud)', fill='#aab2c5', angle=90)
        cv.create_text(margin, h-margin+18, anchor='w', text=f'X: {min_x:.0f} .. {max_x:.0f}', fill='#9aa1af')
        cv.create_text(w-margin, margin-18, anchor='e', text=f'Z: {max_z:.0f} .. {min_z:.0f}', fill='#9aa1af')
        self._compass(w,h,margin)

    def _frame_grid(self, mx,pw,my,ph):
        cv=self.cv
        cv.create_rectangle(mx,my,mx+pw,my+ph, outline='#3a445a')
        step=40
        x=mx
        while x<=mx+pw+1:
            cv.create_line(x,my,x,my+ph, fill='#202838'); x+=step
        y=my
        while y<=my+ph+1:
            cv.create_line(mx,y,mx+pw,y, fill='#202838'); y+=step
        cv.create_line(mx+pw/2, my, mx+pw/2, my+ph, fill='#2b3750', dash=(3,3))
        cv.create_line(mx, my+ph/2, mx+pw, my+ph/2, fill='#2b3750', dash=(3,3))

    def _compass(self, w,h,margin):
        cv=self.cv; r=36; cx=w - margin//2 - r; cy=margin//2 + r
        cv.create_oval(cx-r, cy-r, cx+r, cy+r, outline='#3a445a')
        cv.create_line(cx,cy-r, cx,cy-r+10, fill='#cbd5e1')
        cv.create_line(cx+r-10,cy, cx+r,cy, fill='#cbd5e1')
        cv.create_line(cx,cy+r-10, cx,cy+r, fill='#cbd5e1')
        cv.create_line(cx-r,cy, cx-r+10,cy, fill='#cbd5e1')
        cv.create_text(cx, cy-r-10, text='N', fill='#e5e7eb', font=('TkDefaultFont',10,'bold'))
        cv.create_text(cx+r+10, cy, text='E', fill='#e5e7eb', font=('TkDefaultFont',10,'bold'))
        cv.create_text(cx, cy+r+10, text='S', fill='#e5e7eb', font=('TkDefaultFont',10,'bold'))
        cv.create_text(cx-r-10, cy, text='O', fill='#e5e7eb', font=('TkDefaultFont',10,'bold'))

def main():
    httpd = start_server()
    app = App()
    def on_close():
        try: httpd.shutdown()
        except Exception: pass
        app.destroy()
    app.protocol('WM_DELETE_WINDOW', on_close)
    app.mainloop()

if __name__ == '__main__':
    main()
