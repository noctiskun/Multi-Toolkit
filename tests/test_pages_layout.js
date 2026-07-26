// Serves the page over real HTTP in both GitHub Pages layouts and checks that
// the QR library resolves in each. This reproduces a real failure: Pages was
// publishing the repo root, so `vendor/qrcode.js` 404'd because the vendor
// folder lives under docs/.
const fs = require('fs');
const path = require('path');
const http = require('http');
const { JSDOM } = require('jsdom');

const ROOT = path.join(__dirname, '..');
const errors = [];

function copy(src, dst) {
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.copyFileSync(src, dst);
}

// Layout A — Pages publishes /docs:  index.html and vendor/ side by side.
// Layout B — Pages publishes the repo root: index.html at top, vendor under docs/.
function buildLayout(kind) {
  const base = fs.mkdtempSync('/tmp/pages-' + kind + '-');
  if (kind === 'docs-folder') {
    // Pages publishes /docs: index.html and vendor/ sit side by side.
    copy(path.join(ROOT, 'docs', 'index.html'), path.join(base, 'index.html'));
    for (const f of ['qrcode.js', 'qrcode_UTF8.js'])
      copy(path.join(ROOT, 'docs', 'vendor', f), path.join(base, 'vendor', f));
  } else {
    // Pages publishes the repo root: the root stub redirects into docs/.
    copy(path.join(ROOT, 'index.html'), path.join(base, 'index.html'));
    copy(path.join(ROOT, 'docs', 'index.html'), path.join(base, 'docs', 'index.html'));
    for (const f of ['qrcode.js', 'qrcode_UTF8.js'])
      copy(path.join(ROOT, 'docs', 'vendor', f),
           path.join(base, 'docs', 'vendor', f));
  }
  return base;
}

const MIME = { '.html': 'text/html', '.js': 'text/javascript' };

function serve(dir) {
  return new Promise(resolve => {
    const requested = [];
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p.endsWith('/')) p += 'index.html';
      const file = path.join(dir, p);
      requested.push({ url: p, ok: fs.existsSync(file) });
      if (!fs.existsSync(file)) { res.writeHead(404); return res.end('nope'); }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'text/plain' });
      res.end(fs.readFileSync(file));
    });
    srv.listen(0, '127.0.0.1', () => resolve({ srv, requested,
      port: srv.address().port }));
  });
}

function load(url) {
  return JSDOM.fromURL(url, {
    runScripts: 'dangerously',
    resources: 'usable',
    pretendToBeVisual: true,
  });
}

function check(label, cond, detail) {
  console.log(`  ${cond ? 'ok  ' : 'FAIL'} ${label}${detail ? ' — ' + detail : ''}`);
  if (!cond) errors.push(label + (detail ? ' — ' + detail : ''));
}

(async () => {
  for (const kind of ['docs-folder', 'repo-root-with-stub']) {
    const dir = buildLayout(kind === 'docs-folder' ? 'docs-folder' : 'root');
    const { srv, requested, port } = await serve(dir);
    console.log(`\n== Pages publishing the ${kind} ==`);
    try {
      let dom = await load(`http://127.0.0.1:${port}/`);
      await new Promise(r => setTimeout(r, 400));
      // The root stub redirects; jsdom does not follow meta-refresh, so do it.
      const meta = dom.window.document.querySelector('meta[http-equiv="refresh"]');
      if (meta) {
        check('root stub points at docs/', /url=\.\/docs\//.test(meta.content),
              meta.content);
        dom.window.close();
        dom = await load(`http://127.0.0.1:${port}/docs/`);
      }
      await new Promise(r => setTimeout(r, 900));
      const w = dom.window, $ = id => w.document.getElementById(id);

      check('QR library resolved', typeof w.qrcode === 'function');
      check('demo booted', !!w.__qrDemo);
      const ro = $('readout');
      check('a plain code rendered on load', ro && ro.dataset.state === 'live',
            ro ? ro.textContent.replace(/\s+/g, ' ').trim().slice(0, 60) : 'no readout');
      check('canvas has real pixels', $('cv').width > 100, $('cv').width + 'px');
      check('download enabled', !$('dl').disabled);

      const misses = requested.filter(r => !r.ok).map(r => r.url);
      console.log(`       requests: ${requested.length}, 404s: ` +
                  (misses.length ? misses.join(', ') : 'none'));

      // Plain must be the default and must not wait on an upload.
      const active = w.document.querySelector('#logoMode .chip.active');
      check('defaults to Plain code', active && active.dataset.m === 'plain');
      for (const id of ['logoDrop', 'logoChip', 'logoOpts']) {
        const el = $(id);
        const shown = w.getComputedStyle(el).display !== 'none';
        check(`${id} hidden while Plain is active`, !shown,
              shown ? 'display=' + w.getComputedStyle(el).display : '');
      }
      dom.window.close();
    } finally {
      srv.close();
      fs.rmSync(dir, { recursive: true, force: true });
    }
  }

  console.log('\n' + (errors.length
    ? `${errors.length} FAILURE(S):\n  ` + errors.join('\n  ')
    : 'BOTH PAGES LAYOUTS WORK'));
  process.exit(errors.length ? 1 : 0);
})();
