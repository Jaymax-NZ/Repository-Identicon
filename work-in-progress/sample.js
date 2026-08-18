// 400 identicons straight from identicon.js, for a 20x20 contact sheet.
//
// Keys are `sample-0` .. `sample-399` rather than a random source, so the sheet
// is reproducible: MD5 of a counter is indistinguishable from random for this
// purpose and can be re-derived by anyone reading the numbers afterwards.
//
// SVG rather than PNG, for the same reason js-vectors.js uses it: the grid comes
// back exactly, one <rect> per foreground cell, with no pixel decoding.
//
//   node sample.js [count] > sample.tsv

const crypto = require('crypto');
const Identicon = require('/home/justin/Code/Projects/Repository-Identicon/reference/vendor/identicon.js');

const COUNT = parseInt(process.argv[2] || '400', 10);
const CELL = 10;

for (let n = 0; n < COUNT; n++) {
  const key = `sample-${n}`;
  const md5 = crypto.createHash('md5').update(key).digest('hex');
  const icon = new Identicon(md5, { size: 5 * CELL, margin: 0, format: 'svg' });
  const svg = icon.toString(true);

  // Single quotes, and x before y -- the library's own spelling. Getting this
  // wrong yields an all-empty grid rather than an error, which is exactly how
  // the first attempt at this file failed silently.
  const grid = Array.from({ length: 5 }, () => Array(5).fill(0));
  for (const [, x, y] of svg.matchAll(/<rect\s+x='(\d+)'\s+y='(\d+)'/g)) {
    grid[y / CELL][x / CELL] = 1;
  }

  const [r, g, b] = icon.foreground.map(Math.round);
  console.log([key, md5, grid.map(row => row.join('')).join(','), r, g, b].join('\t'));
}
