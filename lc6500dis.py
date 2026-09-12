#!/usr/bin/env python3
"""
lc6500dis.py - disassembler for the Sanyo LC6500 series (LC6554D/H).

Opcode map transcribed from the LC6554D/6554H datasheet, Sanyo ordering number
EN 2156B, pages 24-26 ("LC6554D/H INSTRUCTION SET").  80 instructions.

Register/architecture summary from the same datasheet:
  AC    4-bit accumulator            E     4-bit E register
  DP    data pointer, DPH:DPL        M     RAM, 256 x 4, addressed by DP
  CF    carry flag                   ZF    zero flag
  CTL   control register             F0-F15 flag bits
  PC    12-bit program counter, 8-level stack, ROM 4096 bytes
  A0-A3, H0-H1, L0-L1  working registers

Address forms:
  JMP/CAL   11-bit absolute (JMP within current bank, CAL into bank 0)
  Bxx       8-bit, within the current 256-byte page
  CZP       4-bit, calls 0x000-0x00F

Usage: lc6500dis.py rom.bin [--start 0] > listing.asm
"""

import sys
from collections import defaultdict

# ---------------------------------------------------------------- opcode table

# Ports are selected by DPL for IP/OP/SPB/RPB/BP/BNP.  The LC6554 has no port H;
# PORTS[i] is the letter for DPL = i.
PORTS = "ABCDEFGHIJKLMNOP"   # H is reserved; the LC6554 has no port H

ONE, TWO = 1, 2
tbl = {}          # opcode -> (mnemonic, length, kind)
# kind: None, 'jmp', 'cal', 'br', 'czp', 'ret', 'prefix'


def put(code, mnem, length=ONE, kind=None):
    tbl[code] = (mnem, length, kind)


# --- accumulator -------------------------------------------------------------
put(0xC0, "CLA")                       # also LI 0
put(0xE1, "CLC")
put(0xF1, "STC")
put(0xEB, "CMA")
put(0x0E, "INC")
put(0x0F, "DEC")
put(0x01, "RAL")
put(0x03, "TAE")
put(0x0D, "XAE")
# --- memory ------------------------------------------------------------------
put(0x2E, "INM")
put(0x2F, "DEM")
for b in range(4):
    put(0x08 | b, "SMB  %d" % b)
    put(0x28 | b, "RMB  %d" % b)
# --- arithmetic / compare ----------------------------------------------------
put(0x60, "AD")
put(0x20, "ADC")
put(0xE6, "DAA")
put(0xEA, "DAS")
put(0xF5, "EXL")
put(0xE7, "AND")
put(0xE5, "OR")
put(0xFB, "CM")
put(0x2C, "<prefix>", TWO, 'prefix')   # CI / CLI / SCTL / RCTL
# --- load / store ------------------------------------------------------------
for n in range(16):
    put(0xC0 | n, "LI   #%d" % n)      # overwrites CLA at 0xC0 below
put(0xC0, "CLA")
put(0x02, "S")
put(0x21, "L")
for m in range(8):
    put(0xA0 | m, "XM   #%d" % m)
put(0xA0, "X")
put(0xFE, "XI")
put(0xFF, "XD")
put(0x63, "RTBL")
# --- data pointer ------------------------------------------------------------
for n in range(16):
    put(0x80 | n, "LDZ  #%d" % n)
    put(0x40 | n, "LHI  #%d" % n)
put(0xEE, "IND")
put(0xEF, "DED")
put(0xF7, "TAL")
put(0xE9, "TLA")
put(0x23, "XAH")
# --- working registers -------------------------------------------------------
for t in range(4):
    put(0xE0 | (t << 2), "XA%d" % t)
put(0xF8, "XH0")
put(0xFC, "XH1")
put(0xF0, "XL0")
put(0xF4, "XL1")
# --- flags -------------------------------------------------------------------
for n in range(16):
    put(0x50 | n, "SFB  %d" % n)
    put(0x10 | n, "RFB  %d" % n)
