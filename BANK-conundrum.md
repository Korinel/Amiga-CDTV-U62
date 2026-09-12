# The BANK conundrum — complete evidence

Everything the ROM, the datasheet and the schematic say about the `$FD` `BANK`
instruction in the CDTV U62 firmware. Nothing here is summarised away; the raw
bytes are included so every claim can be checked by hand.

---

## 1. The question, stated precisely

Three routines prefix a port access with `BANK`. The datasheet says `BANK` only
affects a following `JMP`, and none of these routines contains a `JMP`. Yet the
port accesses behind that prefix cannot be doing what the port map says they do.

**What is `BANK` actually switching?**

---

## 2. Complete inventory

`$FD` appears **13 times in the whole 8 KB image**. Every one is a decoded
instruction — none is an operand byte or table data.

| Address | Routine | What immediately follows |
|---|---|---|
| `$421` | `$41C` | `61` `OP` with DPL = 12 |
| `$427` | `$41C` | `61` `OP` with DPL = 14 |
| `$42D` | `$41C` | `61` `OP` with DPL = 15 |
| `$431` | `$41C` | `61` `OP` with DPL = 13 |
| `$435` | `$41C` | `61` `OP` with DPL = 13 |
| `$439` | `$41C` | `61` `OP` with DPL = 13 |
| `$44E` | `$41C` | `61` `OP` with DPL = 13 |
| `$456` | `$451` | `61` `OP` with DPL = 12 |
| `$45A` | `$451` | `61` `OP` with DPL = 13 |
| `$45E` | `$451` | `61` `OP` with DPL = 13 |
| `$462` | `$451` | `61` `OP` with DPL = 13 |
| `$7CC` | `$7CB` | `0C` `IP` with DPL = 14 |
| `$7D1` | `$7CB` | `0C` `IP` with DPL = 15 |

**The pattern is exact and without exception.** `BANK` is always immediately
preceded by `LDZ #n` with n in 12–15, and immediately followed by `OP` or `IP`.
It never appears anywhere else, and no `JMP` follows any of them.

---

## 3. The three routines, byte for byte

### `$41C` — send a command

```
41C: 85 C6 61 C1 8C FD 61 81 44 21 8E FD 61 82 44 21 8F FD 61 C8 8D FD 61
     C9 8D FD 61 C8 8D FD 61 89 C8 02 85 C3 61 00 00 85 C7 61 00 00 89 2F
     3E 3E C0 8D FD 61 62
```

```
$41C  85 C6 61     LDZ #5, LI #6, OP     port F = %0110   SI low, SO high, SCK high
$41F  C1           LI  #1
$420  8C FD 61     LDZ #12, BANK, OP     reg12 <- 1
$423  81 44 21     LDZ #1, LHI #4, L     AC = CDCMD_LO   M($41)
$426  8E FD 61     LDZ #14, BANK, OP     reg14 <- CDCMD_LO
$429  82 44 21     LDZ #2, LHI #4, L     AC = CDCMD_HI   M($42)
$42C  8F FD 61     LDZ #15, BANK, OP     reg15 <- CDCMD_HI
$42F  C8 8D FD 61  LI #8,  LDZ #13, BANK, OP    reg13 <- 8
$433  C9 8D FD 61  LI #9,  LDZ #13, BANK, OP    reg13 <- 9
$437  C8 8D FD 61  LI #8,  LDZ #13, BANK, OP    reg13 <- 8
$43B  89 C8 02     LDZ #9, LI #8, S      M($09) = 8, the pulse counter
$43E  85 C3 61     LDZ #5, LI #3, OP     port F = %0011   SCK low
$441  00 00        NOP, NOP
$443  85 C7 61     LDZ #5, LI #7, OP     port F = %0111   SCK high
$446  00 00        NOP, NOP
$448  89 2F        LDZ #9, DEM           count down
$44A  3E 3E        BNZ $43E              loop, 8 times total
$44C  C0           CLA
$44D  8D FD 61     LDZ #13, BANK, OP     reg13 <- 0
$450  62           RT
```

### `$451` — second phase

```
451: 85 C7 61 C1 8C FD 61 C0 8D FD 61 C1 8D FD 61 C0 8D FD 61 89 C8 02
     85 C7 61 00 00 85 C3 61 00 00 89 2F 3E 67 85 C7 61 62
```

