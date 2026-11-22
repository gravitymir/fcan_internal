#!/usr/bin/env python3
"""Автотрассировка платы через kroute.

    route.py <плата.kicad_pcb> [секунд]

Плату делает build.py, этот скрипт её только разводит: kroute прокладывает
дорожки на копии платы и сохраняет новую медь в <плата>.routes.json рядом
с платой. В саму плату трассы вносит следующий запуск build.py (node.finish
накладывает их через `kroute apply`), поэтому генератор остаётся
единственным источником платы.

После перестановки деталей старые трассы к плате не подходят: запустить
route.py заново (node.finish об этом скажет - kroute apply --verify).

Правила: ширины и зазоры - классы цепей в .kicad_pro (lib/gen/netclass.py),
дифпары и прочее - kroute.toml рядом с платой, иначе общий lib/gen/kroute.toml.

kroute - один бинарник: KROUTE, иначе kroute из PATH, иначе соседний
репозиторий ../autorouter/target/release/kroute(.exe).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def kroute():
    exe = os.environ.get("KROUTE") or shutil.which("kroute")
    if not exe:
        repo = os.path.dirname(os.path.dirname(HERE))
        for name in ("kroute.exe", "kroute"):
            p = os.path.join(os.path.dirname(repo), "autorouter", "target", "release", name)
            if os.path.exists(p):
                exe = p
                break
    if not exe:
        sys.exit("kroute не найден (задайте KROUTE)")
    return exe


def routes_path(pcb):
    return os.path.splitext(pcb)[0] + ".routes.json"


def config(pcb):
    own = os.path.join(os.path.dirname(pcb), "kroute.toml")
    return own if os.path.exists(own) else os.path.join(HERE, "kroute.toml")


def apply(pcb):
    """Наложить сохранённые трассы на свежесобранную плату (вызывает node.finish)."""
    routes = routes_path(pcb)
    r = subprocess.run([kroute(), "apply", pcb, routes, "-o", pcb],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("kroute apply: %s" % (r.stdout.strip() or r.stderr.strip()))
    d = json.loads(r.stdout)
    return d.get("segments", 0), d.get("vias", 0)


def main():
    pcb = os.path.abspath(sys.argv[1])
    secs = sys.argv[2] if len(sys.argv) > 2 else "120"
    routes = routes_path(pcb)
    png = os.path.splitext(pcb)[0] + ".routes.png"
    with tempfile.TemporaryDirectory() as tmp:
        # копия платы с проектом и правилами: kroute и его DRC видят те же классы
        base = os.path.splitext(pcb)[0]
        for ext in (".kicad_pcb", ".kicad_pro", ".kicad_dru"):
            if os.path.exists(base + ext):
                shutil.copy(base + ext, os.path.join(tmp, "board" + ext))
        cmd = [kroute(), "route", os.path.join(tmp, "board.kicad_pcb"), "--strip", "--drc",
               "-c", config(pcb), "-t", secs, "-o", os.path.join(tmp, "routed.kicad_pcb"),
               "--emit", routes, "--png", png]
        print(" ".join(cmd))
        r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        sys.exit("kroute: %s" % (r.stdout.strip() or r.stderr.strip())[-1500:])
    if d.get("status") == "error":
        sys.exit("kroute: %s" % d.get("error"))
    st, drc = d["stats"], d.get("drc", {})
    print("%s: разведено %d цепей, не разведено %d, via %d, %.0f мм, %.1f с"
          % (d["status"], d["nets_routed"], d["nets_unrouted"], st["vias"], st["length_mm"], st["time_s"]))
    for u in d["unrouted"]:
        print("  НЕ РАЗВЕДЕНО %s: %s %s" % (u["net"], u["reason"], u.get("at")))
    for p in d.get("pairs", []):
        print("  пара %s/%s: %s, вместе %.1f мм, перекос %.2f мм"
              % (p["p"], p["n"], p["status"], p["coupled_mm"], p["skew_mm"]))
    for n in d["notes"]:
        print("  заметка:", n)
    print("  DRC: нарушений трассировки %s, несоединённых %s" % (drc.get("routing_violations"), drc.get("unconnected")))
    print("трассы ->", routes)
    print("картинка ->", png)
    if r.returncode != 0:
        sys.exit(r.returncode)


if __name__ == "__main__":
    main()
