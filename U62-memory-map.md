# CDTV U62 (Sanyo LC6554H) — memory map, first pass

Derived from `U62.asm`. Addresses are LC6554H program-ROM addresses; the EPROM
image is a 1:1 copy at the same offsets.

## Program ROM

| Address | Contents |
|---|---|
| `$000` | Reset entry. `RCTL $F` clears the control register, drives port A high, then clears all 256 RAM nibbles with a `CLA / XI / BNZ` loop over DPL and DPH |
| `$010`–`$030` | Power-on initialisation; sets up RAM state, calls `$3B2`, `$400`, `$77F`, loads the timer with `E:AC = $7D` (`LI #7 / TAE / LI #13 / WTTM`), enables interrupts with `SCTL $1` |
| `$038` | **Interrupt vector** — `JMP $098` |
| `$03C` | **Second interrupt vector** — `RTI` (unused source) |
| `$03D` | Main loop. Calls `$16A`, `$278`, `$48A`, `$104`, `$35F`, `$374`, `$208`, `$600`, `$300`, `$2D8`, `$05F`, then idles at `$058` until `M($0B)` goes non-zero |
| `$05F` | Housekeeping routine; ends by writing `M($26)` to **port G** (PG = _VDATA/_VCK/_VST/_KBRESET) |
| `$080`–`$08F` | **7-segment font**, read by `RTBL` at `$0AD` with `E = 8` |
| `$090`–`$097` | **Grid mask table**, read by `RTBL` at `$0C8` with `E = 9` |
| `$098`–`$0F7` | **Timer ISR — display refresh** (see below) |
| `$0F8`–`$103` | Data |
| `$104`, `$16A`, `$208`, `$278`, `$2D8`, `$300`, `$35F`, `$374`, `$3B2`, `$400`, `$48A`, `$600`, `$77F` … | Subroutines; 32 distinct call targets in all |
| `$4F6`–`$545`, `$5E1`–`$5EF`, `$700`–`$763`, `$7E1`–`$7EF` | Data tables. The page-4/5 and page-7 tables are the ones reached by the `RTBL` instructions at `$55E`, `$56B` and `$772` |

Hot subroutines: `$5B7` (18 calls), `$2BB` (8), `$15E` (7), `$200` and `$204`
(7 each — a matched set/clear pair, `LDZ #15 / LI #1 / OP / RT` and
`LDZ #15 / CLA / OP / RT`, i.e. drive port P high or low).

## Timer ISR at `$098` — front-panel multiplex

```
098  XA0 / XAE / XA1 / XL0 / XH0     save AC, E, DPL, DPH into working registers
09D  LDZ #13 / CLA / OP / IND / OP   blank both grid ports N and O
0A2  ...                             fetch the digit index from RAM
0A9  LDZ #0 / LHI #8 / XAH / XAE     set E = 8  -> font table base $080
0AD  RTBL                            AC,E <- ROM[$080 + digit]
0AE  LDZ #11 / XAE / OP              low  segment nibble -> port L  (Sa..Sd)
0BE  LDZ #12 / OP                    high segment nibble -> port M  (Se..Sh)
0C4  LDZ #0 / LHI #9 / XAH / XAE     set E = 9  -> grid table base $090
0C8  RTBL                            AC,E <- ROM[$090 + digit]
0C9  LDZ #13 / OP / IND / OP         grid pattern -> ports N and O (G1..G8)
0CE  ...                             advance the digit counter, mask to 0-7
0EC  LI #7 / TAE / LI #13 / WTTM     reload the timer with $7D
0F5  SCTL $1 / RTI                   re-arm the interrupt and return
```

## Port map

The LC6554 selects a port with DPL. The index is the port letter's position,
with slot 7 reserved for a port H the chip does not have.

