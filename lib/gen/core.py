"""Ядро узла внутренней шины - замороженный схемный блок. Стандарт: docs/CORE.md.

Ядро - это всё, что одинаково на каждом узле: STM32G0B1 с кварцем, трансивер
TCAN332G, две колодки шины с терминатором, питание 5 В -> 3.3 В через диодное
ИЛИ и AP2210K, USB-C для DFU, кнопки RESET/BOOT, SWD, светодиод состояния.
Узел (вольтметр, шлюз, LIN...) добавляет к ядру только свою часть.

Здесь одна таблица PARTS, и из неё берётся всё: схема, цепи платы, значения,
посадочные места. Поменять ядро на одной плате нельзя - только здесь, и тогда
поменяется на всех. Это и есть заморозка.

Как пользоваться в build.py узла:

    import core, node
    core.symbols(OUT)                         # + свои символы, если нужны
    b = Builder(layers=2)
    core.place(b, {"U1": (x, y, rot), ...})   # каждая деталь ядра - где стоит
    ... b.place() своих деталей ...
    d = kigen.Design(NAME, TITLE); d.prepare()
    core.add(d, mcu={"11": "VOUT"})           # свои выводы МК - только свободные
    ... d.add() своих деталей ...
    node.finish(b, d, OUT, NAME)              # проверки, схема, плата, библиотеки
"""
import kigen
import symlib

SYMLIB = "fcan"

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
HDR2 = (HDRLIB, "PinHeader_1x02_P2.54mm_Vertical")
HDR4 = (HDRLIB, "PinHeader_1x04_P2.54mm_Vertical")

# Проектные символы ядра. AP2210K-3.3 в библиотеках KiCad нет: графику берём у
# AP2204K-1.5 (тот же SOT-23-5, та же раскладка 1/2/3/5), правим только вывод 4:
# у AP2204K это NC, у AP2210K - BYP, и на нём висит конденсатор.
SYMBOLS = [
    {"name": "AP2210K-3.3",
     "from": "Regulator_Linear:AP2204K-1.5",
     "pins": {"4": ("BYP", "passive")},
     "props": {"Reference": "U",
               "Value": "AP2210K-3.3",
               "Footprint": "Package_TO_SOT_SMD:SOT-23-5",
               "Datasheet": "https://www.diodes.com/assets/Datasheets/AP2210.pdf",
               "Description": "300 mA LDO 3.3 V, VIN 4.3...13.2 V, SOT-23-5"}},
]

USBC_LIBID = "Connector:USB_C_Receptacle_USB2.0_16P"

# Выводы STM32G0B1CBT6 (LQFP-48), которые занимает ядро. Номера сверены с
# символом KiCad. Узлу эти выводы не достаются ни при каких условиях.
#   PD0/PD1   - FDCAN1 RX/TX, та же пара, что у ПЗУ-загрузчика (AN2606, ID 0x92).
#   PA11/PA12 - USB DFU. На всех корпусах G0 это ремап ног 33/34, которые по
#               умолчанию отдают PA9/PA10. Прошивка обязана выставить
#               SYSCFG_CFGR1 PA11_RMP/PA12_RMP, иначе USB не поднимется.
#   PA14      - SWCLK и BOOT0 одновременно (так устроен G0). Кнопка BOOT тянет
#               его вверх, резистор 10к - вниз. Чтобы кнопка заработала, в опциях
#               надо сбросить nBOOT_SEL. Чистый кристалл это прошить не мешает -
#               при пустой флеш-памяти G0 уходит в загрузчик сам.
#   PF2       - NRST.
MCU_PINS = {
    "1": "LED_K",        # PC13 - светодиод состояния
    "4": "+3V3",         # VBAT
    "5": "+3V3",         # VREF+
    "6": "+3V3",         # VDD
    "7": "GND",          # VSS
    "8": "OSC_IN",       # PF0
    "9": "OSC_OUT",      # PF1
    "10": "NRST",        # PF2
    "33": "USB_DM",      # PA9/PA11 - нужен ремап
    "34": "USB_DP",      # PA10/PA12 - нужен ремап
    "35": "SWDIO",       # PA13
    "36": "SWCLK",       # PA14, он же BOOT0
    "38": "CAN_RX",      # PD0
    "39": "CAN_TX",      # PD1
}

# Цепи, которые узел может брать у ядра. Всё остальное - внутреннее дело ядра.
PUBLIC_NETS = {"+3V3", "+5V", "GND"}

