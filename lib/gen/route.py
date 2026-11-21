#!/usr/bin/env python3
"""Автотрассировка платы через Freerouting.

    route.py <плата.kicad_pcb> [проходов]

Плату делает build.py, этот скрипт её только разводит: выгружает в Specctra
DSN, гоняет Freerouting и кладёт сессию <плата>.ses рядом с платой. Дорожки
в саму плату вносит следующий запуск build.py (node.finish подхватывает .ses),
поэтому генератор остаётся единственным источником платы.

После перестановки деталей старая сессия к плате не подходит: запустить
route.py заново.

Freerouting - .jar под Java: FREEROUTING_JAR (иначе
~/tools/freerouting/freerouting-*.jar) и JAVA (иначе java из ~/tools/jre/*/bin
или из PATH). Консольная сборка freerouting-cli.exe 2.5.0 не годится: падает на
первом проходе (ошибка GraalVM при сериализации ComponentOutline) и висит
без нагрузки, не сохраняя результат.
"""
import os
import glob
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicadenv

kicadenv.quiet()
import pcbnew

from netclass import CLASSES   # те же классы node.finish пишет в .kicad_pro


def tool():
    home = os.path.expanduser("~")
    jar = os.environ.get("FREEROUTING_JAR") or next(iter(sorted(glob.glob(
        os.path.join(home, "tools", "freerouting", "freerouting-*.jar")), reverse=True)), None)
    if not jar or not os.path.exists(jar):
        sys.exit("Freerouting .jar не найден (задайте FREEROUTING_JAR)")
    java = os.environ.get("JAVA") or next(iter(sorted(glob.glob(
        os.path.join(home, "tools", "jre", "*", "bin", "java.exe")), reverse=True)), None)         or shutil.which("java")
    if not java:
        sys.exit("Java не найдена (задайте JAVA)")
    return [java, "-jar", jar, "--gui.enabled=false"]


def _q(n):
    return '"%s"' % n if re.search(r'[\s()"-]', n) else n


def patch_classes(dsn):
    """Разнести цепи по классам в секции network файла DSN."""
    s = open(dsn, encoding="utf-8").read()
    m = re.search(r"\(class kicad_default (.*?)\(circuit", s, re.S)
    if not m:
        raise RuntimeError("в DSN нет класса kicad_default")
    names = re.findall(r'"[^"]*"|[^\s"]+', m.group(1))
    names = [n.strip('"') for n in names]
    taken = {n for _, _, nets in CLASSES.values() for n in nets}
    rest = [n for n in names if n not in taken]
    head = "(class kicad_default %s\n      " % " ".join(_q(n) for n in rest)
    s = s[:m.start()] + head + s[m.end() - len("(circuit"):]
    via = re.search(r'\(use_via "([^"]+)"\)', s).group(1)
    extra = ""
    for cname, (w, c, nets) in CLASSES.items():
        nets = [n for n in nets if n in names]
        if not nets:
            continue
        extra += ('    (class %s %s\n      (circuit\n        (use_via "%s")\n      )\n'
                  '      (rule\n        (width %d)\n        (clearance %d)\n      )\n    )\n'
                  % (cname, " ".join(_q(n) for n in nets), via,
                     round(w * 1000), round(c * 1000)))
    i = s.index("(class kicad_default")
    s = s[:i] + extra.lstrip() + "    " + s[i:]
    open(dsn, "w", encoding="utf-8").write(s)


def main():
    pcb = os.path.abspath(sys.argv[1])
    passes = sys.argv[2] if len(sys.argv) > 2 else "40"
    base = os.path.splitext(pcb)[0]
    dsn, ses = base + ".dsn", base + ".ses"

    b = pcbnew.LoadBoard(pcb)
    for t in list(b.GetTracks()):
        b.Remove(t)
    for z in list(b.Zones()):
        b.Remove(z)
    if not pcbnew.ExportSpecctraDSN(b, dsn):
        sys.exit("не удалось выгрузить DSN")
    patch_classes(dsn)

    # Трассировщик недетерминирован: бывает, что оставляет пару соединений.
    # Тогда - ещё попытка, до трёх.
    cmd = tool() + ["-de", dsn, "-do", ses, "-mp", passes]
    print(" ".join(cmd))
    for attempt in range(1, 4):
        if os.path.exists(ses):
            os.remove(ses)
        r = subprocess.run(cmd, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=1800)
        log = r.stdout + r.stderr
        m = re.findall(r"Auto-routing stage completed.*?\((\d+) unrouted and (\d+) violations", log)
        if "Exception" in log or not m:
            print(log[-1500:])
            sys.exit("Freerouting упал")
        left, viol = map(int, m[-1])
        print("попытка %d: не разведено %d, замечаний %d" % (attempt, left, viol))
        if left == 0:
            break
    os.remove(dsn)
    if not os.path.exists(ses):
        sys.exit("Freerouting не сохранил сессию")
    print("сессия ->", ses)


if __name__ == "__main__":
    main()
