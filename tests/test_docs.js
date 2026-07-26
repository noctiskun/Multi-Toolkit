// Boots docs/index.html in jsdom with a real canvas, drives the QR demo,
// and writes each rendered code to /tmp for zbar to decode independently.
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');
const { Image: NodeImage } = require('canvas');

let html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'index.html'), 'utf8');
// jsdom would resolve the relative <script src> against the fake github.io URL,
// so inline the vendored library exactly as the browser would have received it.
for (const f of ['qrcode.js', 'qrcode_UTF8.js']) {
  const code = fs.readFileSync(path.join(__dirname, '..', 'docs', 'vendor', f), 'utf8');
  // replacer FUNCTION, not a string: `$'` etc. are special in replacements
  html = html.replace(`<script src="vendor/${f}"></script>`,
                      () => '<script>' + code + '</scr' + 'ipt>');
}
const errors = [];
const OUT = '/tmp/qrdemo';
fs.mkdirSync(OUT, { recursive: true });

const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  resources: 'usable',
  pretendToBeVisual: true,
  url: 'https://noctis.github.io/multi-toolkit/',
  beforeParse(win) {
    win.onerror = (m, s, l, c, e) => errors.push('onerror: ' + (e ? e.stack : m));
    const ce = win.console.error;
    win.console.error = (...a) => { errors.push('console.error: ' + a.join(' ')); ce(...a); };
  },
});
const win = dom.window;
const doc = win.document;
const $ = id => doc.getElementById(id);

function step(label, fn) {
  try { fn(); console.log(`  ok   ${label}`); }
  catch (e) { errors.push(`${label}: ${e.message}`); console.log(`  FAIL ${label} — ${e.message}`); }
}
function fire(el, type) { el.dispatchEvent(new win.Event(type, { bubbles: true })); }

function dump(name) {
  const cv = $('cv');
  const buf = Buffer.from(cv.toDataURL('image/png').split(',')[1], 'base64');
  fs.writeFileSync(path.join(OUT, name + '.png'), buf);
  return { w: cv.width, h: cv.height, bytes: buf.length };
}

// A logo built with node-canvas, handed to the page as a real <img>.
function makeLogo() {
  const { createCanvas } = require('canvas');
  const c = createCanvas(400, 400);
  const x = c.getContext('2d');
  x.fillStyle = '#111';
  x.beginPath(); x.arc(200, 60, 32, 0, Math.PI * 2); x.fill();
  x.fillRect(160, 95, 80, 145);
  x.beginPath(); x.moveTo(160, 100); x.lineTo(60, 200); x.lineTo(85, 225);
  x.lineTo(165, 140); x.closePath(); x.fill();
  x.beginPath(); x.moveTo(240, 100); x.lineTo(340, 200); x.lineTo(315, 225);
  x.lineTo(235, 140); x.closePath(); x.fill();
  x.fillRect(168, 240, 27, 130); x.fillRect(205, 240, 27, 130);
  const img = new NodeImage();
  img.src = c.toBuffer('image/png');
  return img;
}