```
$451  85 C7 61     LDZ #5, LI #7, OP     port F = %0111   SI, SO released, SCK high
$454  C1 8C FD 61  LI #1, LDZ #12, BANK, OP     reg12 <- 1
$458  C0 8D FD 61  CLA,   LDZ #13, BANK, OP     reg13 <- 0
$45C  C1 8D FD 61  LI #1, LDZ #13, BANK, OP     reg13 <- 1
$460  C0 8D FD 61  CLA,   LDZ #13, BANK, OP     reg13 <- 0
$464  89 C8 02     LDZ #9, LI #8, S      pulse counter = 8
$467  85 C7 61     LDZ #5, LI #7, OP     SCK high
$46A  00 00        NOP, NOP
$46C  85 C3 61     LDZ #5, LI #3, OP     SCK low
$46F  00 00        NOP, NOP
$471  89 2F 3E 67  LDZ #9, DEM, BNZ $467        loop, 8 times
$475  85 C7 61     LDZ #5, LI #7, OP     SCK left high
$478  62           RT
```

Note the phase difference: `$41C` drops SCK first, `$451` raises it first, and
`$451` leaves the line high on exit.

### `$7CB` — read the reply

```
7CB: 8E FD 0C 8A 02 8F FD 0C 89 02 C7 E7 02 AF 64 62
```

```
$7CB  8E FD 0C     LDZ #14, BANK, IP     AC <- reg14
$7CE  8A 02        LDZ #10, S            M($0A) = TMP1, the low nibble
$7D0  8F FD 0C     LDZ #15, BANK, IP     AC <- reg15
$7D3  89 02        LDZ #9,  S            M($09)
$7D5  C7 E7 02     LI #7, AND, S         M($09) = TMP0, masked to three bits
$7D8  AF 64        CAL $764
$7DA  62           RT
```

---

## 4. The register model — inputs and outputs

Four addresses are reachable only behind the `BANK` prefix.

| Reg | Written | Read | Values seen |
|---|---|---|---|
| **12** | `$422`, `$457` | never | always `1` |
| **13** | `$432`, `$436`, `$43A`, `$44F`, `$45B`, `$45F`, `$463` | never | `$41C`: 8, 9, 8 … 0. `$451`: 0, 1, 0. **Bit 0 pulses low-high-low in both; bit 3 is set throughout in `$41C` and clear in `$451`** |
| **14** | `$428` | `$7CD` | out: `CDCMD_LO`. in: low nibble of the reply |
| **15** | `$42E` | `$7D2` | out: `CDCMD_HI`. in: high nibble, masked to 3 bits |

Registers 14 and 15 are **bidirectional** — the same address carries the command
out and the reply back.

### What goes out

`CDCMD_HI:CDCMD_LO` forms one byte. Every value the firmware ever sends:

| Trigger | CDCMD_HI | CDCMD_LO | Byte | AUS code to U75 |
|---|---|---|---|---|
| key row 0 bit 0 | 0 | 1 | `$01` | 10 |
| key row 1 bit 0 | 0 | 6 | `$06` | 6 |
| key row 2 bit 0, fresh press | 0 | 2 | `$02` | 3 |
| key row 3 bit 0, fresh press | 0 | 4 | `$04` | 14 |
| key row 2 bit 0, held | 0 | 3 | `$03` | 11 |
| key row 3 bit 0, held | 0 | 5 | `$05` | 7 |
| idle, every 10 service passes | 1 | 0 | `$10` | — |

So `$0n` is a transport command and `$10` is a status query. Nothing else is sent.

### What comes back

`reg15:reg14` is read as a 7-bit value (reg15 masked to 3 bits) and handed to
`$764`, which uses it to index the BCD table at `$700`. The two resulting font
indices go to `DISP4` and `DISP5` — the **track number** on the front panel, 0–99
with the leading zero blanked.

---

## 5. Timing

`Tcyc` = 1 µs (4 MHz ceramic resonator, 1/1 predivider, LC6554H datasheet Table 2).

| Phase | Cycles | Time |
|---|---|---|
| `$41C` setup, `$41C`–`$43D` | 35 | 35 µs |
| 8 SCK pulses, loop body 14 cycles | 112 | 112 µs |
| `$41C` tail | 5 | 5 µs |
| `$479` delay — two passes of `$47B` | ~4192 | **4.19 ms** |
| `$451` | ~132 | 132 µs |
| `$7CB` + `$764` | ~40 | 40 µs |
| **Whole transaction** | | **≈ 4.5 ms** |

SCK: low 5 µs, high 9 µs, period 14 µs → **71.4 kHz**, exactly 8 pulses.

The transaction runs once per button press, and once every ten service passes
(≈ 335 ms) when idle.

**Interrupts are enabled throughout.** `SCTL $1` is set at `$02D` and re-set at the
end of every ISR (`$0F5`). The only routine that ever clears it is `$546`, the
attenuator bit-banger. Neither `$41C`, `$451` nor `$7CB` disables interrupts. With
an ISR period of 2096 µs, **at least two timer interrupts fire between writing
reg14/reg15 at `$428`/`$42E` and reading them at `$7CD`/`$7D2`.**

---

## 6. What the datasheet says

From the LC6554D/H instruction set table, Sanyo EN 2156B, page 25:

