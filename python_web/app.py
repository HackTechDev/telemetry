#!/usr/bin/env python3
import json, time, queue, threading
from typing import Dict, Tuple, List
from flask import Flask, request, Response, render_template, jsonify

HOST = "127.0.0.1"
PORT = 8080
ENDPOINT = "/collect"

app = Flask(__name__)

positions_lock = threading.Lock()
positions: Dict[str, Tuple[float, float, float, float]] = {}

listeners_lock = threading.Lock()
listeners: List[queue.Queue] = []

def broadcast_snapshot():
    with positions_lock:
        snapshot = {k: {"x": v[0], "y": v[1], "z": v[2], "ts": v[3]} for k, v in positions.items()}
    data = json.dumps({"type": "players_pos", "t": time.time(), "data": snapshot})
    with listeners_lock:
        dead = []
        for q in listeners:
            try:
                q.put_nowait(data)
            except Exception:
                dead.append(q)
        for q in dead:
            try:
                listeners.remove(q)
            except ValueError:
                pass

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/positions")
def api_positions():
    with positions_lock:
        snapshot = {k: {"x": v[0], "y": v[1], "z": v[2], "ts": v[3]} for k, v in positions.items()}
    return jsonify(snapshot)

@app.route("/stream")
def stream():
    q = queue.Queue(maxsize=100)
    with listeners_lock:
        listeners.append(q)
    def event_stream():
        try:
            yield "event: snapshot\ndata: {}\n\n"
            while True:
                try:
                    data = q.get(timeout=15)
                    yield f"event: positions\ndata: {data}\n\n"
                except queue.Empty:
                    yield ": ping\n\n"
        finally:
            with listeners_lock:
                try:
                    listeners.remove(q)
                except ValueError:
                    pass
    return Response(event_stream(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    })

@app.post(ENDPOINT)
def collect():
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return ("invalid json", 400)
    if not isinstance(payload, dict) or payload.get("type") != "players_pos":
        return ("unexpected payload", 400)
    now = time.time()
    arr = payload.get("data") or []
    if isinstance(arr, list):
        with positions_lock:
            for item in arr:
                try:
                    name = str(item["name"])
                    x = float(item["x"])
                    y = float(item["y"])
                    z = float(item["z"])
                except Exception:
                    continue
                positions[name] = (x, y, z, now)
    broadcast_snapshot()
    return ("ok", 200)

def run():
    app.run(host=HOST, port=PORT, debug=False, threaded=True)

if __name__ == "__main__":
    run()
