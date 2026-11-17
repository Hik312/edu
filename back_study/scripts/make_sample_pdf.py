# -*- coding: utf-8 -*-
"""生成 check.js 用的最小样例 PDF（scripts/fixtures/sample.pdf）。

为什么需要它：知识库那组回归要验「论文走原件」和「手动选类型压过自动判据」，
必须有**一个真 PDF** 可传。而把 PDF 当二进制 fixture 提交不如现生成 ——
版本库里放个 1.7KB 的生成脚本，构造过程完全可见，也不会因为换工具重新编码
变成二进制噪音。

★ 正文刻意**避开论文版面标志词**（Abstract / Introduction / References / doi 等），
  这样 `_looks_like_paper` 对它**必须返回 False**。
  这一点是整份fixture 的价值所在：只有自动判据判不出论文，
  「用户手动选『论文』仍然生效」才是真被测到了。
  若用一份自带版面词的文件，自动判据本来就会判成论文，
  那条断言就是**恒真**的，测了个寂寞 —— 恒真的断言比没有断言更危险。

不依赖任何库（连reportlab 都不用），手写 PDF 语法足够应付三页纯文本。
正文用 ASCII（PDF 的 Helvetica 没有中文字形，中文会变乱码），
但刻意写成**技术资料**而非论文的结构。
用完可直接 `./.venv/Scripts/python.exe scripts/make_sample_pdf.py` 重生成。
"""
import os

#: 三页正文。技术笔记结构，刻意不含任何论文版面标志。
PAGES = [
    "Backend Notes\n\n"
    "Routing layer\n"
    "The router groups endpoints by feature and applies the auth dependency.\n\n"
    "Storage layer\n"
    "The store backend keeps card documents and progress rows.\n",
    "Scheduler\n"
    "Due cards are ordered by review priority, then by overdue days.\n\n"
    "Cache\n"
    "Mastery values are cached in redis with a protocol version field.\n",
    "Testing\n"
    "Run scripts/check.js before pushing. It covers API smoke tests.\n\n"
    "Deployment\n"
    "The frontend build output is served as static files by the backend.\n",
]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'fixtures', 'sample.pdf')


def build():
    objs = []                       # 按对象号顺序，1=Catalog 2=Pages，之后页/流成对
    kids = ['%d 0 R' % (3 + i * 2) for i in range(len(PAGES))]
    objs.append('<< /Type /Catalog /Pages 2 0 R >>')
    objs.append('<< /Type /Pages /Kids [%s] /Count %d >>' % (' '.join(kids), len(kids)))

    for i, text in enumerate(PAGES):
        pid = 3 + i * 2
        cpid = pid + 1
        objs.append(
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
            '/Contents %d 0 R /Resources << /Font << /F1 << /Type /Font '
            '/Subtype /Type1 /BaseFont /Helvetica >> >> >> >>' % cpid)
        # 文本流：每行一个 Tj，行距 16pt 从 760pt 往下走
        parts = ['BT /F1 12 Tf 40 760 Td 16 TL']
        for line in text.split('\n'):
            esc = (line.replace('\\', r'\\')
                       .replace('(', r'\(')
                       .replace(')', r'\)'))
            parts.append('(%s) Tj T*' % esc)
        parts.append('ET')
        stream = '\n'.join(parts).encode('latin-1')
        objs.append(('<< /Length %d >>\nstream\n' % len(stream)).encode()
                    + stream + b'\nendstream')

    out = b'%PDF-1.4\n'
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += ('%d 0 obj\n' % i).encode()
        out += o.encode('latin-1') if isinstance(o, str) else o
        out += b'\nendobj\n'
    xref = len(out)
    out += ('xref\n0 %d\n' % (len(objs) + 1)).encode() + b'0000000000 65535 f \n'
    for off in offsets:
        out += ('%010d 00000 n \n' % off).encode()
    out += ('trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF'
            % (len(objs) + 1, xref)).encode()
    return out


if __name__ == '__main__':
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    blob = build()
    with open(OUT, 'wb') as f:
        f.write(blob)
    print('wrote %s (%d bytes)' % (OUT, len(blob)))