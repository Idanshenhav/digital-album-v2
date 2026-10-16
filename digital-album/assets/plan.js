const src = n => 'data:image/jpeg;base64,' + I[n];
const filt = t => `brightness(${1 + t.bright / 100}) contrast(${1 + t.contrast / 100}) saturate(${1 + t.sat / 100})`;
const KEY = STORE_KEY;
let M = {};
try { M = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { M = {}; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(M)); } catch (e) {} refreshMarks(); };

document.querySelectorAll('.ph').forEach(el => {
  const n = el.dataset.n;
  el.style.backgroundImage = `url(${src(n)})`;
  el.style.setProperty('--f', filt(D[n].t));
  el.onclick = e => { if (e.target.classList.contains('mk')) { e.stopPropagation(); toggle(n, 'replace'); } else show(n); };
});
document.querySelectorAll('.blur, .texbg').forEach(el => { el.style.backgroundImage = `url(${src(el.dataset.bg)})`; });

const grid = document.getElementById('grid');
Object.values(D).sort((a, b) => a.o - b.o).forEach(p => {
  const c = document.createElement('div');
  c.className = 'pc' + (p.k ? '' : ' out'); c.dataset.n = p.n;
  const st = p.k ? `<span class="st k">KEEP · page ${p.pg}${p.h ? ' · FULL PAGE' : ''}</span>` : (p.sc ? '<span class="st c">CUT FOR SPACE</span>' : '<span class="st o">OUT</span>');
  c.innerHTML = `<div class="img" style="background-image:url(${src(p.n)})"><i>${p.n}</i></div><div class="body">${st} <span class="st m mkl"></span><div><b>${p.pl}</b></div><div>${p.s}</div>${p.k ? '' : `<div class="muted">Why: ${p.r}</div>`}<div class="muted">${p.d}</div></div>`;
  c.querySelector('.img').style.setProperty('--f', filt(p.t));
  c.querySelector('.img').onclick = () => show(p.n);
  grid.appendChild(c);
});

function toggle(n, kind) {
  n = String(n);
  if (M[n] && M[n].kind === kind) delete M[n]; else M[n] = { kind, note: (M[n] && M[n].note) || '' };
  save();
}
function refreshMarks() {
  document.querySelectorAll('.ph').forEach(el => { const m = M[el.dataset.n]; el.classList.toggle('marked', !!m);
    el.dataset.with = m && m.with ? (m.kind === 'swap' ? ` ↔ #${m.with}` : ` ← #${m.with}`) : ''; });
  grid.querySelectorAll('.pc').forEach(c => { const m = M[c.dataset.n]; c.classList.toggle('marked', !!m);
    c.querySelector('.mkl').textContent = m ? (m.kind === 'replace' ? `· REPLACE${m.with ? ' WITH #' + m.with : ''}` : m.kind === 'swap' ? `· SWAP WITH #${m.with}` : '· MARKED: ADD BACK') : ''; });
  const r = Object.values(M).filter(m => m.kind === 'replace').length, a = Object.values(M).filter(m => m.kind === 'add').length, w = Object.values(M).filter(m => m.kind === 'swap').length;
  document.getElementById('markcount').textContent = r || a || w ? `Replace: ${r} · Swap: ${w} · Add back: ${a}` : 'No marks yet';
  apply();
}
function marksText() {
  const lines = Object.entries(M).sort((a, b) => D[a[0]].o - D[b[0]].o).map(([n, m]) =>
    m.kind === 'replace'
      ? (m.with ? `Replace #${n} (page ${D[n].pg}) with #${m.with}` : `Remove #${n} (page ${D[n].pg}), no replacement yet`) + (m.note ? ` — ${m.note}` : '')
      : m.kind === 'swap' ? `Swap #${n} and #${m.with} (page ${D[n].pg})${m.note ? ` — ${m.note}` : ''}`
      : `Add back #${n}${m.note ? ` — ${m.note}` : ''}`);
  return lines.length ? 'Album marks:\n' + lines.join('\n') : '';
}
document.getElementById('copy').onclick = async () => {
  const t = marksText(); if (!t) return;
  try { await navigator.clipboard.writeText(t); } catch (e) { const b = document.getElementById('copybox'); b.value = t; b.select(); document.execCommand('copy'); }
  const btn = document.getElementById('copy'); btn.textContent = 'Copied ✓ — paste to Claude'; setTimeout(() => btn.textContent = 'Copy my marks', 2500);
};
document.getElementById('clear').onclick = () => { if (confirm('Clear all marks?')) { M = {}; save(); } };