# --- jump / subroutine -------------------------------------------------------
for p in range(8):
    put(0x68 | p, "JMP", TWO, 'jmp')
    put(0xA8 | p, "CAL", TWO, 'cal')
put(0xFA, "JPEA")
for n in range(16):
    put(0xB0 | n, "CZP  $%03X" % n, ONE, 'czp')
put(0x62, "RT", ONE, 'ret')
put(0x22, "RTI", ONE, 'ret')
put(0xFD, "BANK")
for n in range(4):
    put(0x64 | n, "SB   %d" % n)
# --- branches (all 2-byte, page-local) ---------------------------------------
for t in range(4):
    put(0x70 | t, "BA%d" % t, TWO, 'br')
    put(0x30 | t, "BNA%d" % t, TWO, 'br')
    put(0x74 | t, "BM%d" % t, TWO, 'br')
    put(0x34 | t, "BNM%d" % t, TWO, 'br')
    put(0x78 | t, "BP%d" % t, TWO, 'br')
    put(0x38 | t, "BNP%d" % t, TWO, 'br')
put(0x7C, "BTM", TWO, 'br')
put(0x3C, "BNTM", TWO, 'br')
put(0x7D, "BI", TWO, 'br')
put(0x3D, "BNI", TWO, 'br')
put(0x7E, "BZ", TWO, 'br')
put(0x3E, "BNZ", TWO, 'br')
put(0x7F, "BC", TWO, 'br')
put(0x3F, "BNC", TWO, 'br')
for n in range(16):
    put(0xD0 | n, "BF%-2d" % n, TWO, 'br')
    put(0x90 | n, "BNF%-2d" % n, TWO, 'br')
# --- I/O ---------------------------------------------------------------------
put(0x0C, "IP")
put(0x61, "OP")
for b in range(4):
    put(0x04 | b, "SPB  %d" % b)
    put(0x24 | b, "RPB  %d" % b)
# --- other -------------------------------------------------------------------
put(0xF9, "WTTM")
put(0xF6, "HALT")
put(0x00, "NOP")

UNDEFINED = sorted(set(range(256)) - set(tbl))   # 0x2D, 0xE2, 0xE3, 0xED, 0xF2, 0xF3


# ---------------------------------------------------------------- decoding

def decode(b, pc):
    """Return (text, length, kind, target) for the instruction at pc."""
    op = b[pc]
    if op not in tbl:
        return (".db  $%02X          ; undefined opcode" % op, 1, 'bad', None)
    mnem, length, kind = tbl[op]
    if length == ONE:
        if kind == 'czp':
            return (mnem, 1, kind, op & 0x0F)
        return (mnem, 1, kind, None)

    arg = b[pc + 1]
    if kind == 'jmp':
        tgt = ((op & 7) << 8) | arg
        return ("JMP  $%03X" % tgt, 2, kind, tgt)
    if kind == 'cal':
        tgt = ((op & 7) << 8) | arg
        return ("CAL  $%03X" % tgt, 2, kind, tgt)
    if kind == 'br':
        tgt = (pc & 0xF00) | arg
        return ("%-5s$%03X" % (mnem, tgt), 2, kind, tgt)
    if kind == 'prefix':
        hi, lo = arg >> 4, arg & 0x0F
        name = {4: "CI   #%d" % lo, 5: "CLI  #%d" % lo,
                8: "SCTL $%X" % lo, 9: "RCTL $%X" % lo}.get(hi)
        if name is None:
            return (".db  $2C,$%02X      ; bad $2C prefix" % arg, 2, 'bad', None)
        return (name, 2, None, None)
    return (mnem, length, kind, None)


def trace(b, end, entries):
    """Recursive descent.  Returns instruction starts, operand bytes, xrefs."""
    starts, operands = set(), set()
    xref = defaultdict(set)
    stack, seen = list(entries), set()
    while stack:
        pc = stack.pop()
        while 0 <= pc < end and pc not in seen:
            seen.add(pc)
            txt, ln, kind, tgt = decode(b, pc)
            if kind == 'bad':
                break
            starts.add(pc)
            if ln == 2:
                operands.add(pc + 1)
            if tgt is not None:
                xref[tgt].add(pc)
                stack.append(tgt)
            if kind in ('jmp',):
                break
            if kind == 'ret':
                break
            pc += ln
    return starts, operands, xref


