import struct
KEY = 0xa6018502; MAGIC = 0x7f9a0218
def dec(d):
    n = len(d) // 4 * 4
    w = struct.unpack('>%dI' % (n // 4), d[:n])
    assert w[0] ^ KEY == MAGIC
    out = struct.pack('>%dI' % (len(w) - 2), *[x ^ KEY for x in w[2:]])
    size = w[1] ^ KEY
    return out[:size]
def enc(font):
    pad = (-len(font)) % 4; f = font + b'\0' * pad
    w = struct.unpack('>%dI' % (len(f) // 4), f)
    return struct.pack('>%dI' % (len(w) + 2), MAGIC ^ KEY, len(font) ^ KEY, *[x ^ KEY for x in w])
def size_of(d):
    return struct.unpack('>I', d[4:8])[0] ^ KEY
