"""Общая концовка build.py любого узла: проверка ядра, схема, цепи платы,
проектная библиотека посадочных мест, запись платы."""
import os

import pcbnew

import core
import pcbhelp

FPLIB = "fcan"


def finish(b, d, out, name, fill=False):
    core.check(d)

    os.makedirs(out, exist_ok=True)
    for pt in d.parts:
        if ":" in pt.footprint:
            pt.footprint = FPLIB + ":" + pt.footprint.split(":", 1)[1]
    d.write_sch(os.path.join(out, name + ".kicad_sch"))
    for p in d.parts:
        if p.ref.startswith("#"):
            continue
        for pn, net in p.nets.items():
            try:
                b.setnet(p.ref, pn, net)
            except KeyError:
                pass

    # Проектная библиотека: плата не зависит от того, какой KiCad стоит рядом.
    libdir = os.path.join(out, FPLIB + ".pretty")
    os.makedirs(libdir, exist_ok=True)
    saved = set()
    for ref, fp in b.fps.items():
        nm = str(fp.GetFPID().GetLibItemName())
        if nm not in saved:
            c = None
            for args in ((False,), (False, True), ()):
                try:
                    c = fp.Duplicate(*args)
                    break
                except TypeError:
                    continue
            if c is None:
                raise RuntimeError("не удалось скопировать футпринт %s" % nm)
            if not hasattr(c, "IsFlipped"):      # KiCad 10 отдаёт BOARD_ITEM
                c = pcbnew.Cast_to_FOOTPRINT(c)
            if c.IsFlipped():
                c.Flip(c.GetPosition(), False)
            c.SetPosition(pcbnew.VECTOR2I(0, 0))
            c.SetOrientationDegrees(0)
            c.SetReference("REF**")
            c.SetValue(nm)
            pcbhelp.footprint_save(libdir, c)
            saved.add(nm)
        fp.SetFPID(pcbnew.LIB_ID(FPLIB, nm))
    print("библиотека проекта: %d футпринтов" % len(saved))

    with open(os.path.join(out, "fp-lib-table"), "w") as t:
        t.write('(fp_lib_table\n  (version 7)\n'
                '  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.pretty")(options "")(descr "Footprints used by this board"))\n)\n'
                % (FPLIB, FPLIB))

    b.finish(os.path.join(out, name + ".kicad_pcb"), fill=fill)
    print("OK ->", out)
