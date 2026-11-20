#!/bin/sh
# Сборка платы и все проверки одной командой (Git Bash / Linux).
cd "$(dirname "$0")/.."
PY="${KICAD_PY:-/c/Program Files/KiCad/10.0/bin/python.exe}"
CLI="${KICAD_CLI:-/c/Program Files/KiCad/10.0/bin/kicad-cli.exe}"
F='assert|image handler'
NAME=Volt-Node
G=../../../lib/gen      # общие скрипты всех узлов
"$PY" gen/build.py . 2>&1 | grep -v -i -E "$F"
"$CLI" pcb drc --schematic-parity --severity-all -o drc.rpt "$NAME.kicad_pcb" >/dev/null 2>&1
grep -E "^\*\* Found" drc.rpt
grep -E "^\[" drc.rpt | sort | uniq -c
"$CLI" sch erc --severity-error -o erc.rpt "$NAME.kicad_sch" >/dev/null 2>&1
grep -E "^\*\* ERC|Found" erc.rpt | head -3
"$PY" $G/drc.py "$NAME.kicad_pcb" 2>&1 | grep -v -i -E "$F"
"$PY" $G/conn.py "$NAME.kicad_pcb" 2>&1 | grep -v -i -E "$F" | tail -3
"$PY" $G/crtyd.py "$NAME.kicad_pcb" 2>&1 | grep -v -i -E "$F"
"$PY" $G/silkchk.py "$NAME.kicad_pcb" 2>&1 | grep -v -i -E "$F"
# BOM и карта выводов - из той же платы, что сейчас собрана. Иначе BOM тихо
# отстаёт от схемы: именно так один раз и вышло.
"$PY" $G/outputs.py "$NAME.kicad_pcb" 2>&1 | grep -v -i -E "$F"