| DPL | Port | CDTV signal (from `PinOut-U62.txt`) |
|---|---|---|
| 0 | A | CPCP0–3 (input only) |
| 1 | B | KI0–2 key inputs; PB3 tied high (input only) |
| 2 | C | KST0–3 key strobes |
| 3 | D | CD0–3 |
| 4 | E | CA0–3 |
| 5 | F | SDATA / SCK serial link to U75 |
| 6 | G | _VDATA / _VCK / _VST / _KBRESET |
| 8 | I | MS0, MS1, U74 pin 6, AUPLY |
| 9 | J | AUS0–2, MPS |
| 10 | K | POWER, GMS0, GMS1, U60 pin 19 |
| 11 | L | Sa–Sd segment drivers |
| 12 | M | Se–Sh segment drivers |
| 13 | N | G1–G4 grid drivers |
| 14 | O | G5–G8 grid drivers |
| 15 | P | PP0 (single bit) → U80 pin 2 |

## Data memory

256 × 4-bit RAM, addressed as DPH:DPL. `LHI` immediates only ever take values
`$0`–`$A`, so rows `$0`–`$A` are in use and rows `$B`–`$F` are untouched.
Known cells so far: `M($0B)` is the main-loop wake flag; `M($26)` is the port G
shadow; `M($60)` is a counter in the `$05F` routine.

---

## Update after the annotation pass

### `RTBL` nibble order (proved twice)

`RTBL` loads **AC from bits 7–4** of the ROM byte and **E from bits 3–0**.
Confirmed independently by the key strobe table (`EF DF BF 7F` → `E, D, B, 7`,
the active-low one-of-four patterns that appear on KST0–3) and by the font
(`$3F` for digit `0` → `F` to port L = Sa–Sd all on, `3` to port M = Se+Sf on,
Sg off, which is exactly a `0`).

### Display buffer

| RAM | Meaning |
|---|---|
| `M($00)`–`M($07)` | Eight-digit display buffer, each a 0–15 index into the font at `$080` |
| `M($08)` | Multiplex digit index, advanced and masked to 0–7 each interrupt |
| `M($30)`–`M($37)` | Per-digit extra Se–Sh bits, OR'd into the font's high nibble — this is how the decimal points and the panel's standalone indicator segments are lit |
| `M($3B)` | Temp holding the segment high nibble across the OR |

To drive the panel from a replacement controller you only need to reproduce this:
write a font index into `M($00+n)`, optional extra segments into `M($30+n)`, and
let the timer ISR sweep.

### The U75 link

There is no serial protocol between U62 and U75. `U75_pins.txt` shows the two
chips are wired with parallel nibbles:

| Direction | U62 | U75 | Signals |
|---|---|---|---|
| U75 → U62 | port A (in) | PB4–PB7 | CPCP0–3 |
| U62 → U75 | port J bits 0,2,3 (out) | PB3, PB0, PB1 | AUS2, AUS0, AUS1 |

`f_ReadU75Command` at `$48A` is the entire receive side. It clears `M($50)`–`M($54)`,
reads the CPCP nibble once, and runs a `CI`/`BZ` chain over the values 0–10.
Command 0 returns immediately; each of 1–10 sets exactly one of the five result
cells to 1 or 2. So the interface is five two-state requests encoded as a
command number, not a numeric value — pairs like (1,2), (3,4), (5,9), (6,10),
(7,8) toggle the same cell between its two states.

The transmit side is the port J shadow `M($29)`, written by the `$208`, `$278`,
`$300`, `$374`, `$400`, `$600`, `$6AD`, `$6C4`, `$764` and `$77F` routines.

### Port G is a three-wire bus, not a display bus

`f_ShiftBitG` at `$5B7` shifts one bit out of AC: `RAL` moves AC bit 3 into carry,
`SMB 0`/`RMB 0` sets the data bit in the `M($26)` shadow, `OP` presents it, then
`SMB 1`/`OP` and `RMB 1`/`OP` pulse the clock. So PG0 = _VDATA is data and
PG1 = _VCK is clock, exactly as the pinout names them. It is called from 18 sites,
so callers push bits one at a time rather than looping.

### Key matrix

