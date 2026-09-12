# Amiga-CDTV-U62

## What is the U62?

The U62 is the Commodore CDTV's front-panel and system controller: a Sanyo
**LC6554H**, a 4-bit single-chip microcomputer with 4 KB of mask ROM, 256 nibbles
of RAM and fifteen 4-bit I/O ports, six of them high-voltage drivers for a vacuum
fluorescent display. It sits in a 64-pin socket (Commodore part 252608-01, socket
XU62) on the CD1000 main board.

Where the U75 handles everything that comes *in* from peripherals, the U62 runs the
machine's face. From the ROM it:

- sweeps the eight-digit VFD panel at 60 Hz, one digit per timer interrupt
- reads the time of day from the on-board **MSM6242B real-time clock** and shows it
  as HH:MM with a colon that blinks once a second, plus an AM/PM indicator if the
  Amiga has put the clock in 12-hour mode
- talks to the CD drive over a two-wire serial link, sends it transport commands,
  and polls it every ~335 ms for the track number shown on the panel
- scans the front-panel key matrix and debounces it
- sets the headphone volume by bit-banging an 18-bit word to a two-section
  attenuator, and draws the level as an eight-segment bar across the panel
- switches the Amiga's main logic power on and off, watching the Power Sense line
- arbitrates the genlock mode between the Amiga and the remote control
- pulses the Amiga's keyboard reset line from a front-panel key
- receives media-key commands from the U75 as a 4-bit code, and reports front-panel
  button presses back to it as a 3-bit code

The link to the U75 is parallel: four lines in (CPCP0–3, from U75 PB4–7)
and three lines out (AUS0–2, to U75 PB0/PB1/PB3). The U62 treats an incoming
command as a *virtual key press* — it ORs it into the key matrix before debouncing —
so a remote-control command and a front-panel button are the same event from that
point on. That one design choice explains most of how the two chips cooperate, and
is documented from both sides in this repository and in
[Amiga-CDTV-U75](https://github.com/Korinel/Amiga-CDTV-U75).

This is, as far as I know, the first public disassembly of the LC6554H firmware.
The immediate purpose is a **front-panel replacement** for CDTVs whose original panel 
or controller has failed.

---

## An acknowledgement to CDTV Land

This project exists because CDTV Land dumped the LC6554H — alongside the 6500/1 —
from a pre-production CD1000 prototype fitted with EPROM piggyback boards, in June
2022. The EPROM was an MBM27C64 on a DIP-28 adaptor, and its image is
`U62-ROM-dump.csv` in this repository. The ROM identifies itself, in plain ASCII at
offset `$1100`, as `LC6554H`, `VER 1.20`, dated `26-09-1990`.

---

## Files in this repository

| File | Description |
|---|---|
| `U62.asm` | Fully annotated listing. Every line carries its ROM address and raw bytes, so any claim can be checked against the dump. Written to be read, not assembled. |
| `U62.pdf` | The same listing as a colour reference document, grouped by subsystem, with the data tables decoded — including the font rendered as seven-segment glyphs. |
| `U62-ROM-dump.csv` | CDTV Land's EPROM image as a CSV (1024 rows × 9 columns: address + 8 data bytes). Program is `$0000`–`$07EF`; `$0800`–`$0FFF` is unprogrammed; `$1000` holds the mask-option bytes and `$1100` the ASCII identification block, neither of which the MCU can address. |
| `LC6500-opcodes.csv` | The 80-instruction LC6500-series opcode map, transcribed from the Sanyo LC6554D/H datasheet (EN 2156B, pp. 24–26), one row per opcode. |
| `lc6500dis.py` | A disassembler for that instruction set, with a recursive-descent tracer. Reaches 1708 of the 2032 programmed bytes with no undefined opcode at any instruction boundary; the remainder is data tables and filler. |
| `U62-memory-map.md` | RAM map, port map, the decoded tables, timing derivations, and a log of every correction made during review. |
| `BANK-conundrum.md` | The one thing in this ROM that is not settled — see below — with every data point, the competing hypotheses, and the scope test that would decide it. |
| `CD-commands.md` | The seven bytes the U62 ever sends to the CD drive, and which of them the remote can reach. |


---

## Did we learn anything?

Quite a lot, since nothing about this chip had been documented.

- **The panel is a clock.** Four of the eight digits show the time of day from the
  MSM6242B, two show the CD track number, and the remaining two are the blinking
  colon and an AM/PM indicator. The RTC is shared with the Amiga.
- **Only the remote can switch the power.** No front-panel key reaches the POWER
  output; it toggles solely on a U75 command. CD/TV, by contrast, works from both.
- **A third of the key matrix is never read.** Twelve positions are wired, the
  firmware masks the third return line off and uses eight.
- **The remote can only tap the transport keys.** The U62 needs a virtual key held
  for ten of its 33.5 ms passes before the scan action fires; the U75 asserts a
  command once per IR frame and clears it within 56 ms. So scan is front-panel only.
- **A latent command.** The U62 accepts a code that pulses the Amiga's keyboard
  reset line — and the U75 firmware can never send it.
- **Nothing is hidden.** Every unreached byte was tested for orphaned code; there is
  none. No service mode, no unlock combination, one dead RAM cell.
- **The firmware uses 45 of 80 instructions.** No addition at all — every counter
  moves by increment and decrement — and none of the chip's sixteen flag bits.

### The one open question

Three routines prefix a port access with the `BANK` instruction, which the datasheet
says only affects a following jump. One of them *reads* through that prefix from a
port that is output-only, and keeps three bits from a port that has one pin. The
best-fitting explanation is that `BANK` selects the LC6554's own serial-interface
registers — the datasheet shows them in the block diagram but gives no instruction
for them — and the released data lines during the clock burst support that. It is
not proven. `BANK-conundrum.md` has everything, and one oscilloscope capture on the
CD-ROM connector's SCK line would settle it. If you have the *LC6554 Series User's
Manual* (Sanyo No. E21B, December 1987), it would settle it faster.

---

## Related projects

[**Amiga-CDTV-U75**](https://github.com/Korinel/Amiga-CDTV-U75) — the other half of
the front panel: the 6500/1 that decodes the IR remote, the wired peripherals and
the IR keyboard, and exchanges media keys and button events with this chip.

[**Amiga-CDTV-Brick**](https://github.com/Korinel/Amiga-CDTV-Brick) — RP2040 firmware
that reads physical joysticks and transmits CDTV-compatible IR frames.
