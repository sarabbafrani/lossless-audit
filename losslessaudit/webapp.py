"""Local web interface.

Serves a page on 127.0.0.1 and opens it in the browser. Nothing leaves the
machine: files are read by this process, analysed, and the numbers go
straight back to the page in front of you.
"""

import http.server
import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser

from . import engine, i18n

PAGE = r"""<!doctype html>
<html lang="en" dir="ltr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lossless Audit</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --bg:#F4F2EA;--surface:#FFFFFF;--surface2:#EBE8DC;--ink:#16231C;--muted:#586A5F;
  --line:#D8D4C4;--gold:#856811;
  --excellent:#2B7A4B;--good:#8A6D14;--suspect:#B26A18;--poor:#A23C15;
  --mono:'IBM Plex Mono',ui-monospace,Menlo,monospace;
  --ui:'Vazirmatn',system-ui,-apple-system,'Segoe UI',sans-serif;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0D1411;--surface:#141E18;--surface2:#1B2721;--ink:#E3EAE3;--muted:#8DA095;
  --line:#27352D;--gold:#D6B04B;
  --excellent:#5CBD8D;--good:#D6B04B;--suspect:#E8A55D;--poor:#EA8A5D;
}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--ui);line-height:1.7}
.wrap{max-width:900px;margin:0 auto;padding-inline:18px;padding-block:32px 60px}
.ltr{direction:ltr;unicode-bidi:isolate;font-family:var(--mono)}

header{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;
  border-bottom:2px solid var(--ink);padding-bottom:16px;margin-bottom:26px;flex-wrap:wrap}
h1{font-size:25px;margin:0 0 4px;font-weight:700}
.sub{color:var(--muted);font-size:14px;margin:0;max-width:48ch}
.acts{display:flex;gap:8px;flex-wrap:wrap}
button{font-family:var(--ui);font-size:14px;cursor:pointer;border-radius:8px;
  border:1px solid var(--line);background:var(--surface);color:var(--ink);padding:8px 16px}
button:hover{border-color:var(--gold)}
button:focus-visible{outline:2px solid var(--gold);outline-offset:2px}

#drop{border:2px dashed var(--line);border-radius:14px;background:var(--surface);
  padding:42px 20px;text-align:center;transition:.15s;cursor:pointer}
#drop:hover,#drop.hot{border-color:var(--gold);background:var(--surface2)}
#dropTitle{font-size:18px;font-weight:700;margin-bottom:6px}
#dropHint{color:var(--muted);font-size:13.5px}
#file{display:none}

.folder{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.folder input{flex:1 1 240px;min-width:0;font-family:var(--mono);font-size:13px;
  direction:ltr;padding:8px 12px;border-radius:8px;border:1px solid var(--line);
  background:var(--surface);color:var(--ink)}

#status{margin-top:18px;color:var(--muted);font-size:14px;min-height:22px}
.bar{height:3px;background:var(--surface2);border-radius:2px;overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;background:var(--gold);width:0;transition:width .25s}

.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;
  padding:18px;margin-top:16px;display:grid;grid-template-columns:132px 1fr;gap:20px}
@media (max-width:620px){.card{grid-template-columns:1fr}}
.ring{width:132px;height:132px;display:block;margin-inline:auto}
.rbg{fill:none;stroke:var(--surface2);stroke-width:11}
.rfg{fill:none;stroke-width:11;stroke-linecap:round;transform:rotate(-90deg);transform-origin:60px 60px}
.rnum{font-family:var(--mono);font-size:31px;font-weight:500;text-anchor:middle}
.rof{font-family:var(--mono);font-size:10px;text-anchor:middle;fill:var(--muted)}
.gradelbl{text-align:center;font-weight:700;font-size:15px;margin-top:2px}

.fname{font-weight:700;font-size:16px;margin:0 0 2px;word-break:break-word}
.ftag{color:var(--muted);font-size:14px;margin:0 0 4px}
.meta{font-family:var(--mono);font-size:11.5px;color:var(--muted);
  direction:ltr;unicode-bidi:isolate;margin-bottom:12px}

.spec{width:100%;height:auto;display:block;background:var(--surface2);
  border-radius:8px;margin-bottom:14px}
.sline{fill:none;stroke:var(--gold);stroke-width:1.6}
.swall{stroke:var(--poor);stroke-width:1.4;stroke-dasharray:4 3}
.stxt{font-family:var(--mono);font-size:9px;fill:var(--muted)}

.parts{display:grid;gap:9px}
.part{display:grid;grid-template-columns:118px 1fr auto;gap:10px;align-items:center;font-size:13px}
@media (max-width:480px){.part{grid-template-columns:1fr;gap:2px}}
.pname{color:var(--muted)}
.ptrack{height:6px;background:var(--surface2);border-radius:3px;overflow:hidden}
.ptrack i{display:block;height:100%;border-radius:3px}
.pnote{font-size:12px;color:var(--muted);grid-column:1/-1;margin-top:-4px}
.pval{font-family:var(--mono);font-size:11.5px;color:var(--muted);
  white-space:nowrap;direction:ltr;unicode-bidi:isolate}

.card.bad{border-inline-start:4px solid var(--poor)}
footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);
  color:var(--muted);font-size:12.5px}
</style></head><body>
<div class="wrap">

<header>
  <div>
    <h1 id="title"></h1>
    <p class="sub" id="subtitle"></p>
  </div>
  <div class="acts">
    <button id="lang"></button>
    <button id="quit"></button>
  </div>
</header>

<div id="drop">
  <div id="dropTitle"></div>
  <div id="dropHint"></div>
</div>
<input type="file" id="file" multiple
  accept=".flac,.wav,.aiff,.aif,.ogg,.oga,.au,.caf,.w64">

<div class="folder">
  <input type="text" id="folder">
  <button id="scan"></button>
</div>

<div id="status"></div>
<div class="bar" id="barwrap" hidden><i id="bar"></i></div>
<div id="out"></div>

<footer id="legend"></footer>
</div>

<script>
const CATALOGUE = __CATALOGUE__;
const GRADE_COLOUR = {
  'grade.excellent':'var(--excellent)', 'grade.good':'var(--good)',
  'grade.suspect':'var(--suspect)', 'grade.poor':'var(--poor)'
};

let lang = 'en';
try { lang = localStorage.getItem('la.lang') || navigator.language.slice(0,2); } catch(e){}
if (!CATALOGUE[lang]) lang = 'en';

// Same substitution rule as i18n.fill() on the Python side.
function t(code, args){
  let s = (CATALOGUE[lang] && CATALOGUE[lang][code]) || CATALOGUE.en[code] || code;
  if (args) s = s.replace(/\{(\w+)\}/g, (m, k) => (k in args) ? args[k] : m);
  return s;
}
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const mb = b => (b/1048576).toFixed(1) + ' MB';
const clock = s => Math.floor(s/60) + ':' + String(Math.round(s%60)).padStart(2,'0');

const results = [];   // kept so a language switch re-renders without re-reading
let lastStatus = null;

function applyLanguage(){
  document.documentElement.lang = lang;
  document.documentElement.dir = (lang === 'fa') ? 'rtl' : 'ltr';
  document.title = t('ui.title');
  $('#title').textContent = t('ui.title');
  $('#subtitle').textContent = t('ui.sub');
  $('#dropTitle').textContent = t('ui.drop');
  $('#dropHint').textContent = t('ui.drophint');
  $('#folder').placeholder = t('ui.folder');
  $('#scan').textContent = t('ui.scan');
  $('#quit').textContent = t('ui.quit');
  $('#lang').textContent = t('ui.lang');
  $('#legend').textContent = t('ui.legend');
  $('#status').textContent = lastStatus ? t(lastStatus.code, lastStatus.args) : '';
  redraw();
}

function noteText(note){
  let s = t(note.code, note.args);
  if (note.suffix) s += t(note.suffix.code, note.suffix.args);
  return s;
}

function spectrum(r){
  const W = 400, H = 110, PAD = 14, nyq = r.nyquist/1000;
  const pts = r.chart.map(p => {
    const x = PAD + (p[0]/nyq)*(W-PAD*2);
    const y = PAD + (Math.min(0, Math.max(-120, p[1]))/-120)*(H-PAD*2);
    return x.toFixed(1)+','+y.toFixed(1);
  }).join(' ');
  let ticks = '';
  const stepK = nyq > 30 ? 10 : 5;
  for (let f = 0; f <= nyq; f += stepK){
    const x = PAD + (f/nyq)*(W-PAD*2);
    ticks += `<text class="stxt" x="${x}" y="${H-3}" text-anchor="middle">${f}k</text>`;
  }
  let wall = '';
  if (r.has_wall){
    const x = PAD + (r.wall_hz/1000/nyq)*(W-PAD*2);
    wall = `<line class="swall" x1="${x}" y1="${PAD}" x2="${x}" y2="${H-PAD}"/>`;
  }
  return `<svg class="spec" viewBox="0 0 ${W} ${H}" role="img"
    aria-label="${esc(t('ui.title'))}"><polyline class="sline" points="${pts}"/>${wall}${ticks}</svg>`;
}

function card(r){
  const el = document.createElement('div');
  if (r.error){
    el.className = 'card bad';
    el.style.gridTemplateColumns = '1fr';
    el.innerHTML = `<div><p class="fname">${esc(r.name||'?')}</p>
      <p class="ftag">${esc(t('ui.failed', {msg: t(r.error)}))}</p></div>`;
    return el;
  }
  el.className = 'card';
  const colour = GRADE_COLOUR[r.grade] || 'var(--muted)';
  const circumference = 2*Math.PI*52;
  const dash = (r.total/100)*circumference;
  const parts = r.parts.map(p => `<div class="part">
      <span class="pname">${esc(t(p.key))}</span>
      <span class="ptrack"><i style="width:${(p.got/p.max)*100}%;background:${colour}"></i></span>
      <span class="pval">${p.got} / ${p.max}</span>
      <span class="pnote">${esc(noteText(p.note))}</span>
    </div>`).join('');
  el.innerHTML = `
    <div>
      <svg class="ring" viewBox="0 0 120 120" role="img" aria-label="${r.total}/100">
        <circle class="rbg" cx="60" cy="60" r="52"/>
        <circle class="rfg" cx="60" cy="60" r="52"
          style="stroke:${colour};stroke-dasharray:${dash.toFixed(1)} ${circumference.toFixed(1)}"/>
        <text class="rnum" x="60" y="62" fill="${colour}">${r.total}</text>
        <text class="rof" x="60" y="78">${esc(t('ui.of100'))}</text>
      </svg>
      <div class="gradelbl" style="color:${colour}">${esc(t(r.grade))}</div>
    </div>
    <div>
      <p class="fname">${esc(r.name)}</p>
      <p class="ftag">${esc(t(r.tag))}</p>
      <div class="meta">${esc(r.container)} · ${esc(r.subtype)} · ${r.rate} Hz · ${r.channels}ch · ${clock(r.duration)} · ${mb(r.size)}</div>
      ${spectrum(r)}
      <div class="parts">${parts}</div>
    </div>`;
  return el;
}

function redraw(){
  const out = $('#out');
  out.textContent = '';
  for (let i = results.length - 1; i >= 0; i--) out.appendChild(card(results[i]));
}

let busy = false;
function setBusy(on, code, args, pct){
  busy = on;
  lastStatus = code ? {code, args} : null;
  $('#status').textContent = code ? t(code, args) : '';
  $('#barwrap').hidden = !on;
  if (pct !== undefined) $('#bar').style.width = pct + '%';
}

async function handleFiles(list){
  if (busy || !list.length) return;
  const files = Array.from(list);
  for (let i = 0; i < files.length; i++){
    setBusy(true, 'ui.checking', {i: i+1, n: files.length}, (i/files.length)*100);
    try {
      const body = await files[i].arrayBuffer();
      const res = await fetch('/analyse?name=' + encodeURIComponent(files[i].name),
                              {method:'POST', body});
      results.push(await res.json());
    } catch(e){
      results.push({name: files[i].name, error: 'err.unread'});
    }
    redraw();
  }
  setBusy(false, 'ui.done', {n: files.length});
}

$('#drop').onclick = () => $('#file').click();
$('#file').onchange = e => { handleFiles(e.target.files); e.target.value = ''; };
['dragenter','dragover'].forEach(ev => $('#drop').addEventListener(ev, e => {
  e.preventDefault(); $('#drop').classList.add('hot'); }));
['dragleave','drop'].forEach(ev => $('#drop').addEventListener(ev, e => {
  e.preventDefault(); $('#drop').classList.remove('hot'); }));
$('#drop').addEventListener('drop', e => handleFiles(e.dataTransfer.files));
document.addEventListener('dragover', e => e.preventDefault());
document.addEventListener('drop', e => e.preventDefault());

$('#scan').onclick = async () => {
  const path = $('#folder').value.trim();
  if (!path || busy) return;
  setBusy(true, 'ui.searching', null, 0);
  let list;
  try {
    const res = await fetch('/list', {method:'POST', body: JSON.stringify({path})});
    list = await res.json();
  } catch(e){ setBusy(false, 'ui.unreadable'); return; }
  if (list.error){ setBusy(false, list.error); return; }
  if (!list.length){ setBusy(false, 'ui.nofiles'); return; }
  for (let i = 0; i < list.length; i++){
    setBusy(true, 'ui.checking', {i: i+1, n: list.length}, (i/list.length)*100);
    try {
      const res = await fetch('/analyse_path?path=' + encodeURIComponent(list[i]));
      results.push(await res.json());
      redraw();
    } catch(e){ /* one bad file should not stop the run */ }
  }
  setBusy(false, 'ui.done', {n: list.length});
};

$('#lang').onclick = () => {
  const order = Object.keys(CATALOGUE);
  lang = order[(order.indexOf(lang) + 1) % order.length];
  try { localStorage.setItem('la.lang', lang); } catch(e){}
  applyLanguage();
};

$('#quit').onclick = async () => {
  try { await fetch('/quit', {method:'POST'}); } catch(e){}
  document.body.innerHTML = '<p style="padding:60px;text-align:center">' +
    esc(t('ui.closed')) + '</p>';
};

applyLanguage();
</script></body></html>
"""


