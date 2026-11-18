#!/usr/bin/env python3
"""Генератор проекта KiCad: Volt-Node - узел внутренней шины CAN FD, вольтметр.

Измерительный тракт повторяет volt_probe без изменений: щупы V+ / V- через
470 кОм (0805, 150 В) на дифференциальный усилитель LMV358 (половинка A),
коэффициент 18k/470k = 0.0383, выход смещён на опору 1.65 В (делитель 10k/10k
и буфер на половинке B). Диапазон +-43 В, пересчёт V = (OUT - 1.65) * 26.11.

Новое против volt_probe: АЦП теперь на плате. Аналог наружу не выходит, по
кабелю идёт только дифференциальный CAN. Опора 1.65 В заведена на второй канал
АЦП - её можно мерить, а не считать идеальной.

Стандарт шины - docs/BUS.md:
  JST PH S4B-PH-K-S, две колодки параллельно (гирлянда), 1 +5V / 2 CANH /
  3 CANL / 4 GND; 5 В в кабеле, LDO 3.3 В на плате; терминатор 120 Ом на
  разомкнутой перемычке; CAN FD BRS 250 кбит/с + 1 Мбит/с.

Выводы, занятые ПЗУ-загрузчиком и потому неприкасаемые:
  PD0/PD1   - FDCAN1 RX/TX, та же пара, что у загрузчика (AN2606, ID 0x92).
  PA11/PA12 - USB DFU. ВНИМАНИЕ: на всех корпусах STM32G0 это ремап ног 33/34,
              которые по умолчанию отдают PA9/PA10. Прошивка обязана выставить
              SYSCFG_CFGR1 PA11_RMP/PA12_RMP, иначе USB не поднимется.
  PA14      - SWCLK и BOOT0 одновременно (так устроен G0). Кнопка BOOT тянет
              его вверх, резистор 10к - вниз. Чтобы кнопка заработала, в опциях
              надо сбросить nBOOT_SEL: с завода BOOT0 берётся из бита, а не с
              ноги. Чистый кристалл это прошить не мешает - при пустой флеш-
              памяти G0 уходит в загрузчик сам.
  PF2       - NRST.

Сейчас сделаны схема и размещение. Разводки нет: цепи видны связями.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicadenv
import pcbnew
import pcbhelp
from pcbhelp import Builder, mm, tomm, V, FPDIR
import kigen

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
NAME = "Volt-Node"
X0, X1, Y0, Y1 = 100.0, 148.0, 100.0, 142.0
BW, BH = X1 - X0, Y1 - Y0
CXB, CYB = (X0 + X1) / 2, (Y0 + Y1) / 2
FCU, BCU = pcbnew.F_Cu, pcbnew.B_Cu
W, WP = 0.25, 0.4

C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
C0603 = ("Capacitor_SMD", "C_0603_1608Metric")
C0805 = ("Capacitor_SMD", "C_0805_2012Metric")
R0402 = ("Resistor_SMD", "R_0402_1005Metric")
R0603 = ("Resistor_SMD", "R_0603_1608Metric")
R0805 = ("Resistor_SMD", "R_0805_2012Metric")
LQFP48 = ("Package_QFP", "LQFP-48_7x7mm_P0.5mm")
SO8 = ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm")
SOT23 = ("Package_TO_SOT_SMD", "SOT-23")
SOT235 = ("Package_TO_SOT_SMD", "SOT-23-5")
SOT238 = ("Package_TO_SOT_SMD", "SOT-23-8")
XTAL = ("Crystal", "Crystal_SMD_5032-2Pin_5.0x3.2mm")
SMA = ("Diode_SMD", "D_SMA")
LED0805 = ("LED_SMD", "LED_0805_2012Metric")
SWFP = ("Button_Switch_SMD", "SW_SPST_SKQG_WithoutStem")
USBCFP = ("Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12")
PHFP = ("Connector_JST", "JST_PH_S4B-PH-K_1x04_P2.00mm_Horizontal")
JPFP = ("Jumper", "SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm")
HDRLIB = "Connector_PinHeader_2.54mm"

USBC_LIBID = "Connector:USB_C_Receptacle_USB2.0_16P"
SHIELD = [p.number for p in kigen.get_symbol(USBC_LIBID).pins if p.name == "SHIELD"][0]

b = Builder(layers=2)

# ------------------------------------------------------------ размещение
# Первый проход, расставлено по смыслу: аналог сверху, цифра снизу, шина справа.
# Разводки ещё нет, координаты будут уточняться.

# --- аналоговый блок: верхняя полоса, подальше от микроконтроллера
b.place("J4", HDRLIB, "PinHeader_1x02_P2.54mm_Vertical", 104.5, 104.0, 0, value="PROBE")
b.place("R1", R0805[0], R0805[1], 110.5, 103.0, 0, value="470k")
b.place("R2", R0805[0], R0805[1], 110.5, 106.5, 0, value="470k")
b.place("D1", SOT23[0], SOT23[1], 115.5, 103.0, 0, value="BAT54S")
b.place("D2", SOT23[0], SOT23[1], 115.5, 107.5, 0, value="BAT54S")
b.place("U4", SO8[0], SO8[1], 122.5, 105.0, 0, value="LMV358")
b.place("C3", C0402[0], C0402[1], 122.5, 109.0, 0, value="100nF")
b.place("R3", R0402[0], R0402[1], 128.5, 102.5, 0, value="18k")
b.place("R4", R0402[0], R0402[1], 128.5, 104.0, 0, value="18k")
b.place("R5", R0402[0], R0402[1], 128.5, 105.5, 0, value="10k")
b.place("R6", R0402[0], R0402[1], 128.5, 107.0, 0, value="10k")
b.place("C2", C0402[0], C0402[1], 131.5, 107.0, 0, value="100nF")
b.place("R7", R0402[0], R0402[1], 132.0, 102.5, 0, value="220R")
b.place("C1", C0402[0], C0402[1], 132.0, 104.0, 0, value="470pF")

# --- микроконтроллер, кварц, отладка
b.place("U1", LQFP48[0], LQFP48[1], 117.0, 119.0, 0, value="STM32G0B1CBT6")
b.place("Y1", XTAL[0], XTAL[1], 105.0, 114.5, 0, value="8MHz")
b.place("C4", C0402[0], C0402[1], 109.5, 112.5, 0, value="33pF")
b.place("C5", C0402[0], C0402[1], 109.5, 116.0, 0, value="33pF")

b.place("D5", LED0805[0], LED0805[1], 127.0, 112.5, 0, value="LED")
b.place("R12", R0402[0], R0402[1], 130.5, 112.5, 0, value="1k")
b.place("C8", C0402[0], C0402[1], 113.0, 126.5, 0, value="100nF")
b.place("C9", C0805[0], C0805[1], 116.5, 126.5, 0, value="4.7uF")
b.place("C10", C0402[0], C0402[1], 120.5, 126.5, 0, value="100nF")
b.place("C11", C0402[0], C0402[1], 123.5, 126.5, 0, value="1uF")

# --- шина: трансивер, терминатор, две колодки гирляндой у правого края
b.place("U2", SOT238[0], SOT238[1], 127.0, 118.0, 0, value="TCAN332G")
b.place("C6", C0402[0], C0402[1], 127.0, 121.5, 0, value="100nF")
b.place("C7", C0603[0], C0603[1], 130.0, 121.5, 0, value="1uF")
b.place("R8", R0603[0], R0603[1], 133.5, 116.0, 90, value="120R")
b.place("JP1", JPFP[0], JPFP[1], 133.5, 120.0, 90, value="TERM")
b.place("J1", PHFP[0], PHFP[1], 144.5, 110.0, 180, value="BUS")
b.place("J2", PHFP[0], PHFP[1], 144.5, 122.0, 180, value="BUS")

# --- USB-C, кнопки
b.place("J3", USBCFP[0], USBCFP[1], 106.0, 135.5, 90, value="USB-C")
# SWD вдоль нижнего края, подальше от USB-C
b.place("J5", HDRLIB, "PinHeader_1x04_P2.54mm_Vertical", 119.0, 138.5, 90, value="SWD")
b.place("R9", R0402[0], R0402[1], 104.0, 123.5, 0, value="5.1k")
b.place("R10", R0402[0], R0402[1], 104.0, 125.5, 0, value="5.1k")
b.place("SW1", SWFP[0], SWFP[1], 117.0, 131.5, 0, value="RESET")
b.place("SW2", SWFP[0], SWFP[1], 127.0, 131.5, 0, value="BOOT")
b.place("C14", C0402[0], C0402[1], 133.0, 126.5, 0, value="100nF")
b.place("R11", R0402[0], R0402[1], 131.0, 126.5, 0, value="10k")

# --- питание: диодное ИЛИ 5 В и LDO
b.place("U3", SOT235[0], SOT235[1], 140.0, 134.5, 0, value="AP2112K-3.3")
b.place("C12", C0603[0], C0603[1], 144.5, 134.5, 0, value="1uF")
b.place("C13", C0402[0], C0402[1], 140.0, 138.5, 0, value="1uF")
b.place("D3", SMA[0], SMA[1], 137.0, 129.5, 0, value="SS34")
b.place("D4", SMA[0], SMA[1], 105.0, 120.0, 0, value="SS34")

b.edge_rect(CXB, CYB, BW, BH, 1.5)

# ------------------------------------------------------------ схема
d = kigen.Design(NAME, "Volt-Node: вольтметр +-43 В, узел внутренней шины CAN FD")
d.prepare()

# --- микроконтроллер. Номера выводов - LQFP-48, сверено с символом KiCad.
d.add(kigen.Part("U1", "MCU_ST_STM32G0:STM32G0B1CBTx", "STM32G0B1CBT6",
                 "%s:%s" % LQFP48,
                 {"1": "LED_K",        # PC13 - светодиод состояния
                  "4": "+3V3",         # VBAT
                  "5": "+3V3",         # VREF+
                  "6": "+3V3",         # VDD
                  "7": "GND",          # VSS
                  "8": "OSC_IN",       # PF0
                  "9": "OSC_OUT",      # PF1
                  "10": "NRST",        # PF2
                  "11": "VOUT",        # PA0 - АЦП: измерение
                  "12": "VREF",        # PA1 - АЦП: контроль опоры 1.65 В
                  "33": "USB_DM",      # PA9/PA11 - нужен ремап
                  "34": "USB_DP",      # PA10/PA12 - нужен ремап
                  "35": "SWDIO",       # PA13
                  "36": "SWCLK",       # PA14, он же BOOT0
                  "38": "CAN_RX",      # PD0
                  "39": "CAN_TX"},     # PD1
                 at=(160, 120)))
d.add(kigen.Part("Y1", "Device:Crystal", "8MHz", "%s:%s" % XTAL,
                 {"1": "OSC_IN", "2": "OSC_OUT"}, at=(80, 150)))
d.add(kigen.Part("C4", "Device:C", "33pF", "%s:%s" % C0402,
                 {"1": "OSC_IN", "2": "GND"}, at=(60, 165)))
d.add(kigen.Part("C5", "Device:C", "33pF", "%s:%s" % C0402,
                 {"1": "OSC_OUT", "2": "GND"}, at=(100, 165)))
d.add(kigen.Part("C8", "Device:C", "100nF", "%s:%s" % C0402,
                 {"1": "+3V3", "2": "GND"}, at=(240, 155)))
d.add(kigen.Part("C9", "Device:C", "4.7uF", "%s:%s" % C0805,
                 {"1": "+3V3", "2": "GND"}, at=(262, 155)))
d.add(kigen.Part("C10", "Device:C", "100nF", "%s:%s" % C0402,
                 {"1": "+3V3", "2": "GND"}, at=(284, 155)))
d.add(kigen.Part("C11", "Device:C", "1uF", "%s:%s" % C0402,
                 {"1": "+3V3", "2": "GND"}, at=(306, 155)))

# --- сброс и загрузка
d.add(kigen.Part("SW1", "Switch:SW_Push", "RESET", "%s:%s" % SWFP,
                 {"1": "NRST", "2": "GND"}, at=(60, 205)))
d.add(kigen.Part("C14", "Device:C", "100nF", "%s:%s" % C0402,
                 {"1": "NRST", "2": "GND"}, at=(88, 205)))
d.add(kigen.Part("SW2", "Switch:SW_Push", "BOOT", "%s:%s" % SWFP,
                 {"1": "SWCLK", "2": "+3V3"}, at=(122, 205)))
d.add(kigen.Part("R11", "Device:R", "10k", "%s:%s" % R0402,
                 {"1": "SWCLK", "2": "GND"}, at=(150, 205)))
# SWD: нужен не для прошивки (её делает ПЗУ-загрузчик), а для отладки под
# отладчиком. Без него SWDIO висел бы в воздухе - ERC это и поймал.
d.add(kigen.Part("J5", "Connector_Generic:Conn_01x04", "SWD",
                 "%s:PinHeader_1x04_P2.54mm_Vertical" % HDRLIB,
                 {"1": "+3V3", "2": "SWDIO", "3": "SWCLK", "4": "GND"},
                 at=(190, 205)))

# --- светодиод состояния
d.add(kigen.Part("R12", "Device:R", "1k", "%s:%s" % R0402,
                 {"1": "+3V3", "2": "LED_A"}, at=(330, 115)))
d.add(kigen.Part("D5", "Device:LED", "LED", "%s:%s" % LED0805,
                 {"1": "LED_K", "2": "LED_A"}, at=(330, 140)))

# --- шина CAN FD
d.add(kigen.Part("U2", "Interface_CAN_LIN:TCAN332", "TCAN332G", "%s:%s" % SOT238,
                 {"1": "CAN_TX", "2": "GND", "3": "+3V3", "4": "CAN_RX",
                  "6": "CANL", "7": "CANH"}, at=(400, 120)))
d.add(kigen.Part("C6", "Device:C", "100nF", "%s:%s" % C0402,
                 {"1": "+3V3", "2": "GND"}, at=(375, 155)))
d.add(kigen.Part("C7", "Device:C", "1uF", "%s:%s" % C0603,
                 {"1": "+3V3", "2": "GND"}, at=(398, 155)))
# терминатор: запаивается только на двух крайних узлах гирлянды
d.add(kigen.Part("R8", "Device:R", "120R", "%s:%s" % R0603,
                 {"1": "CANH", "2": "TERM"}, at=(455, 100)))
d.add(kigen.Part("JP1", "Jumper:SolderJumper_2_Open", "TERM", "%s:%s" % JPFP,
                 {"1": "TERM", "2": "CANL"}, at=(455, 125)))
# две колодки параллельно: кабель входит в одну, выходит из другой
for _r, _y in (("J1", 75), ("J2", 165)):
    d.add(kigen.Part(_r, "Connector_Generic:Conn_01x04", "BUS", "%s:%s" % PHFP,
                     {"1": "BUS5V", "2": "CANH", "3": "CANL", "4": "GND"},
                     at=(510, _y)))

# --- питание: 5 В из шины и из USB через диодное ИЛИ, дальше LDO
d.add(kigen.Part("D3", "Device:D_Schottky", "SS34", "%s:%s" % SMA,
                 {"2": "BUS5V", "1": "+5V"}, at=(400, 215)))
d.add(kigen.Part("D4", "Device:D_Schottky", "SS34", "%s:%s" % SMA,
                 {"2": "VBUS", "1": "+5V"}, at=(400, 240)))
d.add(kigen.Part("U3", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", "%s:%s" % SOT235,
                 {"1": "+5V", "2": "GND", "3": "+5V", "5": "+3V3"}, at=(455, 225)))
d.add(kigen.Part("C12", "Device:C", "1uF", "%s:%s" % C0603,
                 {"1": "+5V", "2": "GND"}, at=(428, 258)))
d.add(kigen.Part("C13", "Device:C", "1uF", "%s:%s" % C0402,
                 {"1": "+3V3", "2": "GND"}, at=(495, 258)))

# --- USB-C: питание и прошивка по DFU
d.add(kigen.Part("J3", USBC_LIBID, "USB-C", "%s:%s" % USBCFP,
                 {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND",
                  "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
                  "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP",
                  "A7": "USB_DM", "B7": "USB_DM", SHIELD: "GND"}, at=(60, 255)))
d.add(kigen.Part("R9", "Device:R", "5.1k", "%s:%s" % R0402,
                 {"1": "CC1", "2": "GND"}, at=(125, 258)))
d.add(kigen.Part("R10", "Device:R", "5.1k", "%s:%s" % R0402,
                 {"1": "CC2", "2": "GND"}, at=(150, 258)))

# --- измерительный тракт: как в volt_probe, один в один
d.add(kigen.Part("U4", "Amplifier_Operational:LMV358", "LMV358", "%s:%s" % SO8,
                 {"1": "AOUT", "2": "FB", "3": "INP", "4": "GND",
                  "5": "VREFD", "6": "VREF", "7": "VREF", "8": "+3V3"},
                 at=(165, 45)))
d.add(kigen.Part("J4", "Connector_Generic:Conn_01x02", "PROBE",
                 "%s:PinHeader_1x02_P2.54mm_Vertical" % HDRLIB,
                 {"1": "VIN+", "2": "VIN-"}, at=(55, 40)))
d.add(kigen.Part("R1", "Device:R", "470k", "%s:%s" % R0805,
                 {"1": "VIN+", "2": "INP"}, at=(95, 25)))
d.add(kigen.Part("R2", "Device:R", "470k", "%s:%s" % R0805,
                 {"1": "VIN-", "2": "FB"}, at=(95, 60)))
d.add(kigen.Part("R3", "Device:R", "18k", "%s:%s" % R0402,
                 {"1": "INP", "2": "VREF"}, at=(130, 25)))
d.add(kigen.Part("R4", "Device:R", "18k", "%s:%s" % R0402,
                 {"1": "FB", "2": "AOUT"}, at=(130, 60)))
d.add(kigen.Part("R5", "Device:R", "10k", "%s:%s" % R0402,
                 {"1": "+3V3", "2": "VREFD"}, at=(235, 25)))
d.add(kigen.Part("R6", "Device:R", "10k", "%s:%s" % R0402,
                 {"1": "VREFD", "2": "GND"}, at=(235, 60)))
d.add(kigen.Part("C2", "Device:C", "100nF", "%s:%s" % C0402,
                 {"1": "VREFD", "2": "GND"}, at=(258, 60)))
d.add(kigen.Part("C3", "Device:C", "100nF", "%s:%s" % C0402,
                 {"1": "+3V3", "2": "GND"}, at=(205, 25)))
d.add(kigen.Part("R7", "Device:R", "220R", "%s:%s" % R0402,
                 {"1": "AOUT", "2": "VOUT"}, at=(285, 45)))
d.add(kigen.Part("C1", "Device:C", "470pF", "%s:%s" % C0402,
                 {"1": "VOUT", "2": "GND"}, at=(308, 60)))
# BAT54S: 1 - анод нижнего (GND), 2 - катод верхнего (3V3), 3 - средняя точка
d.add(kigen.Part("D1", "Diode:BAT54S", "BAT54S", "%s:%s" % SOT23,
                 {"1": "GND", "2": "+3V3", "3": "INP"}, at=(110, 90)))
d.add(kigen.Part("D2", "Diode:BAT54S", "BAT54S", "%s:%s" % SOT23,
                 {"1": "GND", "2": "+3V3", "3": "FB"}, at=(150, 90)))

# +3V3 флага не требует: эту цепь уже «питает» выход LDO. Флаг на ней даёт
# конфликт двух Power output - ERC это ловит.
for i, n in enumerate(["GND", "+5V"]):
    d.add(kigen.Part("#FLG%d" % i, "power:PWR_FLAG", "PWR_FLAG", "", {"1": n},
                     at=(555, 40 + 22 * i)))

FPLIB = "fcan"
os.makedirs(OUT, exist_ok=True)
for _pt in d.parts:
    if ":" in _pt.footprint:
        _pt.footprint = FPLIB + ":" + _pt.footprint.split(":", 1)[1]
d.write_sch(os.path.join(OUT, NAME + ".kicad_sch"))
for p in d.parts:
    if p.ref.startswith("#"):
        continue
    for pn, net in p.nets.items():
        try:
            b.setnet(p.ref, pn, net)
        except KeyError:
            pass

# ------------------------------------------------------------ шелкография
# Надписи на обороте: лицевая сторона занята плотно.
b.text(NAME, CXB, 118.0, pcbnew.B_SilkS, 1.6, 0.25, mirror=True)
b.text("CAN FD 250k/1M   BUS 5V", CXB, 121.5, pcbnew.B_SilkS, 1.0, 0.18, mirror=True)

# ------------------------------------------------------------ библиотека проекта
LIBDIR = os.path.join(OUT, FPLIB + ".pretty")
os.makedirs(LIBDIR, exist_ok=True)
_saved = set()
for _ref, _fp in b.fps.items():
    _nm = str(_fp.GetFPID().GetLibItemName())
    if _nm not in _saved:
        _c = None
        for _args in ((False,), (False, True), ()):
            try:
                _c = _fp.Duplicate(*_args)
                break
            except TypeError:
                continue
        if _c is None:
            raise RuntimeError("не удалось скопировать футпринт %s" % _nm)
        if not hasattr(_c, "IsFlipped"):      # KiCad 10 отдаёт BOARD_ITEM
            _c = pcbnew.Cast_to_FOOTPRINT(_c)
        if _c.IsFlipped():
            _c.Flip(_c.GetPosition(), False)
        _c.SetPosition(pcbnew.VECTOR2I(0, 0))
        _c.SetOrientationDegrees(0)
        _c.SetReference("REF**")
        _c.SetValue(_nm)
        pcbhelp.footprint_save(LIBDIR, _c)
        _saved.add(_nm)
    _fp.SetFPID(pcbnew.LIB_ID(FPLIB, _nm))
print("библиотека проекта: %d футпринтов" % len(_saved))

with open(os.path.join(OUT, "fp-lib-table"), "w") as _t:
    _t.write('(fp_lib_table\n  (version 7)\n'
             '  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.pretty")(options "")(descr "Footprints used by this board"))\n)\n'
             % (FPLIB, FPLIB))

b.finish(os.path.join(OUT, NAME + ".kicad_pcb"), fill=False)
print("OK ->", OUT)
