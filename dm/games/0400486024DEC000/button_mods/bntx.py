import struct
def brtis(d):
    assert d[:4] == b'BNTX'
    nx = 0x20; assert d[nx:nx+4] in (b'NX  ', b'Ounc')
    count = struct.unpack_from('<I', d, nx + 4)[0]
    arr = struct.unpack_from('<Q', d, nx + 8)[0]
    data_blk = struct.unpack_from('<Q', d, nx + 16)[0]
    out = []
    for i in range(count):
        p = struct.unpack_from('<Q', d, arr + 8 * i)[0]
        assert d[p:p+4] == b'BRTI'
        flags, dim, tile, swz, mips = struct.unpack_from('<BBHHH', d, p + 0x10)
        fmt, acc, w, h, dep, arrn, bh = struct.unpack_from('<IIiiiii', d, p + 0x1c)
        size, align, comp, ttype = struct.unpack_from('<IIII', d, p + 0x50)
        namep, parent, ptrs = struct.unpack_from('<QQQ', d, p + 0x60)
        L = struct.unpack_from('<H', d, namep)[0]; name = d[namep+2:namep+2+L].decode()
        mipoffs = struct.unpack_from('<%dQ' % mips, d, ptrs)
        out.append(dict(i=i, p=p, name=name, fmt=fmt, w=w, h=h, mips=mips, arr=arrn, bh=bh, size=size, tile=tile, comp=comp, ttype=ttype, mipoffs=mipoffs))
    return out