def listing(b, end, entries, out):
    starts, operands, xref = trace(b, end, entries)
    covered = starts | operands
    subs = sorted({t for a in xref for t in [a]})

    print("; Commodore CDTV U62 - Sanyo LC6554H front-panel controller", file=out)
    print("; Disassembled with the LC6554D/H instruction set (Sanyo EN 2156B, pp.24-26)", file=out)
    print("; Reset entry $000.  %d of %d programmed bytes reached by trace.\n"
          % (len(covered), end), file=out)

    pc = 0
    state = (None, None, None, None)
    while pc < end:
        if pc not in starts:
            run = pc
            while run < end and run not in starts:
                run += 1
            print("", file=out)
            for o in range(pc, run, 8):
                row = b[o:min(o + 8, run)]
                print("%03X   %-8s   .db  %s"
                      % (o, '', ','.join('$%02X' % x for x in row)), file=out)
            print("", file=out)
            pc = run
            state = (None, None, None, None)
            continue
        if pc in xref:
            print("\n; ---- $%03X  <- %s" % (pc, ', '.join('$%03X' % a for a in sorted(xref[pc]))),
                  file=out)
            state = (None, None, None, None)
        txt, ln, kind, tgt = decode(b, pc)
        state, note = annotate(b, starts, pc, state)
        raw = ' '.join('%02X' % x for x in b[pc:pc + ln])
        print("%03X   %-8s   %-14s%s" % (pc, raw, txt, ('; ' + note) if note else ''), file=out)
        if kind in ('jmp', 'ret'):
            state = (None, None, None, None)
        pc += ln
    return starts, operands, xref


def annotate(b, starts, pc, state):
    """Light forward simulation so port and table accesses can be named."""
    op = b[pc]
    ac, e, dpl, dph = state
    note = ''
    if 0x80 <= op <= 0x8F:
        dpl, dph = op & 15, 0
    elif 0x40 <= op <= 0x4F:
        dph = op & 15
    elif 0xC0 <= op <= 0xCF:
        ac = op & 15
    elif op == 0xEE:
        dpl = None if dpl is None else (dpl + 1 if dpl >= 100 else (dpl + 1) & 15)
    elif op == 0xEF:
        dpl = None if dpl is None else (dpl - 1) & 15
    elif op == 0x03:
        e = ac
    elif op == 0x0D:
        ac, e = e, ac
    elif op == 0x23:
        ac, dph = dph, ac
    elif op in (0xF7, 0xF0, 0xF4, 0xFE, 0xFF) or 0xA0 <= op <= 0xA7:
        dpl, ac = None, None
    elif op in (0xF8, 0xFC):
        dph = None
    elif op == 0x63:
        if e is not None:
            note = 'read ROM table $%03X + AC' % ((pc & 0xF00) | (e << 4))
        ac, e = None, None
    elif op in (0x0C, 0x61) or 0x04 <= op <= 0x07 or 0x24 <= op <= 0x27 \
            or 0x78 <= op <= 0x7B or 0x38 <= op <= 0x3B:
        if dpl is not None and dpl < 16:
            note = 'port %s' % PORTS[dpl]
        if op == 0x0C:
            ac = None
    elif op == 0x21:
        ac = None
        if dph is not None and dpl is not None and dpl < 100:
            note = 'M($%02X)' % ((dph << 4) | dpl)
    elif op == 0x02:
        if dph is not None and dpl is not None and dpl < 100:
            note = 'M($%02X)' % ((dph << 4) | dpl)
    else:
        if op not in (0x00, 0x02, 0x62, 0x22):
            ac = None
    return (ac, e, dpl, dph), note


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'u62.bin'
    data = open(path, 'rb').read()
    END = 0x7F0
    listing(data, END, [0x000, 0x038, 0x03C], sys.stdout)