`f_ScanKeys` at `$104` strobes one row per call. `M($40)` is the row counter 0–3,
`RTBL` at `$10A` fetches the active-low strobe from `$100`, `OP` drives KST0–3,
`IP` reads KI0–2 back, and `f_KeyRowPtr` at `$15E` computes `DPL = row × 4` so the
four-nibble debounce block for that row sits at `M($10 + 4×row)`. When a keypress
survives debounce the routine sets `M($0B)`, which is the flag the main loop at
`$058` is spinning on.

### Open question

`$41C` contains seven `BANK` instructions interleaved with port writes. The opcode
is confirmed as `$FD` against the scan, and `BANK` only takes effect on a following
`JMP` — there is no `JMP` in that routine, so they act as one-cycle pads. Whether
that was deliberate padding or a quirk of Commodore's toolchain is unresolved, and
the routine's purpose (eight `SCK` pulses on port F with the data lines high, while
writing patterns to the display driver ports) is still a guess.

---

## The three ROM tables, decoded

### `$700`–`$763` — binary to BCD, not ASCII

100 entries, indexed 0–99, read by `RTBL` at `$772`. The byte splits into the two
font indices for DISP4 and DISP5.

```
700: AA A1 A2 A3 A4 A5 A6 A7 A8 A9 10 11 12 13 14 15
710: 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31
...
750: 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95
760: 96 97 98 99  <- $764 is code
```

It is **packed BCD**. Entry *n* is the BCD encoding of *n*, except that entries
0–9 use `$A` in the high nibble — font index 10 is the blank glyph — so the
leading zero is suppressed. Value 0 shows nothing at all, 1–9 show a single digit,
10–99 show two.

The printable-ASCII run is a coincidence: BCD digits 0–9 in the low nibble land on
ASCII `0`–`9`, and the high nibbles 2,3,4,5,6,7 put them in the printable range.
`$714` = `$36` is BCD 36, not the character `6`.

The index arrives as a 7-bit binary value from `$7CB` (`TMP0` masked to 3 bits as
the high nibble, `TMP1` as the low), so this is a binary-to-decimal conversion for a
0–99 quantity — the track number is the obvious candidate. Indices 100–127 are
possible in principle and would read the code at `$764` onward as font indices, so
the CD subsystem is assumed never to report above 99.

### `$500`–`$545` — attenuator level table

70 bytes = 35 pairs, indexed by twice the volume (0, 2, 4 … `$44`), which matches
the 0–`$22` clamp in `$300` exactly: **35 volume steps**. `$546` does two `RTBL`
reads (index and index+1) to collect four nibbles, then shifts 16 bits plus two
trailing zeros — 18 bits, matching the 18 calls to `$5B7`.

```
500: 81 06   80 86   80 46   80 26   80 16     <- levels 0-4
510: 40 26   40 16   21 06   20 86   20 46     ...
540: 02 46   02 26   02 16                     <- level 34
```

First bytes step through 81, 80, 41, 40, 21, 20, 11, 10, 09, 08, 05, 04, 03, 02;
second bytes cycle 06, 86, 46, 26, 16. That is a coarse/fine pair — a two-section
attenuator with a one-hot coarse selector and a five-step fine trim.

### `$080`–`$097` — font and grid, with the physical digit order

The grid table is unambiguous about which VFD grid each buffer position lights:

| buffer | mask | grid |
|---|---|---|
| DISP0 | `$04` | G3 |
| DISP1 | `$02` | G2 |
| DISP2 | `$80` | G8 |
| DISP3 | `$40` | G7 |
| DISP4 | `$20` | G6 |
| DISP5 | `$10` | G5 |
| DISP6 | `$08` | G4 |
| DISP7 | `$01` | G1 |

So in grid order G1…G8 the panel reads DISP7, DISP1, DISP0, DISP6, DISP5, DISP4,
DISP3, DISP2. Which end of the panel is G1 is not derivable from the ROM.

