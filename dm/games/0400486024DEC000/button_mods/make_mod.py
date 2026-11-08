# Button-glyph mod for Zelda: Ocarina of Time (Switch 2) under nxnative: Xbox or PS5 labels, placed by position (nxnative maps an Xbox/PS pad by position:
# right button = Switch A, bottom = B, top = X, left = Y; pad_apple.h). Writes a RomFS overlay folder (DM_ROMFS_OVERLAY) with the font and the HUD textures changed.
# usage: make_mod.py xbox|ps5 <overlay dir> <RomFS image or folder> <ClarimoUDPE-DemiBold.otf> (make_mods.py runs it for both)
import sys, os, io, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import btnlib, bfotf, bntx, tex
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from shapely import affinity
from PIL import Image, ImageDraw, ImageFont

LAYOUT = sys.argv[1]; OUT = sys.argv[2]; btnlib.set_romfs(sys.argv[3]); CLARIMO = sys.argv[4]; PREVIEW = None
assert LAYOUT in ('xbox', 'ps5')
FONT_P = 'Font2/Scalable/External.Nin_Ounce_NVN2.bfotf.zs'
BNTX_P = 'UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.bntx.zs'

# Switch label at each position -> this layout's label there
FACE = {'xbox': {'A': 'B', 'B': 'A', 'X': 'Y', 'Y': 'X'},
        'ps5': {'A': 'circle', 'B': 'cross', 'X': 'triangle', 'Y': 'square'}}[LAYOUT]
SHOULDER = {'xbox': {'L': 'LB', 'R': 'RB', 'ZL': 'LT', 'ZR': 'RT'},
            'ps5': {'L': 'L1', 'R': 'R1', 'ZL': 'L2', 'ZR': 'R2'}}[LAYOUT]

# ---------- symbols (font units: cap height 250, centred on 0,0) ----------
SW = 44   # stroke width, about the weight of the font's knocked-out letters
def symbol(name):
    h = SW / 2
    if name == 'circle':
        return Point(0, 0).buffer(120, 32).difference(Point(0, 0).buffer(120 - SW, 32))
    if name == 'cross':
        a = 98
        return unary_union([LineString([(-a, -a), (a, a)]).buffer(h, cap_style='flat'),
                            LineString([(-a, a), (a, -a)]).buffer(h, cap_style='flat')])
    if name == 'triangle':
        R = 152; pts = [(R * np.cos(np.radians(90 + 120 * k)), R * np.sin(np.radians(90 + 120 * k)) - 22) for k in range(3)]
        outer = Polygon(pts); return outer.difference(outer.buffer(-SW, join_style='mitre'))
    if name == 'square':
        s = 108; outer = box(-s, -s, s, s); return outer.difference(outer.buffer(-SW, join_style='mitre'))
    if name == 'menu':   # three bars
        return unary_union([box(-95, y - 17, 95, y + 17) for y in (-62, 0, 62)])
    if name == 'view':   # two overlapping windows
        back = box(-105, -40, 45, 95); front = box(-45, -95, 105, 40)
        ring = lambda b: b.difference(b.buffer(-30, join_style='mitre'))
        return unary_union([ring(back).difference(front), ring(front)])
    if name == 'create':   # a small screen with three rays (the PS5 Create button)
        scr = box(-70, -90, 70, 10); scr = scr.difference(scr.buffer(-28, join_style='mitre'))
        rays = [LineString([(0, 40), (0, 105)]).buffer(15, cap_style='flat'),
                LineString([(-40, 35), (-80, 85)]).buffer(15, cap_style='flat'),
                LineString([(40, 35), (80, 85)]).buffer(15, cap_style='flat')]
        return unary_union([scr] + rays)
    raise KeyError(name)

def polys(geom):
    return list(geom.geoms) if hasattr(geom, 'geoms') else [geom]

# ---------- font ----------
clarimo = TTFont(CLARIMO); cgs = clarimo.getGlyphSet(); ccmap = clarimo.getBestCmap()
CAP = clarimo['OS/2'].sCapHeight or 700

def contours_of(gs, g):
    p = RecordingPen(); gs[g].draw(p); out = []; cur = []
    for op, a in p.value:
        cur.append((op, a))
        if op in ('closePath', 'endPath'): out.append(cur); cur = []
    return out

