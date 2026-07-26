// Boots the real page in jsdom, then clicks through every tab and control.
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

// Pull the live page straight out of the source so this can never test a
// stale copy: PAGE = r"""...""" in multi_toolkit.py.
const src = fs.readFileSync(path.join(__dirname, '..', 'multi_toolkit.py'), 'utf8');
const start = src.indexOf('PAGE = r"""');
const end = src.indexOf('\n"""', start);
if (start < 0 || end < 0) { console.error('could not locate PAGE in source'); process.exit(1); }
const html = src.slice(start + 'PAGE = r"""'.length, end);
const errors = [];

// Minimal fake backend so the page's fetch() calls resolve.
const routes = {
  '/capabilities': { libreoffice: true, ghostscript: false, ffmpeg: true },
  '/qr': { image: 'iVBORw0KGgo=', mime: 'image/png', size: 1024, modules: 33,
           version: 4, ec: 'H', bytes: 2048, chars: 19, warn: '' },
  '/img_fetch': { name: 'shot.jpg', width: 1600, height: 1000, format: 'JPEG',
                  bytes: 400000, preview: 'iVBORw0KGgo=', token: 'tok123' },
};

const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  beforeParse(win) {
    win.fetch = (url, opts) => {
      const path = String(url).split('?')[0];
      const body = routes[path] ?? { ok: true };
      return Promise.resolve({
        ok: true, status: 200,
        json: () => Promise.resolve(body),
        text: () => Promise.resolve(JSON.stringify(body)),
        blob: () => Promise.resolve({ size: 10 }),
        headers: { get: () => '' },
      });
    };
    win.URL.createObjectURL = () => 'blob:fake';
    win.URL.revokeObjectURL = () => {};
    win.HTMLElement.prototype.setPointerCapture = function () {};
    win.HTMLElement.prototype.releasePointerCapture = function () {};
    win.HTMLElement.prototype.click = function () {
      this.dispatchEvent(new win.Event('click', { bubbles: true }));
    };
    win.onerror = (m, s, l, c, e) => errors.push('window.onerror: ' + (e ? e.stack : m));
    win.addEventListener('unhandledrejection', ev =>
      errors.push('unhandled rejection: ' + ev.reason));
    const origErr = win.console.error;
    win.console.error = (...a) => { errors.push('console.error: ' + a.join(' ')); origErr(...a); };
  },
});

const win = dom.window;
const doc = win.document;
const $ = id => doc.getElementById(id);

function step(label, fn) {
  try { fn(); console.log(`  ok   ${label}`); }
  catch (e) { errors.push(`${label}: ${e.message}`); console.log(`  FAIL ${label} — ${e.message}`); }
}