setTimeout(() => {
  console.log('\n== boot ==');
  step('vendored qrcode library loaded', () => {
    if (typeof win.qrcode !== 'function') throw new Error('global qrcode missing');
  });
  step('demo API exposed', () => {
    if (!win.__qrDemo) throw new Error('__qrDemo missing');
  });
  step('renders on load with default link', () => {
    if ($('cv').width < 100) throw new Error('canvas not sized: ' + $('cv').width);
    const ro = $('readout');
    if (ro.dataset.state !== 'live') throw new Error('state=' + ro.dataset.state);
    for (const bit of ['v', 'EC-H', 'px']) {
      if (!ro.textContent.includes(bit)) throw new Error('missing ' + bit);
    }
  });
  step('readout labels every value it shows', () => {
    const cells = [...$('readout').querySelectorAll('.ro-cell')];
    if (cells.length < 5) throw new Error('cells=' + cells.length);
    if (cells.some(c => !c.querySelector('i').textContent.trim()))
      throw new Error('an unlabelled value');
  });
  step('hero is the instrument, not a screenshot', () => {
    const inst = doc.querySelector('.instrument');
    if (!inst) throw new Error('no .instrument');
    if (!inst.contains($('cv'))) throw new Error('canvas is not inside the hero');
    if (doc.querySelectorAll('.spec-row').length < 12)
      throw new Error('spec sheet too short');
  });
  step('GitHub link rewritten from github.io host', () => {
    const href = $('repoLink').href;
    if (href !== 'https://github.com/noctis/multi-toolkit') throw new Error(href);
  });

  console.log('\n== payload kinds ==');
  const kinds = ['url', 'text', 'wifi', 'email', 'phone', 'vcard'];
  for (const k of kinds) {
    step(`kind ${k}`, () => {
      doc.querySelector(`#kinds .chip[data-k="${k}"]`).click
        ? doc.querySelector(`#kinds .chip[data-k="${k}"]`).dispatchEvent(
            new win.Event('click', { bubbles: true }))
        : null;
      if (!$('fields').children.length) throw new Error('no fields built');
    });
  }

  console.log('\n== render + decode cases ==');
  const cases = [];

  function setUrl(v) {
    doc.querySelector('#kinds .chip[data-k="url"]').dispatchEvent(
      new win.Event('click', { bubbles: true }));
    $('f_text').value = v;
    fire($('f_text'), 'input');
  }

  setUrl('example.com');
  cases.push(['plain', 'https://example.com', dump('plain')]);

  $('style').value = 'dots'; fire($('style'), 'change');
  cases.push(['dots', 'https://example.com', dump('dots')]);

  $('style').value = 'rounded'; fire($('style'), 'change');
  cases.push(['rounded', 'https://example.com', dump('rounded')]);

  $('style').value = 'square'; fire($('style'), 'change');
  $('fg').value = '#1b1035'; $('bg').value = '#f5f2ff';
  fire($('fg'), 'change'); fire($('bg'), 'change');
  cases.push(['coloured', 'https://example.com', dump('coloured')]);

  $('fg').value = '#000000'; $('bg').value = '#ffffff';
  fire($('fg'), 'change'); fire($('bg'), 'change');

  // logo, silhouette, no plate — the look from the reference image
  const logo = makeLogo();
  win.__qrDemo.setLogoMode('logo');
  win.__qrDemo.setLogo(logo);
  $('logoStyle').value = 'silhouette'; fire($('logoStyle'), 'change');
  $('logoPct').value = 24; fire($('logoPct'), 'input');
  $('plate').checked = false; fire($('plate'), 'change');
  setUrl('siu.example');
  cases.push(['logo-silhouette', 'https://siu.example', dump('logo_silhouette')]);

  $('plate').checked = true; fire($('plate'), 'change');
  cases.push(['logo-plate', 'https://siu.example', dump('logo_plate')]);

  $('logoStyle').value = 'original'; fire($('logoStyle'), 'change');
  cases.push(['logo-original', 'https://siu.example', dump('logo_original')]);

  win.__qrDemo.setLogoMode('plain');
  $('plate').checked = false; fire($('plate'), 'change');

  // wifi + vcard payloads
  doc.querySelector('#kinds .chip[data-k="wifi"]').dispatchEvent(
    new win.Event('click', { bubbles: true }));
  $('f_ssid').value = 'Lab 5G'; fire($('f_ssid'), 'input');
  $('f_password').value = 'hunter2'; fire($('f_password'), 'input');
  cases.push(['wifi', 'WIFI:T:WPA;S:Lab 5G;P:hunter2;;', dump('wifi')]);

  doc.querySelector('#kinds .chip[data-k="vcard"]').dispatchEvent(
    new win.Event('click', { bubbles: true }));
  $('f_name').value = 'Ada Lovelace'; fire($('f_name'), 'input');
  $('f_email').value = 'ada@example.com'; fire($('f_email'), 'input');
  cases.push(['vcard', null, dump('vcard')]);

  // unicode
  doc.querySelector('#kinds .chip[data-k="text"]').dispatchEvent(
    new win.Event('click', { bubbles: true }));
  $('f_text').value = 'café ☕ 東京'; fire($('f_text'), 'input');
  cases.push(['unicode', 'café ☕ 東京', dump('unicode')]);

  // big size
  setUrl('example.com');
  $('size').value = '2048'; fire($('size'), 'change');
  cases.push(['2048px', 'https://example.com', dump('big')]);
  $('size').value = '1024'; fire($('size'), 'change');

  for (const [name, , info] of cases) {
    console.log(`  rendered ${name.padEnd(18)} ${info.w}x${info.h} ${Math.round(info.bytes / 1024)}KB`);
  }

  console.log('\n== theme + optional logo ==');
  step('theme toggle flips the chassis, no emoji', () => {
    const before = doc.documentElement.getAttribute('data-theme');
    $('themeBtn').dispatchEvent(new win.Event('click', { bubbles: true }));
    if (doc.documentElement.getAttribute('data-theme') === before)
      throw new Error('did not change');
    if (!$('themeBtn').querySelector('svg')) throw new Error('no svg glyph');
    if (/[\u2600-\u27BF\u{1F300}-\u{1F9FF}]/u.test($('themeBtn').textContent))
      throw new Error('emoji found');
    $('themeBtn').dispatchEvent(new win.Event('click', { bubbles: true }));
  });
  step('plain is the default and needs no upload', () => {
    const chosen = doc.querySelector('#logoMode .chip.active');
    if (!chosen || chosen.dataset.m !== 'plain') throw new Error('not plain');
    if (!$('logoDrop').hidden) throw new Error('upload zone showing');
    if ($('readout').dataset.state !== 'live')
      throw new Error('plain code did not render');
  });
  step('switching to logo reveals the upload, and back hides it', () => {
    doc.querySelector('#logoMode .chip[data-m="logo"]').dispatchEvent(
      new win.Event('click', { bubbles: true }));
    if ($('logoDrop').hidden) throw new Error('upload zone hidden');
    doc.querySelector('#logoMode .chip[data-m="plain"]').dispatchEvent(
      new win.Event('click', { bubbles: true }));
    if (!$('logoDrop').hidden) throw new Error('upload zone still showing');
  });
  step('no stray text renders at the top of the page', () => {
    const first = doc.body.textContent.replace(/\s+/g, ' ').trim().slice(0, 40);
    if (/^["'>\/]/.test(first)) throw new Error('stray markup: ' + first);
    if (!doc.head.querySelector('style')) throw new Error('<style> fell out of <head>');
  });

  console.log('\n== guards ==');
  step('empty input clears the canvas', () => {
    setUrl('');
    if ($('readout').dataset.state !== 'idle')
      throw new Error('state=' + $('readout').dataset.state);
    if (!$('readout').textContent.includes('awaiting'))
      throw new Error($('readout').textContent);
    if (!$('dl').disabled) throw new Error('download still enabled');
  });
  step('low quiet zone warns', () => {
    setUrl('example.com');
    $('border').value = '0'; fire($('border'), 'input');
    if (!$('warn').textContent.includes('Quiet zone')) throw new Error($('warn').textContent);
    $('border').value = '4'; fire($('border'), 'input');
  });
  step('poor contrast warns', () => {
    $('fg').value = '#dddddd'; fire($('fg'), 'change');
    if (!$('warn').textContent.length) throw new Error('no warning');
    $('fg').value = '#000000'; fire($('fg'), 'change');
  });
  step('transparent warns and disables bg', () => {
    $('transparent').checked = true; fire($('transparent'), 'change');
    if (!$('bg').disabled) throw new Error('bg not disabled');
    if (!$('warn').textContent.includes('Transparent')) throw new Error($('warn').textContent);
    $('transparent').checked = false; fire($('transparent'), 'change');
  });
  step('oversized data handled without throwing', () => {
    doc.querySelector('#kinds .chip[data-k="text"]').dispatchEvent(
      new win.Event('click', { bubbles: true }));
    $('f_text').value = 'x'.repeat(9000); fire($('f_text'), 'input');
    if (!$('readout').textContent.length) throw new Error('no message');
    if (!$('warn').textContent.length) throw new Error('no guidance offered');
  });

  fs.writeFileSync('/tmp/qrdemo/expected.json',
    JSON.stringify(cases.map(([n, e]) => [n, e])));
  console.log('\n' + (errors.length ? `${errors.length} PROBLEM(S):\n  ` + errors.join('\n  ')
                                     : 'PAGE OK — now decoding the PNGs'));
  process.exit(errors.length ? 1 : 0);
}, 700);