| Mnemonic | Code | Bytes | Cycles | Function | Remarks |
|---|---|---|---|---|---|
| `BANK` | `1111 1101` = `$FD` | 1 | 1 | PC11 ← ~PC11 | "The bank is changed" / effective immediately before `JMP` |
| `SB` | `0110 01 l1 l0` | 1 | 1 | PC12, PC11 ← l1, l0 | "Applicable only to LC6595" |
| `JMP` | `0110 1 P10P9P8` + `P7..P0` | 2 | 2 | PC ← PC11 (or ~PC11) P10…P0 | "If the BANK and JMP instructions are executed consecutively, PC11 is complemented" |

I re-checked the `BANK` opcode against the scan at high magnification. It is `$FD`.
There is no ambiguity.

The pin description for ports K–P lists only: *4-bit output (OP instruction),
single-bit decision (BP, BNP), single-bit set/reset (SPB, RPB)*. **`IP` is not
listed for ports K–P at all.** `IP` is documented only for ports A, B (input) and
C–J (input/output).

The datasheet's 80-instruction table contains **no instruction for loading or
reading the serial shift register**, even though the block diagram shows a 4/8-bit
serial shift register and two serial mode registers, and the features list says
"Serial input/output interface × 1 (4 bit/8 bit program-selectable)".

---

## 7. What the schematic says

CDTV schematic 252605 Rev A, sheet 9 of 12:

- **PL0–3 (pins 56–59) → Sa–Sd**, **PM0–3 (60–63) → Se–Sh**, **PN0–3 (1–4) → G1–G4**,
  **PO0–3 (5–8) → G5–G8**. All route through RP23/RP24/RP26 to CN15 and CN18, the
  vacuum-fluorescent display connectors. **Nothing else is on those pins.**
- **PP0 (pin 9)** goes via RP22 (4.7 k, drawn dashed — possibly not fitted) and
  R142 (1 k) off-sheet, and to U80 pin 2.
- **PF0/SI (35), PF1/SO (36), PF2/SCK (37) → CN26, "CDROM INTERFACE CD AUDIO"**.
  PF3/_INT is unused.
- U74 and U80 are **74LS08** quad AND gates; U60 is a **74LS244** buffer; U73 and
  U48 are 74LS32; U58 is 74LS04. None of them is a latch or a register file.
- The parts list gives U62 as Commodore part **252608-01, CPU LC6554H**, in a
  socket (**XU62, 390141-01, 64-pin SDIP**).

---

## 8. Four independent reasons `BANK` cannot be a no-op

If `BANK` did nothing, DPL 12–15 would select ports M, N, O and P.

**8.1 — `IP` on an output-only port.** `$7CD` and `$7D2` read DPL 14 and 15. Ports
O and P are output-only, high-voltage P-channel open drain. The datasheet does not
define `IP` for them.

**8.2 — Port P has one pin, but three bits are kept.** `$7D5` masks the DPL-15 read
with `#7`, preserving three bits, and `$764` shifts that value left four places as
the high nibble of a 0–99 index. Port P is `PP0` — a single bit.

**8.3 — The display ISR would destroy the data.** The timer ISR writes port N at
`$09F` and `$0CA`, and port O at `$0A1` and `$0CD` — four writes every 2096 µs. The
`$479` delay alone guarantees two full ISR cycles between the writes at
`$428`/`$42E` and the reads at `$7CD`/`$7D2`. If reg14 were port O, the value read
back would be a grid mask, not a track number, and the BCD table would produce
nonsense on the panel. The firmware does not disable interrupts here, even though
`$546` demonstrates the author knew how to when it mattered.

**8.4 — The same DPL is used both ways.** `$200` and `$204` write DPL 15 **without**
`BANK` to pulse PP0, the CD bus strobe used by `f_ReadCDPanel`. `$42E` writes DPL 15
**with** `BANK`. One DPL value, two prefixes, two unrelated purposes.

Every port access in the ROM with DPL 10–15:

```
without BANK:  $09F N   $0A1 O   $0B0 L   $0BF M   $0CA N   $0CD O
               $202 P   $206 P   $25E K   $26C K   $39E K   $3B4 P
with BANK:     $422 12  $428 14  $42E 15  $432 13  $436 13  $43A 13
               $44F 13  $457 12  $45B 13  $45F 13  $463 13
               $7CD 14 (IP)      $7D2 15 (IP)
```

---

## 9. Hypotheses

### H1 — `BANK` selects a second I/O bank containing the serial interface registers

**This is my leading hypothesis and it fits every observation.**

The LC6554 has a hardware serial interface — a 4/8-bit shift register plus mode
registers, shown in the block diagram — and the instruction set contains **no way
to load or read it**. Something must address those registers. A second I/O bank
selected by the `BANK` flip-flop would do it, and would explain why the mechanism
is undocumented in a device datasheet that refers you to the *LC6554 Series User's
Manual* for detail.