# Таблица ядра: ref -> (символ, значение, посадочное место, {вывод: цепь},
# место на схеме). U1 здесь без выводов: они собираются в add() из MCU_PINS
# и выводов узла.
PARTS = {
    # --- микроконтроллер и кварц
    "U1": ("MCU_ST_STM32G0:STM32G0B1CBTx", "STM32G0B1CBT6", LQFP48, {}, (160, 120)),
    "Y1": ("Device:Crystal", "8MHz", XTAL, {"1": "OSC_IN", "2": "OSC_OUT"}, (80, 150)),
    "C4": ("Device:C", "33pF", C0402, {"1": "OSC_IN", "2": "GND"}, (60, 165)),
    "C5": ("Device:C", "33pF", C0402, {"1": "OSC_OUT", "2": "GND"}, (100, 165)),
    # развязка VDD
    "C8": ("Device:C", "100nF", C0402, {"1": "+3V3", "2": "GND"}, (240, 155)),
    "C9": ("Device:C", "4.7uF", C0805, {"1": "+3V3", "2": "GND"}, (262, 155)),
    "C10": ("Device:C", "100nF", C0402, {"1": "+3V3", "2": "GND"}, (284, 155)),
    "C11": ("Device:C", "1uF", C0402, {"1": "+3V3", "2": "GND"}, (306, 155)),

    # --- сброс и загрузка
    "SW1": ("Switch:SW_Push", "RESET", SWFP, {"1": "NRST", "2": "GND"}, (60, 205)),
    "C14": ("Device:C", "100nF", C0402, {"1": "NRST", "2": "GND"}, (88, 205)),
    "SW2": ("Switch:SW_Push", "BOOT", SWFP, {"1": "SWCLK", "2": "+3V3"}, (122, 205)),
    "R11": ("Device:R", "10k", R0402, {"1": "SWCLK", "2": "GND"}, (150, 205)),
    # SWD нужен не для прошивки (её делает ПЗУ-загрузчик), а для отладки.
    "J5": ("Connector_Generic:Conn_01x04", "SWD", HDR4,
           {"1": "+3V3", "2": "SWDIO", "3": "SWCLK", "4": "GND"}, (190, 205)),

    # --- светодиод состояния
    "R12": ("Device:R", "1k", R0402, {"1": "+3V3", "2": "LED_A"}, (330, 115)),
    "D5": ("Device:LED", "LED", LED0805, {"1": "LED_K", "2": "LED_A"}, (330, 140)),

    # --- шина CAN FD
    "U2": ("Interface_CAN_LIN:TCAN332", "TCAN332G", SOT238,
           {"1": "CAN_TX", "2": "GND", "3": "+3V3", "4": "CAN_RX",
            "6": "CANL", "7": "CANH"}, (400, 120)),
    "C6": ("Device:C", "100nF", C0402, {"1": "+3V3", "2": "GND"}, (375, 155)),
    "C7": ("Device:C", "1uF", C0603, {"1": "+3V3", "2": "GND"}, (398, 155)),
    # терминатор: запаивается только на двух крайних узлах гирлянды
    "R8": ("Device:R", "120R", R0603, {"1": "CANH", "2": "TERM"}, (455, 100)),
    "JP1": ("Jumper:SolderJumper_2_Open", "TERM", JPFP, {"1": "TERM", "2": "CANL"}, (455, 125)),
    # две колодки параллельно: кабель входит в одну, выходит из другой
    "J1": ("Connector_Generic:Conn_01x04", "BUS", PHFP,
           {"1": "BUS5V", "2": "CANH", "3": "CANL", "4": "GND"}, (510, 75)),
    "J2": ("Connector_Generic:Conn_01x04", "BUS", PHFP,
           {"1": "BUS5V", "2": "CANH", "3": "CANL", "4": "GND"}, (510, 165)),

    # --- питание: 5 В из шины и из USB через диодное ИЛИ, дальше LDO
    "D3": ("Device:D_Schottky", "SS34", SMA, {"2": "BUS5V", "1": "+5V"}, (400, 215)),
    "D4": ("Device:D_Schottky", "SS34", SMA, {"2": "VBUS", "1": "+5V"}, (400, 240)),
    # AP2210K-3.3, а не AP2112K: тот же корпус и выводы 1/2/3/5, но вход до
    # 13.2 В (предел 15 В), защита от обратной полярности, до +125 C, PSRR 75 дБ.
    # Замена на случай дефицита - AP2112K-3.3 (C51118): вывод 4 у неё NC, и
    # C15 на нём просто ничего не делает. Разбор - docs/BUS.md, «Питание».
    "U3": ("%s:AP2210K-3.3" % SYMLIB, "AP2210K-3.3", SOT235,
           {"1": "+5V", "2": "GND", "3": "+5V", "4": "BYP", "5": "+3V3"}, (455, 225)),
    "C12": ("Device:C", "1uF", C0603, {"1": "+5V", "2": "GND"}, (428, 258)),
    # BYP: 100 пФ по типовой схеме из datasheet - это и есть низкий шум.
    "C15": ("Device:C", "100pF", C0402, {"1": "BYP", "2": "GND"}, (482, 250)),
    "C13": ("Device:C", "1uF", C0402, {"1": "+3V3", "2": "GND"}, (495, 258)),

    # --- USB-C: питание и прошивка по DFU. Выводы - в add(): SHIELD зависит от символа.
    "J3": (USBC_LIBID, "USB-C", USBCFP, None, (60, 255)),
    "R9": ("Device:R", "5.1k", R0402, {"1": "CC1", "2": "GND"}, (125, 258)),
    "R10": ("Device:R", "5.1k", R0402, {"1": "CC2", "2": "GND"}, (150, 258)),
}

