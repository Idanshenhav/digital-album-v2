# Photo locations (for sections and the route map)

A shared album link hides GPS, and downloaded files have it stripped. The album **owner** sees locations when
signed in to Google Photos. Ask the user which way works for them:

## A. The owner's signed-in Google Photos (best)
1. The user opens Google Photos in their Chrome, signed in as the album owner. Note the account number in the
   address (`/u/0/`, `/u/1/` …). Open the same album: `https://photos.google.com/u/<N>/share/<ALBUM_ID>?key=<KEY>`
   (ALBUM_ID and KEY come from the shared link after it redirects).
2. Pick 3 photos per place (first, middle, last of each section; phone photos carry GPS most reliably).
   Photo ids are the `id` field in items.json.
3. Run this in the page with the browser's JavaScript tool, ~15 sections per call (outputs get cut):

"""
const W = window.WIZ_global_data, KEY = '<KEY>', U = '<ACCOUNT NUMBER, e.g. 0 or 1>';
const rpc = async (rid, args) => {
  const req = [[[rid, JSON.stringify(args), null, "generic"]]];
  const body = 'f.req=' + encodeURIComponent(JSON.stringify(req)) + '&at=' + encodeURIComponent(W.SNlM0e) + '&';
  const url = '/u/' + U + '/_/PhotosUi/data/batchexecute?rpcids=' + rid + '&source-path=' + encodeURIComponent(location.pathname)
    + '&f.sid=' + W.FdrFJe + '&bl=' + W.cfb2h + '&hl=en&_reqid=' + Math.floor(Math.random() * 900000 + 100000) + '&rt=c';
  const t = await (await fetch(url, {method: 'POST', credentials: 'include',
    headers: {'content-type': 'application/x-www-form-urlencoded;charset=UTF-8'}, body})).text();
  const o = JSON.parse(t.split('\n').find(l => l.includes('wrb.fr'))); return o[0][2] ? JSON.parse(o[0][2]) : null;
};
const pick = {"S03": ["<photo id>", "<photo id>", "<photo id>"] /* … */};
const res = {};
for (const [s, ids] of Object.entries(pick)) for (const id of ids) {
  const a = (await rpc('fDcn4b', [id, null, KEY, null, null, [2]]))?.[0];
  const ll = a && ((a[9] && a[9][0]) || (a[13] && a[13][0]));   // [lat*1e7, lng*1e7]
  if (ll) (res[s] = res[s] || []).push([+(ll[0] / 1e7).toFixed(3), +(ll[1] / 1e7).toFixed(3)]);
}
Object.entries(res).map(([s, v]) => s + ':' + JSON.stringify(v)).join(' ')
"""

4. Use one point per stop for STOPS and keep en-route points as ROUTE waypoints. A point far from its place is
   usually a drive photo: a good waypoint. Photos uploaded by other people may have no location.

## B. Without sign-in
- Ask the user to list the stops in order (town names); look up coordinates; use place names from the photos
  (signs, landmarks) to check the order. Or a Google Takeout export of the album (JSON files hold GPS).
