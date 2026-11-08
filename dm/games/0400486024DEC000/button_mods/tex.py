import numpy as np
import astc_encoder as A
def gob_off(x, y):
    # Switch 2 GOB: 16-byte pieces ordered x5 y2 x4 y1 y0 (nvn_deswizzle.h)
    return ((x // 32) % 2) * 256 + ((y // 4) % 2) * 128 + ((x // 16) % 2) * 64 + ((y // 2) % 2) * 32 + (y % 2) * 16 + (x % 16)
def bl_map(wb, rows, bh):
    # byte offset in the swizzled image for each (row, byte) of a linear image wb bytes wide, rows rows
    B = 1 << bh; gpr = (wb + 63) // 64
    y = np.arange(rows)[:, None]; x = np.arange(wb)[None, :]
    off = (y // (8 * B)) * (gpr * B * 512) + (x // 64) * (B * 512) + ((y % (8 * B)) // 8) * 512 + gob_off(x, y)
    return off
def deswizzle(data, wb, rows, bh):
    m = bl_map(wb, rows, bh); return np.frombuffer(data, np.uint8)[m]
def swizzle(lin, size, wb, rows, bh, base=None):
    m = bl_map(wb, rows, bh); out = np.zeros(size, np.uint8) if base is None else np.frombuffer(base, np.uint8).copy()
    out[m] = lin; return out.tobytes()
# BC4
def bc4_decode(blocks, bw, bhh):
    b = blocks.reshape(bhh, bw, 8).astype(np.int32)
    r0 = b[..., 0]; r1 = b[..., 1]
    pal = np.zeros(b.shape[:2] + (8,), np.int32); pal[..., 0] = r0; pal[..., 1] = r1
    big = r0 > r1
    for i in range(1, 7):
        pal[..., i + 1] = np.where(big, ((7 - i) * r0 + i * r1) // 7, 0)
    for i in range(1, 5):
        pal[..., i + 1] = np.where(big, pal[..., i + 1], ((5 - i) * r0 + i * r1) // 5)
    pal[..., 6] = np.where(big, pal[..., 6], 0); pal[..., 7] = np.where(big, pal[..., 7], 255)
    bits = np.zeros(b.shape[:2], np.uint64)
    for k in range(6): bits |= b[..., 2 + k].astype(np.uint64) << np.uint64(8 * k)
    out = np.zeros((bhh * 4, bw * 4), np.uint8)
    for py in range(4):
        for px in range(4):
            idx = ((bits >> np.uint64(3 * (py * 4 + px))) & np.uint64(7)).astype(np.int64)
            out[py::4, px::4] = np.take_along_axis(pal, idx[..., None], 2)[..., 0]
    return out
def bc4_encode(img):
    h, w = img.shape; bw, bhh = w // 4, h // 4
    out = np.zeros((bhh, bw, 8), np.uint8)
    for by in range(bhh):
        for bx in range(bw):
            blk = img[by*4:by*4+4, bx*4:bx*4+4].astype(np.int32).ravel()
            lo, hi = int(blk.min()), int(blk.max())
            if hi == lo:
                out[by, bx, 0] = hi; out[by, bx, 1] = lo; continue   # r0 == r1: 6-value mode, all index 0 = r0
            r0, r1 = hi, lo
            pal = np.array([r0, r1] + [((7 - i) * r0 + i * r1) // 7 for i in range(1, 7)])
            idx = np.abs(blk[:, None] - pal[None, :]).argmin(1)
            bits = 0
            for k, v in enumerate(idx): bits |= int(v) << (3 * k)
            out[by, bx, 0] = r0; out[by, bx, 1] = r1
            out[by, bx, 2:] = np.frombuffer(bits.to_bytes(6, 'little'), np.uint8)
    return out.reshape(-1)
def _ctx(srgb, q=100):
    cfg = A.ASTCConfig(A.ASTCProfile.LDR_SRGB if srgb else A.ASTCProfile.LDR, 4, 4, 1, q)
    return A.ASTCContext(cfg)
SW = A.ASTCSwizzle.from_str('RGBA')
def astc_decode(lin_blocks, w, h, srgb=True):
    img = A.ASTCImage(A.ASTCType.U8, w, h, 1)
    _ctx(srgb).decompress(lin_blocks.tobytes(), img, SW)
    return np.frombuffer(img.data, np.uint8).reshape(h, w, 4)
def astc_encode(rgba, srgb=True, q=100):
    h, w = rgba.shape[:2]
    img = A.ASTCImage(A.ASTCType.U8, w, h, 1, np.ascontiguousarray(rgba, np.uint8).tobytes())
    return np.frombuffer(_ctx(srgb, q).compress(img, SW), np.uint8)
def read(d, e):
    off = e['mipoffs'][0]; data = d[off:off + e['size']]
    w, h = e['w'], e['h']; bw, bhh = (w + 3) // 4, (h + 3) // 4
    if e['fmt'] >> 8 == 0x1d:
        lin = deswizzle(data, bw * 8, bhh, e['bh'])
        return bc4_decode(lin.reshape(-1), bw, bhh)[:h, :w]
    if e['fmt'] >> 8 == 0x2d:
        lin = deswizzle(data, bw * 16, bhh, e['bh'])
        return astc_decode(lin.reshape(-1), w, h, srgb=(e['fmt'] & 0xff) == 6)
    raise ValueError(hex(e['fmt']))
def write(d, e, img, q=100):
    # returns new bytes for the texture's data range (same size and swizzle)
    off = e['mipoffs'][0]; base = d[off:off + e['size']]
    w, h = e['w'], e['h']; bw, bhh = (w + 3) // 4, (h + 3) // 4
    if e['fmt'] >> 8 == 0x1d:
        pad = np.zeros((bhh * 4, bw * 4), np.uint8); pad[:h, :w] = img
        lin = bc4_encode_fast(pad).reshape(bhh, bw * 8)
        return swizzle(lin, e['size'], bw * 8, bhh, e['bh'], base)
    if e['fmt'] >> 8 == 0x2d:
        lin = astc_encode(img, srgb=(e['fmt'] & 0xff) == 6, q=q).reshape(bhh, bw * 16)
        return swizzle(lin, e['size'], bw * 16, bhh, e['bh'], base)
    raise ValueError(hex(e['fmt']))

def bc4_encode_fast(img):
    h, w = img.shape; bw, bhh = w // 4, h // 4
    b = img.reshape(bhh, 4, bw, 4).transpose(0, 2, 1, 3).reshape(bhh, bw, 16).astype(np.int32)
    hi = b.max(-1); lo = b.min(-1)
    pal = np.stack([hi, lo] + [((7 - i) * hi + i * lo) // 7 for i in range(1, 7)], -1)
    idx = np.abs(b[..., :, None] - pal[..., None, :]).argmin(-1).astype(np.uint64)
    idx[hi == lo] = 0
    bits = np.zeros((bhh, bw), np.uint64)
    for k in range(16): bits |= idx[..., k] << np.uint64(3 * k)
    out = np.zeros((bhh, bw, 8), np.uint8); out[..., 0] = hi; out[..., 1] = lo
    for k in range(6): out[..., 2 + k] = ((bits >> np.uint64(8 * k)) & np.uint64(255)).astype(np.uint8)
    return out.reshape(-1)