Under this reading:

| Reg | Role |
|---|---|
| 12 | serial mode register — written 1 to enable |
| 13 | serial control; bit 0 pulsed low-high-low to trigger, bit 3 selects direction or word length |
| 14 | shift register, low nibble, bidirectional |
| 15 | shift register, high nibble, bidirectional |

It also explains the otherwise odd detail that **the data lines are held high
during the entire clock burst**. `LI #3` and `LI #7` both set PF0 and PF1 to 1.
These are open-drain pins, so writing 1 *releases* them — which is exactly what you
do to let the internal serial hardware drive SO and sample SI while you supply the
clock manually on PF2. The firmware never reads port F during the burst because it
does not need to: the shift register captures SI on its own, and `$7CB` reads the
result out afterwards.

The bit-banged clock is then not a bodge but a deliberate choice — the serial block
configured for external SCK, with U62 supplying the edges through the port latch so
it can control the exact timing the CD drive expects.

### H2 — reading an output port returns the pin state, and `BANK` really is inert

Ports K–P are open drain with a pull-down. An external device could pull PO and PP
low and `IP` might return the pin level. This survives objection 8.1 but fails
8.2 (port P has one pin, three bits are kept), 8.3 (the ISR overwrites port O
between write and read) and 8.4 (DPL 15 is used both ways).

### H3 — the code was written for the LC6595 evaluation chip

The datasheet's development tools list the **LC6595** evaluation chip and the
**LC65PG54** piggyback, and `SB` is marked "applicable only to LC6595" — so at
least one relative of this part does have real bank switching. A universal
evaluation chip covering EVA-TB6520/22/54/43/46 would plausibly need a bank bit to
select between different family members' port sets.

Against it: the parts list shows production CDTVs carry a mask **LC6554H**, and this
firmware is what runs in them. Whatever `BANK` does, it has to work on the real part.

### H4 — undocumented instructions

Six opcodes are undefined in the datasheet table: `$2D`, `$E2`, `$E3`, `$ED`, `$F2`,
`$F3`. None appears in this ROM. If any of them were the serial access instruction,
the author did not use it. Worth noting but it does not explain the `BANK` prefix.

---

## 10. What to measure

The transaction is easy to trigger and easy to catch.

**Trigger:** with a disc loaded and no button pressed, the status poll runs every
≈ 335 ms on its own. Pressing a transport button fires one immediately.

**Signature to trigger on:** PF2 (pin 37, SCK) — eight pulses at 71 kHz, low 5 µs,
high 9 µs. Then a 4.19 ms gap, then eight more.

**Test 1 — settle H1 vs H2 in one capture.** Scope PF2 as trigger, and PO0–3
(pins 5–8) and PP0 (pin 9) on the other channels.

- If PO/PP show only the 60 Hz display multiplex and nothing correlated with the
  SCK burst → the accesses are internal. **H1 confirmed, H2 dead.**
- If PO/PP carry the command nibbles in step with the burst → H2 lives, and the
  display is being disturbed in a way we would then need to explain.

**Test 2 — find where the data actually goes.** If Test 1 says internal, watch
PF1/SO (pin 36) during the burst. Under H1 the shift register drives it with the
command bits `$01`, `$06`, `$02`, `$04`, `$03`, `$05` or `$10`. If SO stays high
throughout, H1 is wrong too and the payload is going somewhere we have not found.

**Test 3 — the reply.** Watch PF0/SI (pin 35) during the second burst (`$451`).
Under H1 the CD drive drives the track number onto it. Compare the byte you capture
against what the panel then displays — the BCD table at `$700` makes the mapping
exact and checkable.

**Test 4 — the start marker.** `$41C` begins by writing `%0110` to port F, which
pulls PF0 low while PF1 and PF2 stay high. `$451` does not. Confirm the low pulse
on pin 35 at the start of the first burst only.

---

## 11. Context that would settle it

- **The LC6554 Series User's Manual, No. E21B (December 1987).** The device
  datasheet defers to it, and it is where the serial interface programming model
  will be described. This is the single document that would end the discussion.
- **The EVA-800 · LC6554 Series Development Tool Manual**, or the CP/M-80 or MS-DOS
  cross-assembler (`LC6554D.COM` / `LC6554H.COM`). The assembler's syntax for a
  serial-register access would name the mechanism.
- **Anyone with a Sanyo LC65xx-based product already reverse engineered.** The same
  idiom — `LDZ #n` / `BANK` / `OP` with n ≥ 12 — appearing in another LC6500 ROM
  would confirm it is a family-wide convention rather than something specific here.
- **What is on the other end of CN26.** The CD-ROM interface connector carries
  SDATA and SCK. The drive's own controller and its command set would tell us
  whether `$01`–`$06` and `$10` match a known protocol.
