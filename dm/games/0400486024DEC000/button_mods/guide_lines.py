# Callout lines of the "Controles básicos" guide, redrawn to a new controller.
# Placement measured on the game's screen (1920-wide capture scaled to 2000): controller canvas -> screen: x*0.779 + (550, 316); line canvas -> screen: x*0.702 + (455, 37).
# Every original component keeps its label bars (the vertical bars at the label edge); the connectors from those bars are redrawn to the new targets.
import numpy as np
from scipy import ndimage as nd
from PIL import Image, ImageDraw
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union

CS, CO = 0.779, (550, 316)
LS, LO = 0.702, (455, 37)
LW_ = 7.5; DOT = 9.6; DIA_W = 5.5; SS = 4
LEFT_BAR, RIGHT_BAR = 150, 1405


def c2l(x, y):   # controller canvas -> line canvas
    sx, sy = x * CS + CO[0], y * CS + CO[1]
    return (sx - LO[0]) / LS, (sy - LO[1]) / LS


def components(layer):
    B = layer > 100
    lab, n = nd.label(nd.binary_dilation(B, iterations=2))
    out = []
    for c in range(1, n + 1):
        m = (lab == c) & B
        if m.sum() < 200: out.append(('keep', m, None, None)); continue
        ys, xs = np.nonzero(m)
        left = xs.min() < 700
        if left: bar = m & (np.arange(m.shape[1])[None, :] <= LEFT_BAR); probe = LEFT_BAR + 12
        else: bar = m & (np.arange(m.shape[1])[None, :] >= RIGHT_BAR); probe = RIGHT_BAR - 12
        col = m[:, probe]; runs = []
        y = 0
        while y < len(col):
            if col[y]:
                y0 = y
                while y < len(col) and col[y]: y += 1
                runs.append((y0 + y - 1) / 2)
            y += 1
        merged = []
        for r in runs:
            if merged and r - merged[-1][-1] < 12: merged[-1].append(r)
            else: merged.append([r])
        runs = [sum(g) / len(g) for g in merged]
        by = np.nonzero(bar.any(1))[0]
        out.append(('callout', bar, dict(left=left, starts=runs, bar_top=by.min(), bar_bot=by.max(), x=(LEFT_BAR - 6 if left else RIGHT_BAR + 6)), m))
    return out


def semantic(info):
    t, b = info['bar_top'], info['bar_bot']
    if info['left']:
        return 'ZL' if t < 350 else 'L' if t < 460 else 'minus' if t < 560 else 'LS' if t < 690 else 'dpad'
    if t < 350: return 'ZR'
    if t < 460: return 'R'
    if t < 560: return 'plus'
    return 'RS' if t > 1150 else 'face'


def route(start_x, y0, target, left, diamond=None, hint=None):
    """orthogonal polyline from the bar to the target (the original's elbows); diamonds are met at a side vertex when the line comes in at their height"""
    sgn = 1 if left else -1
    if diamond:
        cx, cy, h = diamond
        if abs(y0 - cy) < h * 1.15:
            vx = cx - sgn * h; ax = vx - sgn * 26
            pts = [(start_x, y0), (ax, y0), (ax, cy), (vx, cy)] if abs(y0 - cy) > 1 else [(start_x, y0), (vx, cy)]
            return pts
        tx, ty = cx, (cy + h if y0 > cy else cy - h)
    else: tx, ty = target
    if hint and hint[0] == 'path':
        P = hint[1]
        return [(start_x, y0), (P[0][0], y0)] + list(P) + [(tx, P[-1][1]), (tx, ty)]
    if hint and hint[0] == 'over':
        xa, yh = hint[1], hint[2]
        return [(start_x, y0), (xa, y0), (xa, yh), (tx, yh), (tx, ty)]
    pts = [(start_x, y0), (tx, y0)]
    if abs(ty - y0) > 1: pts.append((tx, ty))
    return pts


def diamond_geom(cx, cy, h):
    p = Polygon([(cx, cy - h), (cx + h, cy), (cx, cy + h), (cx - h, cy)])
    p = p.buffer(-h * 0.18, join_style='mitre').buffer(h * 0.18, 32)   # rounded corners like the original
    return p.exterior.buffer(DIA_W / 2, 16)


def draw_layer(shape, comps, targets, clusters, hints={}):
    img = Image.new('L', (shape[1] * SS, shape[0] * SS), 0); d = ImageDraw.Draw(img)
    geoms = []
    keep = np.zeros(shape, bool)
    for kind, bar, info, m in comps:
        if kind == 'keep': keep |= bar; continue
        keep |= bar
        sem = semantic(info)
        if sem in clusters:
            cx, cy, r = clusters[sem]; lx, ly = c2l(cx, cy); h = r * CS / LS * 1.25
            geoms.append(diamond_geom(lx, ly, h))
            for y0 in info['starts']:
                if sem in hints and hints[sem][0] == 'around':
                    P = [c2l(x, y) for x, y in hints[sem][1]]
                    vx = lx + h if P[-1][0] > lx else lx - h
                    pts = [(info['x'], y0), (P[0][0], y0)] + P + [(vx, P[-1][1])]
                else: pts = route(info['x'], y0, None, info['left'], (lx, ly, h))
                geoms.append(LineString(pts).buffer(LW_ / 2, 8, cap_style='flat', join_style='mitre'))
        else:
            tx, ty = c2l(*targets[sem])
            hint = None
            if sem in hints:
                if hints[sem][0] == 'path': hint = ('path', [c2l(x, y) for x, y in hints[sem][1]])
                else: k, xa, yh = hints[sem]; hint = (k, c2l(xa, 0)[0], c2l(0, yh)[1])
            for y0 in info['starts']:
                geoms.append(LineString(route(info['x'], y0, (tx, ty), info['left'], hint=hint)).buffer(LW_ / 2, 8, cap_style='flat', join_style='mitre'))
            geoms.append(Point(tx, ty).buffer(DOT, 32))
    for g in [unary_union(geoms)]:
        for p in (g.geoms if hasattr(g, 'geoms') else [g]):
            d.polygon([(x * SS, y * SS) for x, y in p.exterior.coords], fill=255)
            for r in p.interiors: d.polygon([(x * SS, y * SS) for x, y in r.coords], fill=0)
    a = np.asarray(img.resize((shape[1], shape[0]), Image.LANCZOS)).copy()
    return np.maximum(a, np.where(keep, 255, 0).astype(np.uint8) * 0 + np.where(keep, orig_cache[0], 0)).astype(np.uint8)


orig_cache = [None]

def redraw(layer, targets, clusters, hints={}):
    orig_cache[0] = layer
    return draw_layer(layer.shape, components(layer), targets, clusters, hints)
