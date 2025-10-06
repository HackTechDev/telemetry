#!/usr/bin/env python3
import json, time, queue, threading
from typing import Dict, Tuple, List
from flask import Flask, request, Response, render_template, jsonify

HOST, PORT, ENDPOINT = '127.0.0.1', 8080, '/collect'
app = Flask(__name__)

positions_lock = threading.Lock()
positions: Dict[str, Tuple[float,float,float,float]] = {}
listeners_lock = threading.Lock()
listeners: List[queue.Queue] = []

def broadcast():
    with positions_lock:
        snap = {k:{'x':v[0],'y':v[1],'z':v[2],'ts':v[3]} for k,v in positions.items()}
    data = json.dumps({'type':'players_pos','t':time.time(),'data':snap})
    with listeners_lock:
        for q in list(listeners):
            try: q.put_nowait(data)
            except Exception:
                try: listeners.remove(q)
                except ValueError: pass

@app.get('/')
def index(): return render_template('index.html')

@app.get('/api/positions')
def api_positions():
    with positions_lock:
        snap = {k:{'x':v[0],'y':v[1],'z':v[2],'ts':v[3]} for k,v in positions.items()}
    return jsonify(snap)

@app.get('/stream')
def stream():
    q=queue.Queue(maxsize=100)
    with listeners_lock: listeners.append(q)
    def gen():
        try:
            while True:
                try:
                    data=q.get(timeout=15); yield f'event: positions\ndata: {data}\n\n'
                except queue.Empty:
                    yield ': ping\n\n'
        finally:
            with listeners_lock:
                try: listeners.remove(q)
                except ValueError: pass
    return Response(gen(), mimetype='text/event-stream', headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@app.post(ENDPOINT)
def collect():
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception: return ('invalid json', 400)
    if not isinstance(payload, dict) or payload.get('type')!='players_pos':
        return ('unexpected payload', 400)
    now=time.time()
    for item in payload.get('data') or []:
        try:
            name=str(item['name']); x=float(item['x']); y=float(item['y']); z=float(item['z'])
        except Exception: continue
        with positions_lock: positions[name]=(x,y,z,now)
    broadcast(); return ('ok',200)

def run(): app.run(host=HOST, port=PORT, debug=False, threaded=True)
if __name__=='__main__': run()
