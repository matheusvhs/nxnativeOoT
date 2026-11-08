# Builds the guide textures for one brand: Controller_<slot> (light), Controller_<slot>1 (dark), ControllerSh_<slot>1 (shadow), ControllerGuide_<slot>_0N (lines)
# from the originals in the BNTX. usage as a module: textures(d, entries, brand) -> {name: image array}; as a script: preview pngs.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageFilter
import tex, guide_lines, ia_art

SLOTS = ('Console', 'Grip', 'Pro')


def dark_of(light, orig_light, orig_dark):
    m = (orig_light[..., 3] == 255) & (orig_dark[..., 3] == 255)
    g = orig_light[m][:, 0].astype(float); X = np.c_[g, np.ones_like(g)]
    out = light.copy().astype(float)
    for ch in range(3):
        coef = np.linalg.lstsq(X, orig_dark[m][:, ch].astype(float), rcond=None)[0]
        out[..., ch] = light[..., 0] * coef[0] + coef[1]
    return out.round().clip(0, 255).astype(np.uint8)


def shadow_of(alpha, shape=(580, 440)):
    # left half of the silhouette, scaled 0.74 about the centre line (x 580 -> 439), y*0.74+38, blurred, peak 0.72
    sil = Image.fromarray(alpha).resize((round(1160 * 0.74), round(680 * 0.74)), Image.LANCZOS)
    canvas = Image.new('L', (shape[1] * 2, shape[0]), 0)
    canvas.paste(sil, (round(439 - 580 * 0.74), 38))
    canvas = canvas.filter(ImageFilter.GaussianBlur(16))
    a = np.asarray(canvas).astype(float) * 0.72
    return a[:, :shape[1]].round().clip(0, 255).astype(np.uint8)


def textures(d, t, brand):
    light, pts, clusters, hints = ia_art.art(brand)
    out = {}
    for s in SLOTS:
        out[f'Controller_{s}'] = light
        out[f'Controller_{s}1'] = dark_of(light, tex.read(d, t[f'Controller_{s}']), tex.read(d, t[f'Controller_{s}1']))
        out[f'ControllerSh_{s}1'] = shadow_of(light[..., 3])
        for j in range(5):
            n = f'ControllerGuide_{s}_0{j}'
            out[n] = guide_lines.redraw(tex.read(d, t[n]), pts, clusters, hints)
    return out
