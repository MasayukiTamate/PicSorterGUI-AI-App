'''
PicSorterGUI 基本ユーティリティ
'''


def tkConvertWinSize(tateyokoList):
    '''
    最初にサイズの文字の場合も対応する予定
    '''
    res = ""
    dec = "","x","+","+"

    for l, d in zip(tateyokoList, dec):
        res = res + str(d)
        res = res + str(l)

    return res


def blend_color(c1, c2, ratio):
    """2つの色(Hex)を比率でブレンドする。"""
    try:
        if ratio <= 0: return c1
        if ratio >= 1: return c2

        def to_rgb(hex_code):
            return tuple(int(hex_code.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

        def to_hex(rgb):
            return '#{:02x}{:02x}{:02x}'.format(*rgb)

        r1, g1, b1 = to_rgb(c1)
        r2, g2, b2 = to_rgb(c2)

        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)

        return to_hex((r, g, b))
    except Exception:
        return c1