def area(c):
    pts = []
    for op, a in c:
        pts += list(a)
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) / 2

def bbox(c):
    pts = [p for op, a in c for p in a]
    return min(x for x, y in pts), min(y for x, y in pts), max(x for x, y in pts), max(y for x, y in pts)

def replay(c, pen):
    for op, a in c: getattr(pen, op)(*a)

def text_width(s, scale):
    return sum(clarimo['hmtx'][ccmap[ord(ch)]][0] for ch in s) * scale

def draw_text_holes(pen, s, cx, cy, cap=250):
    scale = cap / CAP; w = text_width(s, scale); x = cx - w / 2; y = cy - cap / 2
    for ch in s:
        g = ccmap[ord(ch)]
        tp = TransformPen(ReverseContourPen(pen), (scale, 0, 0, scale, x, y))
        cgs[g].draw(tp); x += clarimo['hmtx'][g][0] * scale

K = 0.5522847498
def circle(pen, cx, cy, r, cw):
    # four cubic arcs; cw=True draws clockwise (a hole in the counter-clockwise base)
    s = -1 if cw else 1
    pts = [(cx + r, cy), (cx, cy + s * r), (cx - r, cy), (cx, cy - s * r)]
    pen.moveTo(pts[0])
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        if i % 2 == 0: c1 = (a[0], a[1] + s * K * r * (1 if i == 0 else -1)); c2 = (b[0] + K * r * (1 if i == 0 else -1), b[1])
        else: c1 = (a[0] - K * r * (1 if i == 1 else -1), a[1]); c2 = (b[0], b[1] + s * K * r * (1 if i == 1 else -1))
        pen.curveTo(c1, c2, b)
    pen.closePath()

def draw_poly_holes(pen, geom, cx, cy):
    if geom == 'circle':   # the PS circle: a ring drawn with curves
        circle(pen, cx, cy, 120, True); circle(pen, cx, cy, 120 - SW, False); return
    for p in polys(geom):
        p = orient(affinity.translate(p, cx, cy), sign=-1.0)   # exterior clockwise: a hole in the counter-clockwise base
        for ring in [p.exterior] + list(p.interiors):
            pts = list(ring.coords)[:-1]; pen.moveTo(pts[0])
            for q in pts[1:]: pen.lineTo(q)
            pen.closePath()

