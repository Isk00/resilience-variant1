import json, os, threading, time, urllib.error, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

DEP_URL = os.environ.get("DEP_URL", "http://dep-a")
PATTERN = os.environ.get("PATTERN", "off") == "on"
COUNT = {}
LOCK = threading.Lock()

def inc(name):
    with LOCK:
        COUNT[name] = COUNT.get(name, 0) + 1

def call_dep(timeout=10.0):
    with urllib.request.urlopen(DEP_URL + "/work", timeout=timeout) as r:
        return json.loads(r.read())

# --- паттерн варианта 1: георезервирование станций + failover dep-a -> dep-b ---
DEP_URL_B = os.environ.get("DEP_URL_B", "http://dep-b")       # резервная станция
TIMEOUT = float(os.environ.get("TIMEOUT_S", "0.5"))           # сколько ждём dep-a
FAILBACK = float(os.environ.get("FAILBACK_S", "10"))          # сколько не трогаем dep-a после отказа
a_down_until = 0.0                                            # до какого момента dep-a считается сломанной

def call_dep_b(timeout=10.0):
    with urllib.request.urlopen(DEP_URL_B + "/work", timeout=timeout) as r:
        return json.loads(r.read())

def do_work():
    global a_down_until
    if not PATTERN:
        return call_dep()                      # без меры: ждём dep до 10 с
    # 1. основная станция, если она не помечена как сломанная
    if time.time() >= a_down_until:
        try:
            r = call_dep(timeout=TIMEOUT)
            inc('dep_calls_total{target="a"}')
            return r
        except Exception:
            a_down_until = time.time() + FAILBACK   # FAILBACK секунд идём сразу в dep-b
            inc('failover_total')
    # 2. резервная станция
    r = call_dep_b(timeout=TIMEOUT)
    inc('dep_calls_total{target="b"}')
    return r

class H(BaseHTTPRequestHandler):
    def reply(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path == "/health":
            return self.reply(200, {"ok": True})
        if self.path == "/metrics":
            with LOCK:
                text = "".join(f"{k} {v}\n" for k, v in sorted(COUNT.items()))
            return self.reply(200, text, "text/plain")
        if self.path == "/work":
            try:
                body, code = do_work(), 200
            except Exception as e:
                body, code = {"error": str(e)}, 500
            inc(f'requests_total{{code="{code}"}}')
            return self.reply(code, body)
        self.reply(404, {})

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    ThreadingHTTPServer(("", int(os.environ.get("PORT", "8080"))), H).serve_forever()