REFS = tuple(PARTS)

# Флаги питания: +3V3 флага не требует, её уже «питает» выход LDO (флаг дал бы
# конфликт двух Power output в ERC).
PWR_FLAGS = ("GND", "+5V")


def _private_nets():
    nets = set(MCU_PINS.values())
    for ref, (_, _, _, pins, _) in PARTS.items():
        if pins:
            nets.update(pins.values())
    nets.update({"VBUS", "CC1", "CC2", "USB_DP", "USB_DM"})
    return nets - PUBLIC_NETS


PRIVATE_NETS = _private_nets()


def symbols(out, extra=()):
    """Проектная библиотека символов: символы ядра + символы узла."""
    return symlib.build(out, SYMLIB, list(SYMBOLS) + list(extra))


def place(b, at):
    """Поставить детали ядра на плату. at: {ref: (x, y, rot)} - ровно по ядру.

    Где стоит ядро, решает узел: форма платы у всех разная. Состав и
    посадочные места - нет.
    """
    missing = [r for r in REFS if r not in at]
    extra = [r for r in at if r not in PARTS]
    if missing or extra:
        raise ValueError("core.place: не размещены %s, лишние %s" % (missing, extra))
    for ref, (_, value, fp, _, _) in PARTS.items():
        x, y, rot = at[ref]
        b.place(ref, fp[0], fp[1], x, y, rot, value=value)


def add(d, mcu=None):
    """Добавить ядро в схему. mcu: {вывод LQFP-48: цепь} - выводы МК узла."""
    mcu = dict(mcu or {})
    busy = sorted(set(mcu) & set(MCU_PINS), key=int)
    if busy:
        raise ValueError("выводы МК %s заняты ядром (docs/CORE.md)" % busy)
    bad = sorted(set(mcu.values()) & PRIVATE_NETS)
    if bad:
        raise ValueError("цепи %s принадлежат ядру, узлу их брать нельзя" % bad)
    shield = [p.number for p in kigen.get_symbol(USBC_LIBID).pins if p.name == "SHIELD"][0]
    for ref, (libid, value, fp, pins, at) in PARTS.items():
        if ref == "U1":
            pins = dict(MCU_PINS)
            pins.update(mcu)
        elif ref == "J3":
            pins = {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND",
                    "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
                    "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP",
                    "A7": "USB_DM", "B7": "USB_DM", shield: "GND"}
        d.add(kigen.Part(ref, libid, value, "%s:%s" % fp, pins, at=at))
    for i, n in enumerate(PWR_FLAGS):
        d.add(kigen.Part("#FLG%d" % i, "power:PWR_FLAG", "PWR_FLAG", "", {"1": n},
                         at=(555, 40 + 22 * i)))


def check(d):
    """Детали узла не должны трогать ядро: ни его позиционные обозначения,
    ни его внутренние цепи."""
    errs = []
    seen = set()
    for p in d.parts:
        if p.ref in seen:
            errs.append("%s: обозначение повторяется" % p.ref)
        seen.add(p.ref)
        if p.ref in PARTS or p.ref.startswith("#"):
            continue
        bad = sorted(set(p.nets.values()) & PRIVATE_NETS)
        if bad:
            errs.append("%s: подключена к цепям ядра %s" % (p.ref, bad))
    for ref in REFS:
        if ref not in seen:
            errs.append("%s: деталь ядра не добавлена (core.add)" % ref)
    if errs:
        raise ValueError("нарушен стандарт ядра:\n  " + "\n  ".join(errs))