def build_font():
    raw, did = btnlib.get(FONT_P); f = TTFont(io.BytesIO(bfotf.dec(raw)), recalcTimestamp=False)
    td = f['CFF '].cff.topDictIndex[0]; cs = td.CharStrings; gs = f.getGlyphSet(); hm = f['hmtx']
    G = lambda cp: 'uni%04X' % cp
    face = {'A': 0xE040, 'B': 0xE041, 'X': 0xE042, 'Y': 0xE043}
    orig = {g: copy.deepcopy(cs[g]) for g in cs.keys()}
    def new_glyph(g, base_outer_of, holes):
        outer = [c for c in contours_of(gs, base_outer_of) if area(c) > 0]
        outer = max(outer, key=lambda c: abs(area(c)))
        pen = T2CharStringPen(hm[g][0], gs)
        replay(outer, pen); holes(pen, bbox(outer))
        cs[g] = pen.getCharString(private=td.Private, globalSubrs=f['CFF '].cff.GlobalSubrs)
    if LAYOUT == 'xbox':
        for sw, lab in FACE.items():   # the glyph at Switch A's place becomes the original B glyph, and so on
            g = G(face[sw]); src = G(face[lab]); cs[g] = copy.deepcopy(orig[src]); hm[g] = hm[src]
    else:
        for sw, lab in FACE.items():
            sym = 'circle' if lab == 'circle' else symbol(lab)
            new_glyph(G(face[sw]), G(face[sw]), lambda pen, bb, sym=sym: draw_poly_holes(pen, sym, (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2))
    for sw, cp in {'L': 0xE044, 'R': 0xE045, 'ZL': 0xE046, 'ZR': 0xE047}.items():
        lab = SHOULDER[sw]; g = G(cp)
        hole = [c for c in contours_of(gs, g) if area(c) < 0]
        hb = bbox(max(hole, key=lambda c: abs(area(c)))) if hole else None
        def holes(pen, bb, lab=lab, hb=hb):
            cy = (hb[1] + hb[3]) / 2 if hb else (bb[1] + bb[3]) / 2
            draw_text_holes(pen, lab, (bb[0] + bb[2]) / 2, cy, cap=200)
        new_glyph(g, g, holes)
    plus_minus = {'xbox': ('menu', 'view'), 'ps5': ('menu', 'create')}[LAYOUT]
    for cp, sym in zip((0xE04B, 0xE04C), plus_minus):
        geom = affinity.scale(symbol(sym), 0.95, 0.95, origin=(0, 0))
        new_glyph(G(cp), G(cp), lambda pen, bb, geom=geom: draw_poly_holes(pen, geom, (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2))
    b = io.BytesIO(); f.save(b); f = TTFont(io.BytesIO(b.getvalue()), recalcTimestamp=False)
    from fontTools import subset   # keeps every glyph; drops unused subroutines and the long name records
    o = subset.Options(); o.name_IDs = [1, 2, 4, 6]; o.notdef_outline = True; o.glyph_names = True; o.layout_features = ['*']
    o.drop_tables = []; o.recalc_bounds = True
    ss = subset.Subsetter(o); ss.populate(glyphs=f.getGlyphOrder()); ss.subset(f)
    b = io.BytesIO(); f.save(b); otf = b.getvalue()
    limit = bfotf.size_of(raw)
    if len(otf) > limit: raise SystemExit(f'font is {len(otf)} bytes, the original {limit}: too big for the size table')
    otf += b'\0' * (limit - len(otf))
    out = bfotf.enc(otf); assert len(out) == len(raw), (len(out), len(raw))
    return otf, btnlib.zs(out, did)

# ---------- textures ----------
SS = 4   # supersampling for the drawn symbols and text
def raster(geom, size, scale, cx, cy):
    im = Image.new('L', (size[0] * SS, size[1] * SS), 0); dr = ImageDraw.Draw(im)
    for p in polys(geom):
        tr = lambda ring: [((x * scale + cx) * SS, (cy - y * scale) * SS) for x, y in ring.coords]
        dr.polygon(tr(p.exterior), fill=255)
        for r in p.interiors: dr.polygon(tr(r), fill=0)
    return np.asarray(im.resize(size, Image.LANCZOS), np.float32) / 255

def raster_text(s, size, cap_px, cx, cy):
    big = cap_px * SS; f = ImageFont.truetype(CLARIMO, int(round(big * clarimo['head'].unitsPerEm / CAP)))
    im = Image.new('L', (size[0] * SS, size[1] * SS), 0); dr = ImageDraw.Draw(im)
    l, t, r, b = dr.textbbox((0, 0), s, font=f, anchor='ls')
    dr.text((cx * SS - (l + r) / 2, cy * SS + big / 2), s, font=f, fill=255, anchor='ls')
    return np.asarray(im.resize(size, Image.LANCZOS), np.float32) / 255

def alpha_bbox(a, thr=128):
    ys, xs = np.nonzero(a >= thr); return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1

def build_bntx():
    d, did = btnlib.get(BNTX_P); d = bytearray(d); t = {e['name']: e for e in bntx.brtis(bytes(d))}
    def rng(n): e = t[n]; o = e['mipoffs'][0]; return o, o + e['size']
    def put(n, img):
        o, e2 = rng(n); d[o:e2] = tex.write(bytes(d), t[n], img)
    orig = {n: tex.read(bytes(d), t[n]) for n in t if n.startswith(('KeyTexFont', 'OcarinaButton'))}
    if LAYOUT == 'xbox':
        # swap the raw blocks (same size and format), pairwise
        for pre in ('KeyTexFont', 'OcarinaButton'):
            for a, b in (('A', 'B'), ('X', 'Y')):
                ao, ae = rng(f'{pre}{a}_00'); bo, be = rng(f'{pre}{b}_00')
                A_, B_ = bytes(d[ao:ae]), bytes(d[bo:be]); d[ao:ae] = B_; d[bo:be] = A_
    else:
        for sw, lab in FACE.items():
            # HUD letter: an alpha mask, white
            n = f'KeyTexFont{sw}_00'; a = orig[n]; x0, y0, x1, y1 = alpha_bbox(a)
            cap = y1 - y0; sc = cap / 250 * 1.0
            m = raster(symbol(lab), (a.shape[1], a.shape[0]), sc, (x0 + x1) / 2, (y0 + y1) / 2)
            put(n, (m * 255).round().astype(np.uint8))
            # ocarina: white disc, black letter
            n = f'OcarinaButton{sw}_00'; im = orig[n].astype(np.float32)
            dark = (im[..., :3].mean(-1) < 128) & (im[..., 3] > 200)
            x0, y0, x1, y1 = alpha_bbox(dark.astype(np.uint8) * 255)
            cap = y1 - y0; sc = cap / 250
            ax0, ay0, ax1, ay1 = alpha_bbox(im[..., 3])
            m = raster(symbol(lab), (im.shape[1], im.shape[0]), sc, (ax0 + ax1) / 2, (ay0 + ay1) / 2)
            rgb = 255 * (1 - m); out = im.copy(); out[..., :3] = rgb[..., None]
            put(n, out.round().clip(0, 255).astype(np.uint8))
    for sw in ('L', 'R'):
        n = f'OcarinaButton{sw}_00'; im = orig[n].astype(np.float32)
        dark = (im[..., :3].mean(-1) < 128) & (im[..., 3] > 200)
        x0, y0, x1, y1 = alpha_bbox(dark.astype(np.uint8) * 255)
        m = raster_text(SHOULDER[sw], (im.shape[1], im.shape[0]), (y1 - y0) * 0.86, im.shape[1] / 2, (y0 + y1) / 2)
        out = im.copy(); out[..., :3] = (255 * (1 - m))[..., None]
        put(n, out.round().clip(0, 255).astype(np.uint8))
    # the "Controles básicos" guide: the controller art, its dark variant and shadow, and the callout lines, for every slot
    import guide_build
    for n, img in guide_build.textures(bytes(d), t, LAYOUT).items():
        o, e2 = rng(n); d[o:e2] = tex.write(bytes(d), t[n], img, q=60)
    return bytes(d), None, did

def zs_plain(b):
    try: from compression import zstd
    except ImportError: from backports import zstd   # Python < 3.14
    return zstd.compress(b, level=6)

if __name__ == '__main__':
    otf, font_zs = build_font()
    d, _, did = build_bntx()
    bntx_zs = btnlib.zs(d, did) if did else zs_plain(d)
    for p, data in ((FONT_P, font_zs), (BNTX_P, bntx_zs)):
        q = os.path.join(OUT, p); os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q + '.part', 'wb').write(data); os.replace(q + '.part', q)
        print('wrote', p, len(data))
    if PREVIEW:
        fnt = ImageFont.truetype(io.BytesIO(otf), 72)
        sheet = Image.new('RGBA', (1300, 470), (60, 60, 60, 255)); dr = ImageDraw.Draw(sheet)
        dr.text((20, 10), ''.join(chr(c) for c in (0xE040, 0xE041, 0xE042, 0xE043, 0xE044, 0xE045, 0xE046, 0xE047, 0xE04B, 0xE04C)), font=fnt, fill='white')
        t = {e['name']: e for e in bntx.brtis(d)}
        names = ['KeyTexFontA_00', 'KeyTexFontB_00', 'KeyTexFontX_00', 'KeyTexFontY_00', 'OcarinaButtonA_00', 'OcarinaButtonB_00', 'OcarinaButtonX_00', 'OcarinaButtonY_00', 'OcarinaButtonL_00', 'OcarinaButtonR_00']
        for i, n in enumerate(names):
            im = tex.read(d, t[n]); rgba = np.dstack([np.full_like(im, 255)] * 3 + [im]) if im.ndim == 2 else im
            p = Image.fromarray(rgba, 'RGBA').resize((110, 110)); sheet.alpha_composite(p, (20 + (i % 5) * 130, 120 + (i // 5) * 170))
            dr.text((20 + (i % 5) * 130, 235 + (i // 5) * 170), n.replace('_00', ''), fill='yellow')
        sheet.save(PREVIEW)