The volume bar in `$278` fills its digits in the order DISP6, DISP0, DISP1, DISP7,
DISP2, DISP3, DISP4, DISP5, taking mask bit 7 first — that is the reverse of the
grid order rotated by four, which is consistent but does not by itself settle the
left-to-right question.

---

## `$1000` and `$1100` are invisible to the firmware

Neither is referenced anywhere in the code, and neither *can* be. The LC6554H has
4096 bytes of program ROM and a 12-bit PC, so the highest address any instruction
can form is `$FFF`: `CAL` and `JMP` carry 11 address bits, and `BANK` supplies the
twelfth. Reaching `$1000` would need a thirteenth address line that the part does
not have. The piggyback adaptor takes a 2732 or 2764, so the 27C64's A12 is simply
not wired to the core.

| Offset | Contents | What it is |
|---|---|---|
| `$1000`–`$100A` | `23 00 00 00 00 00 F0 FF 0F 00 00` | Mask-option block. The LC6554 has selectable oscillator circuit, predivider, port C/D reset level, and per-bit pull-up (ports C–J) or pull-down (ports K–P) options; this is where they are recorded. Decoding the field layout needs the LC6554 Series User's Manual (No. E21B), so the individual bits are not identified here. |
| `$1100`–`$1129` | `"LC6554H"`, `"VER 1.20"`, `"26-09-1990"` | Human-readable label, three 16-byte zero-padded fields. |

Both are metadata for whoever burned the EPROM and for the mask-ROM order, not
data the running program uses. That also means they can be changed or omitted
without affecting behaviour — useful if you are burning a replacement part.

---

## What the `$700` table is actually for

It is the **two-digit track-number display**. Five things say so.

**It is polled, not read continuously.** `$7CB` is reached from exactly one place:
the idle tail of `f_TransportButtons`. When no button has been pressed for ten
service passes, `$6EE`–`$6FD` clears `CDTIMEOUT`, loads `CDCMD_LO/HI` with 0 and 1,
sends that over SDATA/SCK via `$41C`, waits in `$479`, sends the `$451` sequence,
then jumps to `$7CB` to read the two-nibble reply. The table converts that reply.

**Its input is a different device from the rest of the panel.** DISP0–DISP3 come
from the CA/CD nibble bus in `f_ReadCDPanel`. DISP4 and DISP5 are written in only
one place, `$764`, and their value comes from the SDATA/SCK link. The panel is fed
by two independent sources.

**The range is exactly 0–99.** Red Book track numbers run 1 to 99.

**Zero blanks the field completely.** Entry 0 is `$AA` — font index 10 twice, the
blank glyph. A time field would show `00`; only a "nothing selected" field goes
blank. Entries 1–9 blank just the leading digit, which is ordinary leading-zero
suppression.

**It blanks when the machine is off.** `$779` writes 10 to both digits when MPS
says the main logic is down.

### Timing

The whole chain falls out of the `$7D` timer reload, with `Tcyc = 1 µs` (4 MHz
ceramic resonator, 1/1 predivider — LC6554H datasheet Table 2):

| | |
|---|---|
| timer counts | 256 − `$7D` = 131, ÷16 prescaler |
| one digit | 2096 µs |
| full 8-digit sweep | 16.8 ms — **60 Hz panel refresh** |
| service pass (`TICK` nibble wraps every 16) | 33.5 ms |
| track-number poll (`CDTIMEOUT` = 10) | **335 ms** |

A 60 Hz refresh is what a VFD of this era wants, which is a good independent check
on the reload value and on the prescaler assumption.

### Consequences

The index is a 7-bit value (`TMP0` masked to 3 bits as the high nibble, `TMP1` as
the low), so 0–127 is expressible but only 0–99 is in the table. Indices 100–127
read the code at `$764` onward and would put arbitrary font indices on the panel.
The device is trusted never to report above 99.

