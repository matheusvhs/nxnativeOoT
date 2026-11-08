# Controller art from the drawings beside this file (xbox.png, ps5.png: front views drawn from photos of the real controllers, on white) -> 1160x680 RGBA canvas in the game's grey palette
import os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as nd
IA = os.path.dirname(os.path.abspath(__file__))

def cutout(path):
    im = np.asarray(Image.open(path).convert('L')).astype(float)
    im = im[3:-3, 3:-3]                        # the viewer's frame edge
    bg = im > 232
    lab, n = nd.label(bg)
    edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
    outside = np.isin(lab, list(edge))
    inside = ~outside
    # soft edge: in a 2 px band around the shape, alpha from darkness (black outline on white)
    band = nd.binary_dilation(inside, iterations=2) & ~nd.binary_erosion(inside, iterations=1)
    a = np.where(inside, 255.0, 0.0)
    a[band] = np.clip((255 - im[band]) / (255 - 20) * 255, 0, 255) * np.where(inside[band], 1, 1)
    a[nd.binary_erosion(inside, iterations=1)] = 255
    g = np.where(band, np.minimum(im, 40), im)   # the edge band is outline: keep it black
    return g, a

def place(name, s, ox, oy):
    g, a = cutout(f'{IA}/{name}.png')
    h, w = g.shape
    G = Image.fromarray(g.clip(0, 255).astype(np.uint8)).resize((round(w * s), round(h * s)), Image.LANCZOS)
    A = Image.fromarray(a.clip(0, 255).astype(np.uint8)).resize((round(w * s), round(h * s)), Image.LANCZOS)
    cg = Image.new('L', (1160, 680), 0); ca = Image.new('L', (1160, 680), 0)
    # offsets refer to the uncropped capture (3 px frame removed)
    cg.paste(G, (round(ox + 3 * s), round(oy + 3 * s))); ca.paste(A, (round(ox + 3 * s), round(oy + 3 * s)))
    g2 = np.asarray(cg); a2 = np.asarray(ca)
    return np.dstack([g2, g2, g2, a2]).astype(np.uint8)


# measured on the AI drawings (capture pixels), then the placement on the 1160x680 canvas
SPEC = {
    'xbox': dict(file='xbox', s=0.838, ox=50.4, oy=50.3,
                 pts={'LS': (385, 230), 'RS': (760, 375), 'minus': (563, 228), 'plus': (700, 228),
                      'L': (360, 95), 'ZL': (440, 48), 'R': (904, 95), 'ZR': (824, 48)},
                 clusters={'dpad': (508, 385, 74), 'face': (878, 230, 92)}),
    'ps5': dict(s=1.0, ox=-2, oy=10,
                pts={'LS': (455, 352), 'RS': (708, 352), 'minus': (395, 152), 'plus': (770, 152),
                     'L': (322, 92), 'ZL': (375, 66), 'R': (842, 92), 'ZR': (789, 66)},
                clusters={'dpad': (331, 240, 75), 'face': (835, 242, 75)},
                # label order is Mover-se above the d-pad, but on the DualSense the stick is below the d-pad: Mover-se goes down left of the d-pad into
                # the stick from the side; the d-pad line runs under the controller, up between the left stick and the PS button, into the diamond's right corner
                hints={'LS': ('path', [(228, 362)]), 'dpad': ('around', [(540, 250)])}),
}


def art(brand):
    sp = SPEC[brand]; s, ox, oy = sp['s'], sp['ox'], sp['oy']
    T = lambda x, y: (x * s + ox, y * s + oy)
    pts = {k: T(*v) for k, v in sp['pts'].items()}
    cl = {k: (*T(x, y), r * s) for k, (x, y, r) in sp['clusters'].items()}
    return place(sp.get('file', brand), s, ox, oy), pts, cl, sp.get('hints', {})
