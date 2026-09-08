const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const S = 256;
const C = {
  grassA: [143,209,98],  grassB: [121,184,78],
  leftA:  [138,90,51],   leftB:  [122,78,43],
  rightA: [107,69,38],   rightB: [94,60,33],
  stripA: [110,160,72],  stripB: [94,138,60], stripC: [80,118,52]
};
const hash = (x, y) => {
  let h = (x * 374761393 + y * 668265263) >>> 0;
  h = ((h ^ (h >>> 13)) * 1274126177) >>> 0;
  return (h ^ (h >>> 16)) >>> 0;
};

function colorAt(x, y) {
  const dx = Math.abs(x - 128), dy = Math.abs(y - 74);
  if (dx / 106 + dy / 53 <= 1) return hash(x >> 2, y >> 2) % 3 ? C.grassA : C.grassB; // الوجه العلوي
  let u = (x - 22) / 106, v = (y - 74 - 53 * u) / 106;                                 // الوجه الأيسر
  if (u >= 0 && u < 1 && v >= 0 && v < 1) {
    if (v < 0.14) return hash(x >> 1, y >> 1) % 2 ? C.stripA : C.stripB;
    return hash(x >> 2, y >> 2) % 3 ? C.leftA : C.leftB;
  }
  u = (234 - x) / 106; v = (y - 74 - 53 * u) / 106;                                    // الوجه الأيمن
  if (u >= 0 && u < 1 && v >= 0 && v < 1) {
    if (v < 0.14) return hash(x >> 1, y >> 1) % 2 ? C.stripB : C.stripC;
    return hash(x >> 2, y >> 2) % 3 ? C.rightA : C.rightB;
  }
  return null;
}

const raw = Buffer.alloc(S * (S * 4 + 1));
let o = 0;
for (let y = 0; y < S; y++) {
  raw[o++] = 0;
  for (let x = 0; x < S; x++) {
    const c = colorAt(x, y);
    if (c) { raw[o++] = c[0]; raw[o++] = c[1]; raw[o++] = c[2]; raw[o++] = 255; }
    else o += 4;
  }
}

const T = [];
for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; T[n] = c >>> 0; }
const crc32 = b => { let c = 0xFFFFFFFF; for (const x of b) c = T[(c ^ x) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
const chunk = (t, d) => {
  const len = Buffer.alloc(4); len.writeUInt32BE(d.length);
  const body = Buffer.concat([Buffer.from(t), d]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
};
const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(S, 0); ihdr.writeUInt32BE(S, 4); ihdr[8] = 8; ihdr[9] = 6;
const png = Buffer.concat([
  Buffer.from([137,80,78,71,13,10,26,10]),
  chunk('IHDR', ihdr),
  chunk('IDAT', zlib.deflateSync(raw, { level: 9 })),
  chunk('IEND', Buffer.alloc(0))
]);

const head = Buffer.alloc(6); head.writeUInt16LE(1, 2); head[4] = 1;
const entry = Buffer.alloc(16);
entry.writeUInt16LE(1, 4); entry.writeUInt16LE(32, 6);
entry.writeUInt32LE(png.length, 8); entry.writeUInt32LE(22, 12);

const dir = path.join(__dirname, 'build');
fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(path.join(dir, 'icon.png'), png);
fs.writeFileSync(path.join(dir, 'icon.ico'), Buffer.concat([head, entry, png]));
console.log('OK: build/icon.png + build/icon.ico');