This is also the best clue yet about the unidentified device on SDATA/SCK. Whatever
`$41C` and `$451` are talking to, it answers a status query with a binary track
number — so it is the CD drive's own controller, and the `BANK`-prefixed port
accesses in those routines are how U62 reaches it.

---

## `$4F6` — what is actually there

Nothing. `$4F0`–`$4F5` is the tail of the CPCP dispatch (`$4F1` `LDZ #0` / `LHI #5`
/ `LI #2` / `S` / `RT` — the handler for CPCP 10), and `$4F6`–`$4FF` is ten bytes of
`$00` filler. The real content starts at `$500`, page-aligned because `RTBL` forms
its address as `(PC & $F00) | (E << 4) | AC` and the level index has to start at
zero.

## `$500`–`$545` — the attenuator word table, decoded

70 bytes, 35 pairs, indexed by twice the volume. `$546` reads both bytes of a pair
with two `RTBL` calls and splits them into `ATT0`–`ATT3`, then `$5B7` shifts them
out MSB-first followed by two zero bits — 18 bits, matching the 18 call sites.

The bit layout is regular:

```
byte 1:  c c c c c c c f      byte 2:  f f f f 0 1 1 0
         7 6 5 4 3 2 1 0               7 6 5 4
```

* **bits 7–1 of byte 1: a 7-way one-hot coarse selector.** It steps `$80, $40, $20,
  $10, $08, $04, $02` — one position per five volume steps.
* **bit 0 of byte 1 plus bits 7–4 of byte 2: a 5-way one-hot fine selector.** Within
  each coarse group the fine tap runs `b1.0, b2.7, b2.6, b2.5, b2.4`.
* **bits 3–0 of byte 2 are always `$6`** — a constant field, presumably a chip
  address or mode nibble.

7 coarse × 5 fine = 35, which is exactly the `0`–`$22` clamp in `$300`. So the
attenuator is a two-section ladder driven by a one-hot tap select in each section,
and the firmware never computes the word — every level is a literal table entry.

### Which way is loud

`VOL` is an **attenuation** index: 0 is loudest, 34 is quietest. Two independent
proofs from the ROM:

1. `$208` writes `VOL = $22` (34, the maximum) when MPS says the main logic has
   gone away, and `$12` (18) when it comes back. `$400` does the same at startup.
   Setting *maximum volume* on power-down would be absurd; setting maximum
   attenuation is exactly right.
2. `$278` computes the bar level as `(VOL >> 2) & 7` and fetches the mask from
   `$270`, which runs `$FF, $FE, $FC, $F8, $F0, $E0, $C0, $80`. `VOL = 0` lights all
   eight bar segments; `VOL >= $20` is special-cased to `$80`, a single segment.
   The bar shrinks as `VOL` rises.

## The SDATA/SCK protocol, as far as the ROM determines it

The device is almost certainly the CD drive's own controller: the only thing it
ever returns is a value the `$700` table converts to a 0–99 track number.

**Port F is one bidirectional data wire plus a clock.** The pinout names both
PF0/SI (pin 35) and PF1/SO (pin 36) `SDATA` — they are tied together, which is why
the firmware always drives them to the same value. PF2 is `SCK`. PF3/_INT is unused.

**The hardware serial port is not in use.** The LC6554's serial interface is enabled
through the control register, and the only CTL bit this ROM ever touches is bit 0
(interrupt enable, set at `$02D`, `$0F5`, `$5B4` and cleared at `$572`). So PF0–PF3
are plain I/O and everything here is bit-banged.

**Clock timing.** The burst loop is 14 instruction cycles: `LDZ/LI/OP` plus two
`NOP`s for each phase, plus `LDZ/DEM/BNZ` for the counter. At Tcyc = 1 µs that is
**SCK ≈ 71 kHz**, low for ~5 µs and high for ~9 µs, and `TMP0` is preloaded with 8
so there are exactly **8 clock pulses** per burst.

**Transaction shape.**