def render_page():
    catalogue = {lang: i18n.catalogue(lang) for lang in i18n.LANGUAGES}
    return PAGE.replace("__CATALOGUE__",
                        json.dumps(catalogue, ensure_ascii=False))


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    page = None

    def log_message(self, *args):
        pass

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def _json(self, obj):
        self._send(200, "application/json; charset=utf-8",
                   json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8",
                       Handler.page.encode("utf-8"))
        elif url.path == "/analyse_path":
            path = urllib.parse.parse_qs(url.query).get("path", [""])[0]
            self._json(self._safe_analyse(path))
        else:
            self._send(404, "text/plain; charset=utf-8", b"not found")

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""

        if url.path == "/analyse":
            name = urllib.parse.parse_qs(url.query).get("name", ["audio"])[0]
            suffix = os.path.splitext(name)[1] or ".bin"
            fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="lossless_audit_")
            try:
                os.write(fd, body)
                os.close(fd)
                result = self._safe_analyse(tmp)
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            result["name"] = name
            result["size"] = len(body)
            self._json(result)

        elif url.path == "/list":
            try:
                path = os.path.expanduser(json.loads(body.decode())["path"])
                if not os.path.isdir(path):
                    self._json({"error": "err.notdir"})
                    return
                self._json(engine.collect([path]))
            except Exception:
                self._json({"error": "err.notdir"})

        elif url.path == "/quit":
            self._json({"ok": True})
            threading.Thread(
                target=lambda: (time.sleep(0.4), os._exit(0)),
                daemon=True).start()
        else:
            self._send(404, "text/plain; charset=utf-8", b"not found")

    @staticmethod
    def _safe_analyse(path):
        try:
            result = engine.analyse(path)
        except Exception:
            result = {"error": "err.unread"}
        result.pop("path", None)
        result.setdefault("name", os.path.basename(str(path)))
        return result


def pick_port(preferred=(8777, 8778, 8779)):
    for port in preferred:
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
        finally:
            sock.close()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    open_browser = "--no-browser" not in argv

    Handler.page = render_page()
    port = pick_port()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = "http://127.0.0.1:%d/" % port
    print("Lossless Audit is running at %s" % url)
    print("Press Ctrl-C to stop, or use the Quit button in the page.")
    if open_browser:
        threading.Thread(target=lambda: (time.sleep(0.6), webbrowser.open(url)),
                         daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
