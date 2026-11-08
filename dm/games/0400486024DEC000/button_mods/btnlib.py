# RomFS access for the button mods: an indexed image (dm/tools/romfs_image.py) or an extracted folder; Tears of the Kingdom-style zstd dictionaries (Pack/ZsDic.pack.zs)
import os, struct, sys
try: from compression import zstd
except ImportError: from backports import zstd   # Python < 3.14
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../tools'))
import romfs_image
ROMFS = None; _idx = None; _dicts = None

def set_romfs(path):
    global ROMFS, _idx, _dicts
    ROMFS = path; _dicts = None
    _idx = None if os.path.isdir(path) else {k.lstrip('/'): v for k, v in romfs_image.read_index(path).items()}

def raw(p):
    if _idx is None:
        with open(os.path.join(ROMFS, p), 'rb') as f: return f.read()
    isdir, off, size = _idx[p]
    with open(ROMFS, 'rb') as f: f.seek(off); return f.read(size)

def sarc(d):
    hl, bom, size, doff = struct.unpack_from('<HHII', d, 4)
    n = struct.unpack_from('<H', d, hl + 6)[0]
    names = hl + 12 + 16 * n + 8
    out = []
    for i in range(n):
        h, attr, s, e = struct.unpack_from('<IIII', d, hl + 12 + 16 * i)
        o = names + (attr & 0xffffff) * 4; z = d.find(b'\0', o)
        out.append((d[o:z].decode(), doff + s, doff + e))
    return out

def dicts():
    global _dicts
    if _dicts is None:
        d = zstd.decompress(raw('Pack/ZsDic.pack.zs'))
        _dicts = {struct.unpack_from('<I', d, s + 4)[0]: zstd.ZstdDict(d[s:e]) for nm, s, e in sarc(d) if d[s:s + 4] == bytes.fromhex('37a430ec')}
    return _dicts

def dict_id(d):
    fhd = d[4]; n, o = (0, 1, 2, 4)[fhd & 3], 6 - (fhd >> 5 & 1)
    return int.from_bytes(d[o:o + n], 'little')

def unzs(d):
    did = dict_id(d)
    return zstd.decompress(d, zstd_dict=dicts()[did]) if did else zstd.decompress(d)

def zs(data, did, level=19):
    return zstd.compress(data, level=level, zstd_dict=dicts()[did]) if did else zstd.compress(data, level=level)

def get(p):
    d = raw(p)
    return (unzs(d), dict_id(d)) if p.endswith('.zs') else (d, 0)