setTimeout(() => {
  console.log('\n== boot ==');
  step('page booted with no script error', () => {
    if (!$('go')) throw new Error('go button missing');
  });
  step('default tab is Merge', () => {
    const a = doc.querySelector('.tab.active');
    if (!a || a.dataset.tab !== 'merge') throw new Error('active=' + (a && a.dataset.tab));
    if ($('go').textContent.indexOf('Merge') < 0) throw new Error($('go').textContent);
  });
  step('QR fields rendered on boot', () => {
    if (!$('qrf_text')) throw new Error('qrf_text missing');
  });

  console.log('\n== tab switching ==');
  const expect = {
    merge: 'Merge', split: 'Split', compress: 'Compress', convert: 'Convert',
    youtube: 'Download Video', reels: 'Download Reel', image: 'Export Image',
    qr: 'Download QR Code',
  };
  for (const [name, label] of Object.entries(expect)) {
    step(`switch to ${name}`, () => {
      doc.querySelector(`.tab[data-tab="${name}"]`).dispatchEvent(
        new win.Event('click', { bubbles: true }));
      const a = doc.querySelector('.tab.active');
      if (!a || a.dataset.tab !== name) throw new Error('active=' + (a && a.dataset.tab));
      if (!$('go').textContent.includes(label)) throw new Error('label=' + $('go').textContent);
      // the right panel must be visible, the others hidden
      const panels = { youtube: 'ytUI', reels: 'ytUI', image: 'imgUI', qr: 'qrUI' };
      if (panels[name] && $(panels[name]).classList.contains('hide'))
        throw new Error(panels[name] + ' hidden');
      if (name !== 'qr' && !$('qrUI').classList.contains('hide'))
        throw new Error('qrUI leaked into ' + name);
      if (name !== 'image' && !$('imgUI').classList.contains('hide'))
        throw new Error('imgUI leaked into ' + name);
    });
  }

  console.log('\n== group nav ==');
  step('each group restores the tab you last used in it', () => {
    // the loop above ended on convert (pdf) and qr (media)
    const click = sel => doc.querySelector(sel).dispatchEvent(
      new win.Event('click', { bubbles: true }));
    const active = () => doc.querySelector('.tab.active').dataset.tab;
    click('.group[data-g="pdf"]');
    if (active() !== 'convert') throw new Error('pdf group -> ' + active());
    click('.group[data-g="media"]');
    if (active() !== 'qr') throw new Error('media group -> ' + active());
    // pick a different tab, leave, come back — it should still be there
    click('.tab[data-tab="split"]');
    click('.group[data-g="media"]');
    click('.group[data-g="pdf"]');
    if (active() !== 'split') throw new Error('did not remember split, got ' + active());
  });
  step('rail shows every tool at once', () => {
    // The rail is a directory, not a switcher: all 8 tabs stay visible and the
    // group heading highlights to show where you are.
    const rows = [...doc.querySelectorAll('.tabs')];
    if (rows.some(r => r.classList.contains('hide')))
      throw new Error('a tab row is hidden');
    if (doc.querySelectorAll('.tab').length !== 8)
      throw new Error('expected 8 tabs, got ' + doc.querySelectorAll('.tab').length);
    doc.querySelector('.tab[data-tab="qr"]').dispatchEvent(
      new win.Event('click', { bubbles: true }));
    const activeGroup = doc.querySelector('.group.active');
    if (!activeGroup || activeGroup.dataset.g !== 'media')
      throw new Error('group heading did not follow the tab');
  });

  console.log('\n== readout ==');
  step('readout reports idle before anything is loaded', () => {
    doc.querySelector('.tab[data-tab="merge"]').dispatchEvent(
      new win.Event('click', { bubbles: true }));
    const ro = $('readout');
    if (ro.dataset.state !== 'idle') throw new Error('state=' + ro.dataset.state);
    if (!ro.textContent.toLowerCase().includes('none')) throw new Error(ro.textContent);
  });
  step('readout switches context with the tab', () => {
    doc.querySelector('.tab[data-tab="image"]').dispatchEvent(
      new win.Event('click', { bubbles: true }));
    if (!$('readout').textContent.toLowerCase().includes('nothing loaded'))
      throw new Error($('readout').textContent);
  });
  // Drive the real path — type, let the debounce fire, assert in the later block.
  doc.querySelector('.tab[data-tab="qr"]').dispatchEvent(
    new win.Event('click', { bubbles: true }));
  doc.querySelector('#qrKinds .chip[data-k="url"]').dispatchEvent(
    new win.Event('click', { bubbles: true }));
  $('qrf_text').value = 'example.com';
  $('qrf_text').dispatchEvent(new win.Event('input', { bubbles: true }));

  console.log('\n== QR panel ==');
  doc.querySelector('.tab[data-tab="qr"]').dispatchEvent(new win.Event('click', { bubbles: true }));
  for (const k of ['url', 'text', 'wifi', 'email', 'sms', 'phone', 'vcard', 'geo']) {
    step(`kind ${k} builds fields`, () => {
      doc.querySelector(`#qrKinds .chip[data-k="${k}"]`).dispatchEvent(
        new win.Event('click', { bubbles: true }));
      if (!$('qrFields').children.length) throw new Error('no fields');
    });
  }
  step('typing a link triggers a request', () => {
    doc.querySelector('#qrKinds .chip[data-k="url"]').dispatchEvent(
      new win.Event('click', { bubbles: true }));
    $('qrf_text').value = 'example.com';
    $('qrf_text').dispatchEvent(new win.Event('input', { bubbles: true }));
  });
  step('style controls toggle cleanly', () => {
    $('qrTransparent').checked = true;
    $('qrTransparent').dispatchEvent(new win.Event('change', { bubbles: true }));
    if (!$('qrBg').disabled) throw new Error('bg not disabled');
    $('qrPad').checked = true;
    $('qrPad').dispatchEvent(new win.Event('change', { bubbles: true }));
    if ($('qrPadShapeWrap').classList.contains('hide')) throw new Error('shape still hidden');
    $('qrLogoPct').value = 30;
    $('qrLogoPct').dispatchEvent(new win.Event('input', { bubbles: true }));
    if ($('qrLogoPctVal').textContent !== '30%') throw new Error($('qrLogoPctVal').textContent);
  });

  console.log('\n== video panel ==');
  const goTab = n => doc.querySelector(`.tab[data-tab="${n}"]`)
    .dispatchEvent(new win.Event('click', { bubbles: true }));

  step('reels shows vertical, defaulted to blurred backdrop', () => {
    goTab('reels');
    if ($('ytVertWrap').classList.contains('hide')) throw new Error('vertical control hidden');
    if ($('ytVert').value !== 'blur') throw new Error('vert=' + $('ytVert').value);
    if ($('ytSizeWrap').classList.contains('hide')) throw new Error('canvas picker hidden');
    if (!$('ytUrl').placeholder.includes('instagram')) throw new Error($('ytUrl').placeholder);
  });
  step('youtube hides vertical reframing entirely', () => {
    goTab('youtube');
    if (!$('ytVertWrap').classList.contains('hide')) throw new Error('vertical control shown');
    if (!$('ytSizeWrap').classList.contains('hide')) throw new Error('canvas picker shown');
    if (!$('ytUrl').placeholder.includes('youtube')) throw new Error($('ytUrl').placeholder);
  });
  step('youtube keeps the cookies control', () => {
    goTab('youtube');
    if ($('ytCookies').closest('.opts').classList.contains('hide'))
      throw new Error('cookies row hidden');
  });
  step('a reels choice survives a trip to youtube', () => {
    goTab('reels');
    $('ytVert').value = 'crop';
    $('ytVert').dispatchEvent(new win.Event('change', { bubbles: true }));
    goTab('youtube');
    goTab('reels');
    if ($('ytVert').value !== 'crop') throw new Error('lost choice: ' + $('ytVert').value);
  });
  step('vertMode() reports off on youtube even after a reels choice', () => {
    goTab('reels');
    $('ytVert').value = 'crop';
    $('ytVert').dispatchEvent(new win.Event('change', { bubbles: true }));
    goTab('youtube');
    if (win.vertMode() !== 'off') throw new Error('vertMode=' + win.vertMode());
    goTab('reels');
    if (win.vertMode() !== 'crop') throw new Error('vertMode=' + win.vertMode());
  });

  console.log('\n== image panel ==');
  step('loading an image opens the editor', async () => {
    doc.querySelector('.tab[data-tab="image"]').dispatchEvent(new win.Event('click', { bubbles: true }));
    $('imgUrl').value = 'https://example.com/a.jpg';
    $('imgFetch').dispatchEvent(new win.Event('click', { bubbles: true }));
  });

  setTimeout(() => {
    step('editor visible with crop state', () => {
      if ($('imgEditor').classList.contains('hide')) throw new Error('editor hidden');
      if ($('outW').value !== '1600') throw new Error('outW=' + $('outW').value);
      if ($('outH').value !== '1000') throw new Error('outH=' + $('outH').value);
    });
    step('aspect chips reshape the crop', () => {
      doc.querySelector('#arChips .chip[data-ar="0.5625"]').dispatchEvent(
        new win.Event('click', { bubbles: true }));
      const w = +$('outW').value, h = +$('outH').value;
      if (Math.abs(w / h - 0.5625) > 0.02) throw new Error(`${w}x${h}`);
      doc.querySelector('#arChips .chip[data-ar="1"]').dispatchEvent(
        new win.Event('click', { bubbles: true }));
      if (Math.abs(+$('outW').value / +$('outH').value - 1) > 0.02)
        throw new Error($('outW').value + 'x' + $('outH').value);
    });
    step('width input keeps the ratio', () => {
      $('outW').value = 500;
      $('outW').dispatchEvent(new win.Event('input', { bubbles: true }));
      if (+$('outH').value !== 500) throw new Error('outH=' + $('outH').value);
    });
    step('rotate swaps reported dimensions', () => {
      doc.querySelector('#arChips .chip[data-ar="full"]').dispatchEvent(
        new win.Event('click', { bubbles: true }));
      const before = $('outW').value;
      $('imgRot').dispatchEvent(new win.Event('click', { bubbles: true }));
      if ($('outW').value === before) throw new Error('no swap');
    });
    step('format toggle reveals quality', () => {
      $('imgFmt').value = 'jpg';
      $('imgFmt').dispatchEvent(new win.Event('change', { bubbles: true }));
      if ($('imgQWrap').classList.contains('hide')) throw new Error('quality hidden');
      $('imgFmt').value = 'png';
      $('imgFmt').dispatchEvent(new win.Event('change', { bubbles: true }));
      if (!$('imgQWrap').classList.contains('hide')) throw new Error('quality shown for png');
    });
    step('reset restores the full frame', () => {
      $('cropReset').dispatchEvent(new win.Event('click', { bubbles: true }));
      if ($('outW').value !== '1600' || $('outH').value !== '1000')
        throw new Error($('outW').value + 'x' + $('outH').value);
    });

    console.log('\n== readout, after the QR request resolved ==');
    step('readout goes live with real QR measurements', () => {
      doc.querySelector('.tab[data-tab="qr"]').dispatchEvent(
        new win.Event('click', { bubbles: true }));
      const ro = $('readout');
      if (ro.dataset.state !== 'live')
        throw new Error('state=' + ro.dataset.state + ' text=' + ro.textContent);
      for (const bit of ['v4', '33×33', 'EC-H', '1024 px']) {
        if (!ro.textContent.includes(bit))
          throw new Error('missing ' + bit + ' in ' + ro.textContent);
      }
      if (ro.querySelectorAll('.ro-cell').length !== 5)
        throw new Error('cells=' + ro.querySelectorAll('.ro-cell').length);
    });
    step('every readout value carries a label', () => {
      const labels = [...$('readout').querySelectorAll('.ro-cell i')]
        .map(e => e.textContent);
      if (!labels.includes('version') || !labels.includes('correction'))
        throw new Error(labels.join(','));
      if (labels.some(l => !l.trim())) throw new Error('an unlabelled value');
    });

    console.log('\n== regression: PDF tabs ==');
    step('split chips still switch modes', () => {
      doc.querySelector('.tab[data-tab="split"]').dispatchEvent(new win.Event('click', { bubbles: true }));
      doc.querySelector('#splitChips .chip[data-m="ranges"]').dispatchEvent(
        new win.Event('click', { bubbles: true }));
      if ($('rangesWrap').classList.contains('hide')) throw new Error('ranges input hidden');
    });
    step('compress presets still select', () => {
      doc.querySelector('.tab[data-tab="compress"]').dispatchEvent(new win.Event('click', { bubbles: true }));
      doc.querySelector('.pcard[data-p="lossless"]').dispatchEvent(new win.Event('click', { bubbles: true }));
      if (!doc.querySelector('.pcard[data-p="lossless"]').classList.contains('active'))
        throw new Error('not active');
    });
    step('convert route toggles options', () => {
      doc.querySelector('.tab[data-tab="convert"]').dispatchEvent(new win.Event('click', { bubbles: true }));
      $('route').value = 'pdf2img';
      $('route').dispatchEvent(new win.Event('change', { bubbles: true }));
      if ($('imgFmtWrap').classList.contains('hide')) throw new Error('img format hidden');
    });

    console.log('\n' + (errors.length ? `${errors.length} PROBLEM(S):\n  ` + errors.join('\n  ')
                                       : 'ALL PASS'));
    process.exit(errors.length ? 1 : 0);
  }, 400);
}, 400);
