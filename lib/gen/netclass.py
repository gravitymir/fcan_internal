"""Классы цепей платы узла: ширина дорожки и зазор, мм.

node.finish пишет их в .kicad_pro. Оттуда их берут KiCad (зазор проверяет
DRC, ширину подставляет интерактивный роутер) и kroute (route.py).
Остальные цепи - класс Default, 0.2/0.2.

Питание шины и USB идёт через плату транзитом (ток всех узлов ниже по
гирлянде), поэтому широко. Земля и 3.3 В уже: им заходить на выводы LQFP
с шагом 0.5. Щупы - до 43 В, зазор побольше.
"""
import json

CLASSES = {
    "bus": (0.40, 0.20, ["+5V", "BUS5V", "VBUS"]),
    "pwr": (0.30, 0.20, ["GND", "+3V3"]),
    "can": (0.25, 0.20, ["CANH", "CANL"]),
    "hv": (0.25, 0.30, ["VIN+", "VIN-"]),
}


def write_project(pro):
    """Вписать классы и привязку цепей в net_settings файла .kicad_pro."""
    with open(pro, encoding="utf-8") as f:
        d = json.load(f)
    ns = d.setdefault("net_settings", {})
    classes = ns.get("classes") or []
    default = next((c for c in classes if c.get("name") == "Default"), None)
    if default is None:
        raise RuntimeError("в %s нет класса Default" % pro)
    out = [default]
    for i, (name, (w, c, _)) in enumerate(CLASSES.items()):
        cl = dict(default)
        cl.update(name=name, track_width=w, clearance=c, priority=i)
        out.append(cl)
    ns["classes"] = out
    ns["netclass_patterns"] = [{"netclass": name, "pattern": n}
                               for name, (_, _, nets) in CLASSES.items() for n in nets]
    ns["netclass_assignments"] = None
    with open(pro, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")
