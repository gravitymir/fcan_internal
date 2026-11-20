"""Проектная библиотека символов: то, чего нет в стандартных библиотеках KiCad.

Символ не рисуется руками. Берётся готовый из библиотеки KiCad - с нужной
графикой, геометрией и сеткой выводов, - и у него правятся имя, свойства и
только те выводы, которыми части отличаются. Так проектный символ по виду
совпадает с остальными, а в правке видно ровно суть различия.

Зачем вообще. Футпринты проект уже складывает рядом с платой, в fcan.pretty;
здесь то же самое для символов - fcan.kicad_sym плюс sym-lib-table, чтобы
схема открывалась в KiCad без системных библиотек и чтобы имя символа не
врало про то, какая это микросхема.
"""
import os
import re

import kigen
from kigen import block, raw_symbol

HEADER = ('(kicad_symbol_lib\n'
          '  (version 20251024)\n'
          '  (generator "fcan-symlib")\n'
          '  (generator_version "10.0")\n')


def _flat(libid):
    """Имя-источник графики и её тело: у (extends ...) это тело родителя."""
    lib, name = libid.split(":", 1)
    blk = raw_symbol(lib, name)
    ext = re.search(r'\(extends "([^"]+)"\)', blk)
    if not ext:
        return name, blk
    return ext.group(1), raw_symbol(lib, ext.group(1))


def _set_prop(text, key, value):
    """Переписать значение свойства, если оно в символе есть."""
    m = re.search(r'\(property "%s" "((?:[^"\\]|\\.)*)"' % re.escape(key), text)
    if not m:
        return text
    return text[: m.start(1)] + value + text[m.end(1) :]


def _patch_pin(text, number, name=None, etype=None):
    """Переименовать вывод и/или сменить его электрический тип.

    Тип важен не меньше имени: вывод типа no_connect с подключённой цепью ERC
    считает ошибкой, а BYP у AP2210 цепь как раз имеет.
    """
    for m in re.finditer(r"\(pin (\w+) (\w+)", text):
        pb = block(text, m.start())
        if not re.search(r'\(number "%s"' % re.escape(number), pb):
            continue
        nb = pb
        if etype:
            nb = re.sub(r"\(pin \w+ (\w+)", r"(pin %s \1" % etype, nb, count=1)
        if name is not None:
            nb = re.sub(r'\(name "[^"]*"', '(name "%s"' % name, nb, count=1)
        return text[: m.start()] + nb + text[m.start() + len(pb) :]
    raise KeyError("вывод %s в символе не найден" % number)


def build(libdir, libname, items):
    """Собрать <libdir>/<libname>.kicad_sym и подключить его к kigen.

    items: список словарей
        name  - имя символа в проектной библиотеке
        from  - откуда взять графику, "Библиотека:Символ"
        pins  - {номер: (имя, электрический тип)}, что поправить
        props - {свойство: значение}
    """
    out = []
    for it in items:
        src, text = _flat(it["from"])
        text = re.sub(r'\(symbol "%s' % re.escape(src), '(symbol "%s' % it["name"], text)
        for num, (pname, etype) in it.get("pins", {}).items():
            text = _patch_pin(text, num, pname, etype)
        for k, v in it.get("props", {}).items():
            text = _set_prop(text, k, v)
        out.append("  " + text.replace("\n", "\n  "))

    if not os.path.isdir(libdir):
        os.makedirs(libdir)
    path = os.path.join(libdir, libname + ".kicad_sym")
    with open(path, "w", encoding="utf-8") as f:
        f.write(HEADER + "\n".join(out) + "\n)\n")

    with open(os.path.join(libdir, "sym-lib-table"), "w", encoding="utf-8") as f:
        f.write('(sym_lib_table\n  (version 7)\n'
                '  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.kicad_sym")'
                '(options "")(descr "Symbols used by this board"))\n)\n' % (libname, libname))

    if libdir not in kigen.EXTRA_SYMDIRS:
        kigen.EXTRA_SYMDIRS.insert(0, libdir)
    kigen._libcache.pop(libname, None)
    return path