const lb = document.getElementById('lb');
function show(n) {
  n = String(n); const p = D[n]; const m = M[n];
  const status = p.k ? `<b style="color:var(--keep)">Kept</b> · page ${p.pg}${p.h ? ' (full page / spread)' : ''}` : (p.sc ? `<b style="color:var(--cut)">Cut for space</b>` : `<b style="color:var(--out)">Left out</b>`);
  const act = p.k
    ? `<button class="${m && m.kind === 'replace' ? 'btn-mark' : ''}" id="bm">${m && m.kind === 'replace' ? '✓ Marked for replacement' : 'Mark for replacement'}</button>`
    : `<button class="${m && m.kind === 'add' ? 'btn-mark' : ''}" id="bm">${m && m.kind === 'add' ? '✓ Marked: add back' : 'Add back to album'}</button>`;
  document.getElementById('lbin').innerHTML = `<div class="cmp"><img src="${src(n)}" alt="before"><img src="${src(n)}" alt="after" style="filter:${filt(p.t)}"></div>
   <div class="meta"><h3>Photo #${p.n}</h3><p>${status}</p><p><b>${p.pl}</b> · ${p.d}</p><p>${p.s}</p>
   ${p.k ? '' : `<p><b>Why out:</b> ${p.r}</p>`}${p.note ? `<p><b>Note:</b> ${p.note}</p>` : ''}
   ${p.fr ? `<p><b>Frame:</b> ${p.fr}</p>` : ''}
   <p><b>Tuning:</b> ${p.tt}</p><p class="muted">Reviewer hint: ${p.fx || 'none'} · quality ${p.q}/5 · ratio ${p.ar}</p>
   <p class="he muted">${S[p.sec].he}</p>
   <div class="actions">${act}<button id="bc">Close</button></div>
   ${p.k ? `<div class="pick"><b>Replace with:</b> <span class="muted">click a photo from this place, or type a number</span>
     <div class="cands" id="cands"></div>
     <div class="actions"><input type="search" id="bw" placeholder="Photo #" value="${m && m.kind === 'replace' && m.with ? m.with : ''}" style="width:110px"><button id="more">More from nearby places</button>${m && m.kind === 'replace' && m.with ? '<button id="nowith">No replacement</button>' : ''}</div></div>
     <div class="pick"><b>Swap with</b> <span class="muted">another photo on this page / spread (they trade places)</span>
     <div class="cands" id="mates"></div></div>` : ''}
   <input type="text" id="bn" placeholder="Optional note (e.g. crop less, brighter)" value="${m ? (m.note || '').replace(/"/g, '&quot;') : ''}">
   <p class="muted">Left: before · Right: after tuning (preview)</p></div>`;
  document.getElementById('bm').onclick = () => { toggle(n, p.k ? 'replace' : 'add'); show(n); };
  if (p.k) {
    const setWith = w => { M[n] = { kind: 'replace', with: w ? String(w) : '', note: (M[n] && M[n].note) || '' }; save(); show(n); };
    const secs = Object.keys(S).sort(); const si = secs.indexOf(p.sec);
    const fill = wide => {
      const near = wide ? secs.slice(Math.max(0, si - 1), si + 2) : [p.sec];
      const list = Object.values(D).filter(x => near.includes(x.sec) && String(x.n) !== n && (!x.k || wide)).sort((a, b) => (a.k - b.k) || (b.sc - a.sc) || (a.o - b.o));
      document.getElementById('cands').innerHTML = list.map(x => `<div class="cand ${m && m.with == x.n ? 'sel' : ''} ${x.k ? 'inalb' : ''}" data-w="${x.n}" title="${x.s}"><img src="${src(x.n)}" alt="#${x.n}"><i>${x.n}</i>${x.k ? '<em>in album</em>' : x.sc ? '<em>cut</em>' : ''}</div>`).join('') || '<span class="muted">No other photos from this place — try "More from nearby places" or type a number.</span>';
      document.querySelectorAll('#cands .cand').forEach(c => c.onclick = () => setWith(c.dataset.w));
    };
    fill(false);
    document.getElementById('mates').innerHTML = (p.mt || []).map(x => `<div class="cand ${m && m.kind === 'swap' && m.with == x ? 'sel' : ''}" data-s="${x}" title="${D[x].s}"><img src="${src(x)}" alt="#${x}"><i>${x}</i></div>`).join('') || '<span class="muted">This photo is alone on its page.</span>';
    document.querySelectorAll('#mates .cand').forEach(c => c.onclick = () => { const w = c.dataset.s;
      if (M[n] && M[n].kind === 'swap' && M[n].with === w) delete M[n]; else M[n] = { kind: 'swap', with: w, note: (M[n] && M[n].note) || '' };
      save(); show(n); });
    document.getElementById('more').onclick = () => fill(true);
    document.getElementById('bw').onchange = e => { const w = e.target.value.trim().replace('#', ''); if (D[w]) setWith(w); };
    const nw = document.getElementById('nowith'); if (nw) nw.onclick = () => setWith('');
  }
  document.getElementById('bc').onclick = () => lb.classList.remove('show');
  document.getElementById('bn').oninput = e => { if (!M[n]) M[n] = { kind: p.k ? 'replace' : 'add', note: '' }; M[n].note = e.target.value; save(); };
  lb.classList.add('show');
}
lb.onclick = e => { if (e.target === lb) lb.classList.remove('show'); };
document.addEventListener('keydown', e => { if (e.key === 'Escape') lb.classList.remove('show'); });
const ba = document.getElementById('ba');
ba.onclick = () => { document.body.classList.toggle('after'); ba.textContent = document.body.classList.contains('after') ? 'Show: After tuning' : 'Show: Before'; ba.classList.toggle('on'); };
let mode = 'all';
function apply() {
  const q = document.getElementById('q').value.trim().toLowerCase();
  grid.querySelectorAll('.pc').forEach(c => { const p = D[c.dataset.n];
    const okm = mode === 'all' || (mode === 'keep' && p.k) || (mode === 'out' && !p.k && !p.sc) || (mode === 'cut' && p.sc) || (mode === 'hero' && p.h) || (mode === 'marked' && M[c.dataset.n]);
    const okq = !q || String(p.n) === q || (p.pl + ' ' + p.s + ' ' + p.r).toLowerCase().includes(q);
    c.style.display = okm && okq ? '' : 'none'; });
}
document.querySelectorAll('button.f').forEach(b => b.onclick = () => { document.querySelectorAll('button.f').forEach(x => x.classList.remove('on')); b.classList.add('on'); mode = b.dataset.f; apply(); });
document.getElementById('q').oninput = apply;
document.getElementById('jump').onchange = e => { const el = document.querySelector(`.page[data-page="${e.target.value.trim()}"]`); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' }); };
refreshMarks();

// Click a QR code to see it large, so it can be scanned with a phone from the screen. Click again (or Esc) to close.
(() => {
  const box = document.createElement('div');
  box.className = 'qrbig';
  box.innerHTML = "<img alt='QR'><p></p>";
  document.body.appendChild(box);
  const close = () => box.classList.remove('show');
  document.addEventListener('click', e => {
    const q = e.target.closest('img.qr');
    if (q) {
      e.preventDefault(); e.stopPropagation();
      box.querySelector('img').src = q.src;
      box.querySelector('p').textContent = (q.title || '').replace(/^QR · /, '') + ' · page ' + (q.closest('[data-page]') || {dataset: {}}).dataset.page;
      box.classList.add('show');
    } else if (e.target.closest('.qrbig')) close();
  }, true);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
})();
