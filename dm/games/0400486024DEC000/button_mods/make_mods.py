# Button mods for Zelda: Ocarina of Time (Switch 2): RomFS overlays with the button icons and the "Controles básicos" controller pictures of an Xbox pad (xbox/) and of a
# PlayStation pad (ps/), made from the player's own RomFS (the game's symbol font, its HUD and ocarina button textures, the controller guide's art and callout lines).
# The host picks one by the controller connected when the game starts (hle_fs.c, DM_BUTTON_MODS; DM_BUTTONS / DM_BOTOES = xbox | ps | nintendo forces it).
# Labels follow the button's position, as nxnative maps an Xbox or PlayStation pad (pad_apple.h): the right button is the game's A, so it shows B (Xbox) or the circle (PlayStation).
# Nothing of the game is in this folder: xbox.png and ps5.png are drawings of the real controllers, everything else is read from the RomFS at build time.
# usage: make_mods.py <RomFS image or folder> <out dir>   (needs numpy, Pillow, scipy, shapely, fonttools, astc-encoder-py; exit 2 without them)
import os, sys, subprocess, shutil, importlib.util, hashlib, json
HERE = os.path.dirname(os.path.abspath(__file__))
NEEDS = {'numpy': 'numpy', 'PIL': 'Pillow', 'scipy': 'scipy', 'shapely': 'shapely', 'fontTools': 'fonttools', 'astc_encoder': 'astc-encoder-py'}


def main():
    if len(sys.argv) != 3: sys.exit('usage: make_mods.py <RomFS image or folder> <out dir>')
    romfs, out = sys.argv[1], os.path.abspath(sys.argv[2])
    missing = [pkg for mod, pkg in NEEDS.items() if importlib.util.find_spec(mod) is None]
    if missing:
        print(f'button mods skipped: python packages missing ({" ".join(missing)}); pip install {" ".join(missing)} and build again'); sys.exit(2)
    st = os.stat(romfs)
    stamp = hashlib.sha256(json.dumps([os.path.abspath(romfs), st.st_size, st.st_mtime_ns] + [(n, hashlib.sha256(open(os.path.join(HERE, n), 'rb').read()).hexdigest())
                                       for n in sorted(os.listdir(HERE)) if n.endswith(('.py', '.png'))]).encode()).hexdigest()
    if os.path.isfile(os.path.join(out, 'stamp')) and open(os.path.join(out, 'stamp')).read() == stamp:
        print(f'button mods: {out}, reused (generator and RomFS unchanged)'); return
    sys.path.insert(0, HERE)
    import btnlib, bfotf
    btnlib.set_romfs(romfs)
    tmp = out + '.part'; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    font = os.path.join(tmp, 'clarimo.otf')   # the game's own UI font, for the shoulder labels (LB, RT, L1, R2): deleted below
    raw, _ = btnlib.get('Font2/Scalable/ClarimoUDPE-DemiBold.Nin_Ounce_NVN2.bfotf.zs')
    open(font, 'wb').write(bfotf.dec(raw))
    for layout, folder in (('xbox', 'xbox'), ('ps5', 'ps')):
        r = subprocess.run([sys.executable, os.path.join(HERE, 'make_mod.py'), layout, os.path.join(tmp, folder), romfs, font], capture_output=True, text=True)
        if r.returncode: sys.exit(f'button mod {folder} failed:\n{r.stdout}{r.stderr}')
        print(f'button mod {folder}: ' + ', '.join(l.split()[1].split('/')[-1] for l in r.stdout.splitlines() if l.startswith('wrote ')))
    os.remove(font)
    open(os.path.join(tmp, 'stamp'), 'w').write(stamp)
    shutil.rmtree(out, ignore_errors=True); os.replace(tmp, out)
    print(f'button mods: {out} (xbox, ps)')


if __name__ == '__main__':
    main()
