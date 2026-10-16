// Rebuild a Lupa online-editor book from ready/lupa_layout.json (made by lupa_layout.py).
// Run inside the Lupa editor tab (online-v3.lupa.co.il/preview/<token>) with the Chrome extension's javascript tool:
//   1. paste this file once (defines window.claudeLupa)
//   2. await claudeLupa.loader()      -> adds a file input; feed it lupa_layout.json with the file_upload tool
//   3. await claudeLupa.build()       -> builds the new tree in memory, returns a summary (nothing saved yet)
//   4. await claudeLupa.save()        -> saves to Lupa (same call the editor makes), then reload the tab
// A backup of the tree as it was when the tab loaded is kept in localStorage "__claude_backup_tree_<time>".
window.claudeLupa = (() => {
  const fiberRoot = () => {
    const el = document.getElementById('root') || document.body.firstElementChild;
    return el[Object.keys(el).find(k => k.startsWith('__reactContainer'))];
  };
  const state = () => {  // the editor's live tree + photo list + theme resources (React state)
    let T = null, ctx = null, RS = null, stack = [fiberRoot()], seen = 0;
    while (stack.length && seen++ < 40000) {
      const f = stack.pop(); if (!f) continue;
      for (let s = f.memoizedState, i = 0; s && i < 40; s = s.next, i++) {
        const v = s.memoizedState; if (!T && v && typeof v === 'object' && v.m_treeV5) T = v;
        if (!RS && v && typeof v === 'object' && v.m_album_resources) RS = v;
      }
      const p = f.memoizedProps;
      if (!ctx && p && p.value && typeof p.value === 'object' && p.value.currentAlbum && p.value.currentAlbum.img_arr) ctx = p.value;
      if (f.child) stack.push(f.child); if (f.sibling) stack.push(f.sibling);
    }
    return { T, arr: ctx.currentAlbum.img_arr, RS: T.m_treeV5Resources || RS };
  };
  // capture the editor's auth header and save URL from its own requests (never printed)
  if (!window.__claudeFetch) {
    const of = window.fetch;
    window.fetch = function (i, o) {
      try {
        if (i instanceof Request && /lupa\.co\.il\/v1/.test(i.url)) {
          const a = i.headers.get('authorization'); if (a) window.__auth = a;
          if (/updatetree3/.test(i.url)) window.__saveUrl = i.url;
        }
      } catch (e) {}
      return of.apply(this, arguments);
    };
    window.__claudeFetch = 1;
  }
  const saveUrl = () => {
    if (window.__saveUrl) return window.__saveUrl;
    // same call the editor makes; built from the book's token (the page's request history may have rolled over)
    const tok = location.pathname.split('/').pop();
    return 'https://groupa.lupa.co.il/v1/editor.aspx?action=editor&isCustomErr=false&cloudcode=public&lang=en&app_version=3.5.27.tf' +
      '&device_type=desktop&image_list=true&show_basket=false&show_friend_basket=false&event_token=' + tok +
      '&force=false&isUpdateCover=false&method=updatetree3';
  };
  return {
    async loader() {
      let inp = document.getElementById('__claude_in');
      if (!inp) {
        inp = document.createElement('input'); inp.type = 'file'; inp.id = '__claude_in';
        inp.setAttribute('aria-label', 'claude layout loader');
        inp.style.cssText = 'position:fixed;left:300px;top:60px;width:200px;height:30px;z-index:2147483647';
        inp.addEventListener('change', async () => { window.__layoutJSON = JSON.parse(await inp.files[0].text()); inp.remove(); });
        document.body.appendChild(inp);
      }
      return 'feed the "claude layout loader" input with lupa_layout.json';
    },
    async build(opts = {}) {  // opts.only = [spread indexes] to rebuild; every other spread is left exactly as it is
      const L = window.__layoutJSON, { T, arr, RS } = state();
      try { localStorage.setItem('__claude_backup_tree_' + Date.now(), JSON.stringify(T.m_treeV5)); } catch (e) {}
      const tree = JSON.parse(JSON.stringify(T.m_treeV5)), b = tree.m_book_subtree;
      const R = RS.m_album_resources;
      const bgRes = n => R.m_bg_resources.find(b => b.m_color_im_id === (n.single ? '' : 'Layflat\\') + String(n.n).padStart(2, '0') + '.jpg');
      const byKey = {}, byTime = {}, oldImg = {};
      arr.forEach(e => {
        const k = e.creation_date + '|' + (e.imageOriginalWidth / e.imageOriginalHeight).toFixed(2);
        (byKey[k] = byKey[k] || []).push(e); (byTime[e.creation_date] = byTime[e.creation_date] || []).push(e);
      });
      T.m_treeV5.m_book_subtree.m_tree_tmages.forEach(i => { oldImg[i.m_unique_id] = i; });
      const anyFrame = T.m_treeV5.m_book_subtree.m_spread_folders.flatMap(s => s.m_child_folders.filter(Boolean))
        .flatMap(c => c.m_child_folders || []).find(f => f && f.m_type === 'IMAGE_TYPE' && f.m_folder_frame);
      const tpl = JSON.stringify(anyFrame);
      let nextId = b.m_next_folderID; const used = new Set(), miss = [], imgs = [];
      const find = k => {
        let c = (byKey[k] || []).filter(e => !used.has(e.uniqueId));
        if (!c.length) {
          const [t, a] = k.split('|');
          c = (byTime[t] || []).filter(e => !used.has(e.uniqueId))
            .sort((x, y) => Math.abs(x.imageOriginalWidth / x.imageOriginalHeight - a) - Math.abs(y.imageOriginalWidth / y.imageOriginalHeight - a));
        }
        return c[0];
      };
      const lay = (set, n, solid) => { const c = set.filter(l => l.m_count === n && !!l.m_isSolid === !!solid); return c.length ? c[0].m_ID : 0; };
      const frames = fs => fs.map((f, k) => {
        const e = find(f.k); if (!e) { miss.push(f.n + ':' + f.k); return null; }
        used.add(e.uniqueId);
        const fr = JSON.parse(tpl);
        Object.assign(fr, { m_folderID: nextId++, m_size: f.w + ', ' + f.h, m_pivot: { IsEmpty: false, X: f.x, Y: f.y }, m_layoutID: k, m_child_folders: [] });
        // Frame styling is explicit (a theme change resets it to the theme's dark grey line).
        // Photos: the thinnest white line that still prints (3 px = 0.25 mm, ).
        // QR codes, title images, the map and blurred backgrounds: no line at all (opacity 0).
        // Width 0 is avoided: Lupa falls back to its dark theme line then.
        fr.m_folder_frame = {
          m_width_px: f.bleed ? 8 : 3,
          m_frame_opacity: f.bleed ? 0 : 1,
          m_image_or_color: '#FFFFFFFF',
          m_text_frame_opacity: 0,
        };
        const ia = e.imageOriginalWidth / e.imageOriginalHeight, fa = f.w / f.h;  // center trim (plan allows <= 5%)
        const crop = ia > fa ? { X: (1 - fa / ia) / 2, Y: 0, Width: fa / ia, Height: 1 } : { X: 0, Y: (1 - ia / fa) / 2, Width: 1, Height: ia / fa };
        const im = oldImg[e.uniqueId] ? JSON.parse(JSON.stringify(oldImg[e.uniqueId])) : {
          m_unique_id: e.uniqueId, m_medium_width_px: e.imageMediumWidth, m_medium_height_px: e.imageMediumHeight, m_alignment: 0,
          m_orientation: 'JPEG_NORMAL', m_faceRects: [], m_image_name: e.image_name, m_status: 'NORMAL_STAT', m_folderID: 0,
          m_crop_rect: null, m_image_opacity: 1, m_text: null, m_isLocked: false };
        im.m_folderID = fr.m_folderID; im.m_crop_rect = crop; imgs.push(im);
        return fr;
      }).filter(Boolean);
      // page-title template: any TEXT_TYPE folder + its text entry in the live tree (Lupa's own "page title")
      const liveTexts = T.m_treeV5.m_book_subtree.m_tree_texts;
      const tFolder = T.m_treeV5.m_book_subtree.m_spread_folders.flatMap(sp => sp.m_child_folders.filter(Boolean))
        .flatMap(c => c.m_child_folders || []).find(f => f && f.m_type === 'TEXT_TYPE' && liveTexts.some(t => t.m_folderID === f.m_folderID));
      const tText = tFolder && liveTexts.find(t => t.m_folderID === tFolder.m_folderID);
      const newTexts = [], rebuilt = new Set();
      const only = opts.only ? new Set(opts.only) : null;
      L.spreads.forEach(s => {
        if (only && !only.has(s.i)) return;
        const kids = b.m_spread_folders[s.i].m_child_folders;
        const want = /LEFT/.test(s.type) ? /LEFT/ : /RIGHT/.test(s.type) ? /RIGHT/ : /LAYFLAT/;
        const child = kids.find(c => c && want.test(c.m_type)) || kids.find(Boolean);
        (child.m_child_folders || []).forEach(f => rebuilt.add(f.m_folderID));
        child.m_child_folders = frames(s.frames);
        if (s.prolog_frames) {  // photo on Lupa's opening-words page (the region facing page 1)
          const pr = kids.find(c => c && c !== child && /RIGHT/.test(c.m_type));
          if (pr) { (pr.m_child_folders || []).forEach(f => rebuilt.add(f.m_folderID)); pr.m_child_folders = frames(s.prolog_frames); }
          else miss.push('prolog region');
        }
        if (s.title && tFolder && tText) {  // editable page title (Lupa's "page title" dialog edits it)
          const wide = /LAYFLAT/.test(child.m_type);
          const tf = JSON.parse(JSON.stringify(tFolder));
          Object.assign(tf, { m_folderID: nextId++, m_size: (wide ? 6616 : 3074) + ', 128',
                              m_pivot: { IsEmpty: false, X: wide ? 3543 : 1772, Y: s.title_bottom ? L.H - 136 : 136 }, m_layoutID: 0, m_child_folders: [] });
          const tt = JSON.parse(JSON.stringify(tText));
          tt.m_folderID = tf.m_folderID; tt.m_text.m_text_str = s.title;
          // no box behind the title; text colour stands out from the page
          tf.m_textbox = { m_font_color: s.title_ink === 'light' ? '#FFFFFFFF' : '#FF1F2328', m_font_opacity: 1,
                           m_text_bg_color: '#FFffffff', m_text_bg_opacity: 0 };
          if (tf.m_background) tf.m_background.m_bg_opacity = 0;
          child.m_child_folders.push(tf); newTexts.push(tt);
        }
        if (s.bg) {  // plain theme background of the same colour family: no drawing under a title or QR
          const r = bgRes({ n: s.bg, single: !/LAYFLAT/.test(child.m_type) });
          if (r) child.m_background = Object.assign({}, child.m_background, { m_unique_id: r.m_unique_id, m_color_im_id: r.m_color_im_id,
            m_direction_type_bg: r.m_direction_type_bg, m_theme_name: r.m_theme_name, m_theme_family: r.m_theme_family });
          else miss.push('bg ' + s.i + ':' + s.bg);
        }
        const n = s.frames.length;
        child.m_layoutID = /LAYFLAT/.test(child.m_type) ? (s.solid ? lay(R.m_layouts_for_album_Set2, 1, true) : lay(R.m_layouts_for_album_Set2, n, false))
          : lay(R.m_layouts_for_album, n, false);
      });
      const alive = new Set();
      const walk = f => { if (!f) return; alive.add(f.m_folderID); (f.m_child_folders || []).forEach(walk); };
      b.m_spread_folders.forEach(walk);
      b.m_tree_texts = b.m_tree_texts.filter(t => alive.has(t.m_folderID) && !rebuilt.has(t.m_folderID)).concat(newTexts);
      if (only) {  // keep the photos of the spreads we did not touch
        const kept = T.m_treeV5.m_book_subtree.m_tree_tmages.filter(i => alive.has(i.m_folderID) && !rebuilt.has(i.m_folderID));
        kept.forEach(i => used.add(i.m_unique_id));
        imgs.push(...kept);
      }
      b.m_tree_tmages = imgs; b.m_next_folderID = nextId; window.__newTree = tree;
      const unplaced = arr.filter(e => !used.has(e.uniqueId)).map(e => e.creation_date + ' ' + e.imageOriginalWidth + 'x' + e.imageOriginalHeight);
      return { spreads: L.spreads.length, placed: imgs.length, titles: newTexts.length, template: !!tText, miss, unplaced };
    },
    check() {  // final QA inside the editor: sharpness, crop, empty frames, overlaps, QR layering, duplicates
      const { T, arr } = state(), B = T.m_treeV5.m_book_subtree, W = 7087, H = 2551;
      const byU = new Map(arr.map(a => [a.uniqueId, a])), imgByF = new Map(B.m_tree_tmages.map(i => [i.m_folderID, i]));
      const F = { lowDpi: [], cropped: [], empty: [], outside: [], overlap: [], qrNotOnTop: [], qrCrossesPhoto: [], dup: [] };
      const used = new Map(); let minDpi = 9999;
      B.m_spread_folders.forEach((sp, si) => {
        const fr = []; const walk = f => { if (!f) return; if (f.m_type === 'IMAGE_TYPE') { const [w, h] = f.m_size.split(',').map(Number);
          const im = imgByF.get(f.m_folderID); fr.push({ x: f.m_pivot.X - w / 2, y: f.m_pivot.Y - h / 2, w, h, im, a: im && byU.get(im.m_unique_id) }); }
          (f.m_child_folders || []).forEach(walk); }; walk(sp);
        fr.forEach(f => { if (!f.a) { F.empty.push(si); return; }
          const c = typeof f.im.m_crop_rect === 'string' ? JSON.parse(f.im.m_crop_rect) : (f.im.m_crop_rect || { Width: 1, Height: 1 });
          f.dpi = Math.round(f.a.imageOriginalWidth * c.Width / f.w * 300); f.lab = f.a.creation_date.slice(5, 16);
          f.bg = f.w * f.h > 0.45 * W * H; f.qr = f.a.imageOriginalWidth === f.a.imageOriginalHeight && f.w < 400;
          f.tile = f.a.imageOriginalHeight <= 900 && f.a.imageOriginalWidth / f.a.imageOriginalHeight > 2.2;
          if (!f.qr && !f.tile) { minDpi = Math.min(minDpi, f.dpi); if (f.dpi < 200) F.lowDpi.push([si, f.lab, f.dpi]); }
          if (!f.bg && !f.qr && !f.tile && (c.Width < 0.94 || c.Height < 0.94)) F.cropped.push([si, f.lab]);
          if (!f.bg && (f.x < -5 || f.y < -5 || f.x + f.w > W + 5 || f.y + f.h > H + 5)) F.outside.push([si, f.lab]);
          if (!f.bg && !f.qr && !f.tile) used.set(f.im.m_unique_id, (used.get(f.im.m_unique_id) || []).concat(si)); });
        const ov = (p, q) => Math.min(p.x + p.w, q.x + q.w) - Math.max(p.x, q.x) > 8 && Math.min(p.y + p.h, q.y + q.h) - Math.max(p.y, q.y) > 8;
        const photos = fr.filter(f => f.a && !f.bg && !f.qr && !f.tile);
        photos.forEach((p, i) => photos.slice(i + 1).forEach(q => { if (ov(p, q)) F.overlap.push([si, p.lab, q.lab]); }));
        fr.forEach((q, k) => { if (!q.qr) return;
          if (fr.slice(k + 1).some(f => !f.qr)) F.qrNotOnTop.push([si, q.lab]);
          photos.forEach(p => { const inside = q.x >= p.x && q.y >= p.y && q.x + q.w <= p.x + p.w && q.y + q.h <= p.y + p.h;
            if (ov(q, p) && !inside) F.qrCrossesPhoto.push([si, q.lab, p.lab]); }); });
      });
      F.dup = [...used].filter(([k, v]) => v.length > 1).map(([k, v]) => [byU.get(k).creation_date, v]);
      return JSON.stringify(Object.assign({ spreads: B.m_spread_folders.length, frames: B.m_tree_tmages.length, minDpi }, F));
    },
    patch(o = {}) {  // small edits without rebuilding a page (keeps the user's own edits in the editor):
      // o.swaps = [[oldTime, newTime, ratio]]  re-made tile/photo; o.moves = [[spread, time, dx, dy]];
      // o.coverText = [from, to] (spine / cover texts). Then: await claudeLupa.save()
      const { T, arr } = state(), tree = JSON.parse(JSON.stringify(T.m_treeV5)), B = tree.m_book_subtree, out = { swaps: 0, moves: 0, text: 0 };
      const byU = new Map(arr.map(a => [a.uniqueId, a])), ratio = a => a.imageOriginalWidth / a.imageOriginalHeight;
      (o.swaps || []).forEach(([ot, nt, r]) => {
        const ne = arr.filter(a => a.creation_date === nt && Math.abs(ratio(a) - r) < 0.05); if (ne.length !== 1) return;
        B.m_tree_tmages.forEach(im => { const a = byU.get(im.m_unique_id);
          if (a && a.creation_date === ot && Math.abs(ratio(a) - r) < 0.05) { Object.assign(im, { m_unique_id: ne[0].uniqueId,
            m_medium_width_px: ne[0].imageMediumWidth, m_medium_height_px: ne[0].imageMediumHeight, m_image_name: ne[0].image_name }); out.swaps++; } }); });
      const imgByF = new Map(B.m_tree_tmages.map(i => [i.m_folderID, i]));
      (o.moves || []).forEach(([si, t, dx, dy]) => { const walk = f => { if (!f) return; if (f.m_type === 'IMAGE_TYPE') {
          const im = imgByF.get(f.m_folderID), a = im && byU.get(im.m_unique_id);
          if (a && a.creation_date === t) { f.m_pivot.X += dx; f.m_pivot.Y += dy; out.moves++; } } (f.m_child_folders || []).forEach(walk); };
        walk(B.m_spread_folders[si]); });
      if (o.coverText) { tree.m_cover_subtree.m_tree_texts.forEach(t => { if (t.m_text && t.m_text.m_text_str && t.m_text.m_text_str.includes(o.coverText[0])) {
        t.m_text.m_text_str = t.m_text.m_text_str.split(o.coverText[0]).join(o.coverText[1]); out.text++; } }); window.__isCover = true; }
      window.__newTree = tree; return out;
    },
    themeInfo() {  // the book's theme backgrounds, for lupa_titles.py: save the result as ready/lupa_theme.json
      const { T, RS } = state(), t = T.m_treeV5, R = RS.m_album_resources;
      const num = c => { const m = /(\d+)\.jpg$/.exec(c || ''); return m ? +m[1] : 0; };
      const live = t.m_book_subtree.m_spread_folders.map(sp => {
        const c = (sp.m_child_folders || []).find(x => x && x.m_background && x.m_background.m_color_im_id);
        return c ? num(c.m_background.m_color_im_id) : 0;
      });
      const any = t.m_book_subtree.m_spread_folders.flatMap(s => s.m_child_folders || []).find(x => x && x.m_background && x.m_background.m_theme_name);
      const theme = any ? any.m_background.m_theme_name : t.m_album_theme;
      const count = Math.max(...R.m_bg_resources.map(b => num(b.m_color_im_id)));
      return JSON.stringify({ format: t.m_format, theme, count, live,
        url: `https://assets.lupa.co.il/resources/format${t.m_format}/${theme}/medium/{}{:02d}.jpg` });
    },
    async cover(o) {  // front cover photo -> the file with the title drawn in; Lupa's own front-cover title texts removed
      const { T, arr } = state();
      try { localStorage.setItem('__claude_backup_cover_' + Date.now(), JSON.stringify(T.m_treeV5.m_cover_subtree)); } catch (e) {}
      const tree = JSON.parse(JSON.stringify(T.m_treeV5)), c = tree.m_cover_subtree;
      const e = arr.find(x => x.creation_date === o.time && Math.abs(x.imageOriginalWidth / x.imageOriginalHeight - o.ratio) < 0.01);
      if (!e) return { error: 'cover photo not found in the upload list' };
      const im = c.m_tree_tmages.find(i => i.m_folderID === o.imageFolder);
      Object.assign(im, { m_unique_id: e.uniqueId, m_medium_width_px: e.imageMediumWidth, m_medium_height_px: e.imageMediumHeight, m_image_name: e.image_name });
      const drop = new Set(o.dropTitles);
      c.m_spread_folders[0].m_child_folders = c.m_spread_folders[0].m_child_folders.filter(f => !f || !drop.has(f.m_folderID));
      c.m_tree_texts = c.m_tree_texts.filter(t => !drop.has(t.m_folderID));
      window.__newTree = tree; window.__isCover = true;
      return { ok: true, uniqueId: e.uniqueId, texts: c.m_tree_texts.map(t => t.m_text && t.m_text.m_text_str) };
    },
    async save() {
      if (!window.__auth) {  // fallback: the signed-in user's token kept by the editor (never printed)
        try { const k = Object.keys(localStorage).find(k => /^user-storage$|^User/.test(k)); const t = JSON.parse(localStorage[k]).state.user.token; if (t) window.__auth = 'Bearer ' + t; } catch (e) {}
      }
      let w = 0; while (!window.__auth && w++ < 40) await new Promise(r => setTimeout(r, 1000));  // editor pings every ~20 s
      const fd = new FormData(); fd.append('tree', JSON.stringify(window.__newTree));
      const url = window.__isCover ? saveUrl().replace('isUpdateCover=false', 'isUpdateCover=true') : saveUrl();
      window.__isCover = false;
      const r = await fetch(new Request(url, { method: 'POST', body: fd, headers: { authorization: window.__auth } }));
      const j = await r.json();
      if (j.isValid) {  // keep the editor's local copy in step, so a reload shows the saved book
        const ps = JSON.parse(localStorage.getItem('photo-album-storage'));
        window.__newTree.m_creationTime = j.payload.m_creationTime;
        ps.state.album.m_treeV5 = window.__newTree; ps.state.m_creationTime = j.payload.m_creationTime; ps.state.pendingSync = false;
        localStorage.setItem('photo-album-storage', JSON.stringify(ps));
      }
      return { ok: j.isValid, error: j.Error };
    },
  };
})();
'claudeLupa ready';