```
$41C   port F = $6      SDATA pulled low, SCK high      <- start marker
       reg12  = 1
       reg14  = CDCMD_LO
       reg15  = CDCMD_HI
       reg13  = 8, 9, 8                                 <- strobe on bit 0
       8 x SCK, SDATA released high throughout
       reg13  = 0
$479   ~4.2 ms wait (two passes of $47B, each ~2.1 ms)
$451   port F = $7      SDATA released, SCK high        <- no start marker
       reg12  = 1
       reg13  = 0, 1, 0                                 <- strobe on bit 0
       8 x SCK
       port F = $7      leaves SCK high
$7CB   reg14 -> low nibble of the reply
       reg15 -> high nibble, masked to 3 bits
       -> $764 -> $700 table -> DISP4/DISP5
```

So: command out, ~4 ms turnaround, clock burst, two nibbles back. The reply is
7 bits, which is why the BCD table only needs 100 entries.

**What is unresolved.** `reg12`–`reg15` are the four port accesses that carry a
`BANK` prefix. During the 8-clock burst SDATA is released and U62 never samples
port F, so the payload is not moving through port F under firmware control — it
moves through those four registers. They behave as a small bidirectional file:
12 = control, 13 = strobe (bit 0 pulsed), 14 and 15 = data, written on the way out
and read on the way back.

Without the prefix those DPL values select ports M, N, O and P. That cannot be
right: `$7D5` masks the port-15 read with `#7`, keeping three bits, and port P has
a single pin. So `BANK` is redirecting the port decode to something the datasheet
does not describe, and the four registers are most likely an external interface
latch sitting between U62 and the drive. A scope on PF2 will show the 71 kHz
8-pulse burst every ~335 ms while a disc is loaded; whichever pins move in step
with it are the real reg12–reg15.

---

## Dead code audit

Four separate checks. The instruction stream comes out clean; the interesting
findings are all about capability left on the table rather than code left behind.

### Unreachable code — none

Recursive descent from the three entry points (`$000`, `$038`, `$03C`) reaches
1708 of 2032 programmed bytes. Every one of the remaining 324 is either one of the
six data tables or filler, and each filler run was tested by decoding it: none
produces a plausible instruction sequence, and none ends in an `RT`.

### Unreferenced routines — none

All 38 routines are reached. Every one except the three entry points has at least
one `CAL` or `JMP` referencing it, or is reached by fall-through from the routine
above. Twenty-one have exactly one caller, which is normal for a main loop that
polls each subsystem once.

### Dead stores — none

Six candidate pairs turned up on a linear scan, but all six are the two arms of an
`if`/`else` writing the same cell on alternative paths, not a value written twice
in straight-line code. After filtering by control flow the count is zero.

### Dead data

| Item | Status |
|---|---|
| `M($43)` `CDCMD_X` | **Written at `$611` and `$63E`, never read anywhere.** A vestigial third command byte. This is the only genuinely dead cell in RAM |
| `$03C` second interrupt vector | One byte, `RTI`. PF3/_INT is unconnected per the pinout, so the external source cannot fire; whether the serial source can depends on the `BANK` question |
| Font entries 14 and 15 (`'E'`, `'F'`) | Reachable only if the CD bus returns 14 or 15 in an unmasked digit. Present but probably never seen |
| BCD table indices 100–127 | The index is 7 bits and can express them; the table stops at 99. Out-of-range would read code at `$764` as font indices |
| Key return KI2 (PB2) | **Never read.** `$11C` masks the port B sample with `#3`, discarding the third return line. Four of the twelve matrix positions are wired but ignored |

### Unused CPU capability

Forty-five of roughly eighty instructions appear. Whole features are never touched:

- **All sixteen flag bits.** `SFB`, `RFB`, `BF`, `BNF` — the entire flag register is
  unused. Conditions are tested by masking with `AND` and branching on `BZ`/`BNZ`
- **Every bit-test branch.** `BA`, `BNA` (accumulator), `BM`, `BNM` (memory),
  `BP`, `BNP` (port). The same mask-and-branch idiom is used instead
