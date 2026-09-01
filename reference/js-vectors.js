// Generate identicon conformance vectors from stewartlord/identicon.js.
//
// This file is ours; the library under vendor/ is not. It is committed rather
// than fetched so that vectors.json can be re-derived by anyone, offline, for
// as long as this repository exists -- a reference that has to be downloaded
// is a reference that can disappear, and one did during the week this was
// written.
//
// SVG rather than PNG, because the matrix is then recoverable exactly: the
// library emits one <rect> per *foreground* cell inside a <g> carrying the
// fill, and puts the background on the root element's style. The rects alone
// are the pattern, with no pixel decoding and no resampling to argue about.
//
// Seeds. The seed is the whole of what is hashed, so this takes the finished
// strings and knows nothing about how they were built or what colour map they
// will be drawn under. The reference implementation owns those rules; a second
// copy of either here would be a second thing to forget.
//
//   node js-vectors.js <seed> [seed...]

const crypto = require('crypto');
const Identicon = require('./vendor/identicon.js');

const CELL = 10;

function rgb(rgba) {
  const [r, g, b] = rgba.split(',').map(n => parseInt(n, 10));
  return '#' + [r, g, b].map(v => v.toString(16).padStart(2, '0')).join('');
}

function vector(seed) {
  const md5 = crypto.createHash('md5').update(seed).digest('hex');
  const svg = new Identicon(md5, { size: 50, margin: 0, format: 'svg' }).toString(true);

  const matrix = Array.from({ length: 5 }, () => Array(5).fill(0));
  for (const [, x, y] of svg.matchAll(/<rect\s+x='(\d+)'\s+y='(\d+)'/g)) {
    matrix[y / CELL][x / CELL] = 1;
  }

  // The pattern only. The colour is this project's own rule -- a capped ring
  // at one Oklab lightness -- which this library cannot produce and has no
  // opinion about. The matrix rule is unchanged, so it is still the thing an
  // outside implementation pins.
  return {
    seed,
    md5,
    matrix: matrix.map(r => r.join('')),
  };
}

const argv = process.argv.slice(2);
if (!argv.length) {
  console.error('usage: node js-vectors.js <seed> [seed...]');
  process.exit(2);
}
console.log(JSON.stringify({ vectors: argv.map(vector) }, null, 1));
