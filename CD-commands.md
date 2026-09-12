# Commands U62 sends to the CD drive

Sent as one byte over SDATA/SCK (PF1/PF2) to CN26, the CD-ROM interface
connector. The byte is `CDCMD_HI:CDCMD_LO`, loaded at `$41C` and clocked out as
eight bits at 71 kHz.

| Byte | Trigger in U62 | Reachable from the IR remote? |
|---|---|---|
| `$01` | key row 0 bit 0 | **yes** — CPCP 5 |
| `$06` | key row 1 bit 0 | **yes** — CPCP 6 |
| `$02` | key row 2 bit 0, fresh press | **yes** — CPCP 7 |
| `$04` | key row 3 bit 0, fresh press | **yes** — CPCP 4 |
| `$03` | key row 2 bit 0, held past the repeat threshold | **yes** — hold CPCP 7 |
| `$05` | key row 3 bit 0, held past the repeat threshold | **yes** — hold CPCP 4 |
| `$10` | idle poll, once every ten service passes (≈335 ms) | **no — firmware only** |

## The answer

**Exactly one command is not available from the remote: `$10`, the status poll.**

Everything else is, and for a structural reason. `f_ScanKeys` at `$121`–`$12D`
ORs `VKEY0`–`VKEY3` straight into the raw key bits before debouncing, so an IR
command and a button press are the same event by the time `f_TransportButtons`
sees them. That includes the two held variants: U75 asserts CPCP for as long as
the remote key is down, so the hold counter reaches its threshold of 10 and the
auto-repeat commands `$03` and `$05` fire exactly as they would from the panel.

`$10` is issued by `f_TransportButtons` itself when no button has been pressed for
ten passes. It is a query, not a transport command — the drive answers with a
7-bit value that `$764` turns into the two track digits.

## Command space

Only `$01`–`$06` and `$10` are ever sent. `$00`, `$07`–`$0F` and everything above
`$10` never appear. `CDCMD_HI` only ever holds 0 or 1. So the drive may well accept
commands this firmware never issues — worth probing if anyone gets a capture of a
CDTV talking to its drive.

## Not commands, but also not on the remote

- **The AUPLY pulse.** `$612`–`$624` pulls PI3 (CD Audio Play) low for about 4 ms
  before sending `$01`. It happens on that one button only, and it is a hardware
  handshake rather than anything on the serial link.
- **The real-time clock initialisation** at `$3B2`, which runs once at power-on.

---

# Correction: ports D and E are the real-time clock

I previously described ports D and E as a "CD bus". **They are not.** They are the
interface to **U61, an OKI MSM6242B real-time clock**, shared with the Amiga
through the U57/U59 buffers.

Evidence:

- The CDTV Service Manual glossary lists **`CLKRD/CLKWR — Real-time Clock
  Read/Write`**, and the schematic shows those signals buffered through U60.
- Schematic 252605 sheet 9 shows **U61 MSM6242B** with a 32.768 kHz crystal (X2),
  its D0–D3 and A0–A3 running both to the U57/U59 Amiga buffers and across to
  U62's ports D and E. `CA` is Clock Address, `CD` is Clock Data.
- The register numbers `f_ReadClock` uses are the MSM6242B map exactly: **5 = tens
  of hours, 4 = units of hours, 3 = tens of minutes, 2 = units of minutes, 0 =
  units of seconds, 15 = control register F**.
- `f_InitRTC` at `$3B2` is a textbook MSM6242 start-up: control F ← `$7`
  (RESET + STOP + 24-hour), then `$6` (reset released), clear registers 0–5,
  control D ← 0, then control F ← `$4` — STOP released, 24-hour mode — which
  starts the clock.
- That last write explains something that had bothered me. `$174` masks the first
  digit to two bits. In 24-hour mode the tens-of-hours digit is only ever 0, 1 or
  2, so two bits is exactly right. Under my earlier "CD time" reading the mask made
  no sense.

## What the front panel actually shows

| Buffer | Was | Is |
|---|---|---|
| `M($00)` | DISP0 | **HRS10** — tens of hours, blanked when zero |
| `M($01)` | DISP1 | **HRS1** — units of hours |
| `M($02)` | DISP2 | **MIN10** — tens of minutes |
| `M($03)` | DISP3 | **MIN1** — units of minutes |
| `M($04)` | DISP4 | **TRK10** — tens of the CD track number |
| `M($05)` | DISP5 | **TRK1** — units of the CD track number |
| `M($06)`, `M($07)` | DISP6, DISP7 | symbol positions, driven from the clock control register and the seconds tick |

So the panel is a **clock and a track counter**: the time of day comes from the
RTC over ports D and E, and the track number comes from the CD drive over
SDATA/SCK. Two independent sources, which is why there are two interfaces.

`M($0E)`/`M($48)` are not CD status as I had them — they are the previous and
current seconds digit, compared at `$1E2` to spot the tick. That is what drives
the blinking symbol on `M($07)`.

`U62.asm` and `U62.pdf` have been regenerated with the corrected names
(`f_ReadClock`, `f_InitRTC`, `f_ClockReadHigh`, `f_ClockReadLow`, `f_ClockWrite`)
and the corrected RAM symbols.