- **Direct port bit set and reset.** `SPB`, `RPB` are never used; the firmware keeps
  a RAM shadow of each port and does read-modify-write through `SMB`/`RMB`
- **Timer and interrupt branches.** `BTM`, `BNTM`, `BI`, `BNI`
- **Both addition instructions.** `AD` and `ADC` are used zero times. There is no
  addition anywhere in this ROM — every counter moves by `INC` or `DEC`, and the
  two-nibble volume carries by explicit comparison
- **Decimal adjust.** `DAA`, `DAS` — the BCD conversion is done by table instead
- `CZP` zero-page call, `HALT` standby, `JPEA` computed jump, `SB` set bank,
  `CMA` complement, `STC` set carry, `CLI` compare DPL, and working registers
  A3, H1, L1

`HALT` being absent is worth a note: the LC6554's standby mode is never entered, so
U62 keeps running the 60 Hz display sweep even when it has switched the Amiga's
main logic off. `CM` (compare against RAM) appears exactly once.

The overall picture is a firmware written to a narrow, consistent idiom — load,
mask, branch on zero — rather than one exploiting the instruction set. That is
useful context for anyone writing a replacement: you need far less of the LC6500
than the datasheet suggests.

---

## Review pass, 12 September 2026 — corrections to earlier commentary

A line-by-line re-read of the listing against the ROM found these errors in my
own earlier annotation. `U62.asm` and `U62.pdf` are regenerated with all of them
fixed.

| Where | Was | Is |
|---|---|---|
| `$208` `@skip` branch | "power has just come up — restore the working volume" | It is the power-*lost* path: `ATTEN = $22` is full attenuation, silence |
| `$300` key labels | volume-down on the decrement path | Decrementing an attenuation index is **louder**: row 1 bit 1 is volume UP (CPCP 9), row 2 bit 1 is volume DOWN (CPCP 8) |
| `$133` in `f_ScanKeys` | "AND with the previous sample — two agreeing reads = debounced" | `TMP0` holds the *inverted* previous state, so this is `new AND NOT old`: a **rising-edge detector**. `KEY<row>_1` means "went down this pass", not "debounced" |
| `$05F` | reset asserted while the key is held | Fires on the press **edge** and produces a fixed ~470 ms pulse regardless of hold |
| `$642`–`$6A2` buttons 2 and 3 | tap fires on a fresh press | Tap fires on **release**, and only if the hold action has not fired and the key was held fewer than 10 passes |
| Hold action | "auto-repeats every third pass" | A **burst of three**: once when the scanner pulse arrives, then twice more three passes apart; the scanner re-arms it every 16 passes |
| `M($06)`, `M($07)` | "mode symbols" | `AMPM` (from RTC control F bit 2 and the H10 PM flag) and the blinking `COLON` (set on a seconds tick, cleared by the ISR after 256 ticks) |
| `M($0C)`–`M($0F)` | CD status flags | The colon timer and its enable |
| `M($59)` | `CDTIMEOUT` | `POLL_TICK` — passes until the next track query; a button press sets it to 8 so the track is re-read two passes later |
| `f_ShiftAttBit` `XA2` | "restore the caller's AC" | A2 parks the *rotated* value while port G is worked, then brings it back for the next bit |
| `f_PowerSymbol` `$77F` | a display helper | Its result is overwritten before anything reads it — a vestigial routine |
| Ports D/E, `$16A`, `$3B2`, `$200`, `$204`, `$2CE` | "CD bus" | The MSM6242B real-time clock (corrected earlier, now consistent throughout) |

Renamed symbols: `VOL_LO/HI → ATTEN_LO/HI`, `BTN2_PREV → KEY2_UP`,
`BTN4_LATCH → HOLD2_FIRED` (and the key-3 pair), `CDTIMEOUT → POLL_TICK`,
`DISP0–7 → HRS10 HRS1 MIN10 MIN1 TRK10 TRK1 AMPM COLON`, `BLINK → COLON_ON`.
