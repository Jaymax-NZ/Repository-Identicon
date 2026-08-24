# Emoji colour-square reference — per-vendor samples and a developer-weighted average

Generated 2026-08-23. Self-contained: every number below is either sampled from a
named artefact or derived by the script in [§7](#7-reproduction).

**Scope** — the nine Unicode "large square" emoji:
`🟥 U+1F7E5` · `🟧 U+1F7E7` · `🟨 U+1F7E8` · `🟩 U+1F7E9` · `🟦 U+1F7E6` ·
`🟪 U+1F7EA` · `🟫 U+1F7EB` · `⬛ U+2B1B` · `⬜ U+2B1C`

---

## Contents

- [1. Headline result](#1-headline-result)
- [2. Per-vendor sampled colours](#2-per-vendor-sampled-colours)
- [3. Sampling method](#3-sampling-method)
- [4. Averaging method](#4-averaging-method)
- [5. The weighting model](#5-the-weighting-model)
  - [5.1 Why surfaces, not operating systems](#51-why-surfaces-not-operating-systems)
  - [5.2 Population inputs](#52-population-inputs)
  - [5.3 Forward-looking adjustments](#53-forward-looking-adjustments)
  - [5.4 The case for two Microsoft rows](#54-the-case-for-two-microsoft-rows)
  - [5.5 Final weights](#55-final-weights)
- [6. Sensitivity and known gaps](#6-sensitivity-and-known-gaps)
- [7. Reproduction](#7-reproduction)

---

## 1. Headline result

Weighted mean per block, baseline weights from [§5.5](#55-final-weights).

| block | glyph | **weighted mean** | unweighted mean (7 sets) |
|---|---|---|---|
| red | 🟥 | `#E43B3F` | `#E5363B` |
| orange | 🟧 | `#FD8526` | `#F88122` |
| yellow | 🟨 | `#FDC139` | `#FECA3C` |
| green | 🟩 | `#53BC53` | `#64C158` |
| blue | 🟦 | `#277EE2` | `#409AEB` |
| purple | 🟪 | `#A655D7` | `#A262D7` |
| brown | 🟫 | `#985D4A` | `#905943` |
| black | ⬛ | `#29282A` | `#28292C` |
| white | ⬜ | `#E0DBE4` | `#EBE9EF` |

- **Caveat on ⬜ white** — the weighted value carries a visible lilac cast, inherited
  entirely from Microsoft's Fluent 3D asset (a `#F6E8FF → #BBA4D2` vertical gradient).
  That is a faithful average, but it is probably not what you want as a token.
  For ⬜ prefer a neutral `#E4E4E4`, and for ⬛ prefer `#292929`.
  See [§6](#6-sensitivity-and-known-gaps).
- **Caveat on 🟥 red** — likewise pulled slightly magenta by Fluent 3D's
  `#D84278 → #D83954` gradient. `#E43B3F` is defensible; `#E03A34` is the value if you
  exclude Fluent 3D entirely.

---

## 2. Per-vendor sampled colours

Every cell below is a measured pixel value, not recalled from memory.
Provenance per column in [§3](#3-sampling-method).

| block | apple | noto | ms2d | ms3d | twemoji | facebook | openmoji |
|---|---|---|---|---|---|---|---|
| red 🟥 | `#D83421` | `#F44336` | `#F8312F` | `#D83D65` | `#DD2E44` | `#FA2E2F` | `#D22F27` |
| orange 🟧 | `#FF9317` | `#FF9800` | `#FF6723` | `#F66343` | `#F4900C` | `#FC9002` | `#E27022` |
| yellow 🟨 | `#F9C814` | `#FFCC32` | `#FFB02E` | `#FFAE53` | `#FDCB58` | `#FEDB3B` | `#FCEA2B` |
| green 🟩 | `#15B714` | `#7CB342` | `#00D26A` | `#49C48A` | `#78B159` | `#44C966` | `#B1CC33` |
| blue 🟦 | `#1A6BF3` | `#1976D2` | `#00A6ED` | `#407FD6` | `#55ACEE` | `#3CAAFB` | `#92D3F5` |
| purple 🟪 | `#BF42FF` | `#AB47BC` | `#C790F1` | `#7049BB` | `#AA8ED6` | `#9B3BFB` | `#8967AA` |
| brown 🟫 | `#81502F` | `#B76D54` | `#A56953` | `#815258` | `#C1694F` | `#6E4528` | `#6A462F` |
| black ⬛ | `#151514` | `#424242` | `#000000` | `#423C48` | `#31373D` | `#30323C` | `#3F3F3F` |
| white ⬜ | `#D9D9D9` | `#E0E0E0` | `#FFFFFF` | `#D9C6E9` | `#E6E7E8` | `#F9FCFF` | `#FFFFFF` |

- **Column key**
  - `apple` — Apple Color Emoji. Surfaces: macOS, iOS, iPadOS; also Slack, which has
    historically shipped Apple imagery on every platform rather than deferring to the OS.
  - `noto` — Google Noto Color Emoji. Surfaces: Android (non-Samsung), ChromeOS,
    most Linux desktops.
  - `ms2d` — Microsoft **Fluent 2D**. Surface: Windows 11 from the Nov 2021 update
    (build 22000.346) through the 3D rollout.
  - `ms3d` — Microsoft **Fluent 3D** (hybrid COLR font). Surface: Windows 11, broadly
    from 2025. See [§5.4](#54-the-case-for-two-microsoft-rows).
  - `twemoji` — Twemoji. Surfaces: Discord, X/Twitter web, and a long tail of web apps
    that substitute sprites rather than trusting the platform font.
  - `facebook` — Meta. Included for reference; excluded from the weighted average
    (not a developer surface).
  - `openmoji` — OpenMoji. Same: reference only, zero weight.

- **Not sampled** — Samsung One UI, WhatsApp, JoyPixels, Huawei. See
  [§6](#6-sensitivity-and-known-gaps).

---

## 3. Sampling method

- **Artefact sources** (all fetched from allow-listed hosts, no manual transcription)
  - `apple`, `noto`, `twemoji`, `facebook` — `emoji-datasource-{apple,google,twitter,facebook}@16.0.0`
    from the npm registry; the `img/<set>/64/<codepoint>.png` assets. This is the
    iamcal/emoji-data corpus.
  - `openmoji` — `hfg-gmuend/openmoji`, `color/618x618/<CODEPOINT>.png` from
    `raw.githubusercontent.com`.
  - `ms2d` — `microsoft/fluentui-emoji`, `assets/<Name>/Flat/<name>_flat.svg`.
    These squares are a single `<path>` with a literal `fill="#RRGGBB"`, so the value
    is read directly from the source, not rasterised.
  - `ms3d` — same repo, `assets/<Name>/Color/<name>_color.svg`. These are a `<path>`
    filled with a `linearGradient` inside an inner-shadow `<filter>`; rasterised with
    `cairosvg` at 256×256, then sampled.

- **Sample region** — central 40% × 40% of the glyph box, pixels with `alpha > 200`,
  arithmetic mean of R, G, B in 8-bit sRGB.
  - Rationale: the squares have rounded corners and antialiased edges; a whole-image
    mean would blend the transparent surround into the result.
  - The inner-shadow filters on the Fluent 3D assets act within roughly 2px of the
    edge at 32px design size, i.e. well outside the sampled core.

- **Known method limitation** — for the gradient-filled designs (Apple, Facebook,
  Fluent 3D) this yields the **centre** colour, which is close to but not identical to
  the whole-face perceptual mean. For the flat designs (Noto, Fluent 2D, Twemoji,
  OpenMoji) the two are the same by construction.

---

## 4. Averaging method

- Averaging is done in **Oklab**, not sRGB.
  - sRGB is gamma-encoded, so a naive channel mean lands darker and less saturated than
    the perceptual midpoint. The effect is worst where the inputs are far apart in hue,
    which here is green (`#15B714` vs `#B1CC33`) and purple (`#7049BB` vs `#C790F1`).
  - Pipeline: sRGB → linear → LMS → cube root → Oklab → weighted mean of `(L, a, b)`
    → inverse → clamp to sRGB gamut.
- Weights apply in Oklab space, so a vendor's weight is a weight on its perceptual
  position, not on its raw byte values.

---

## 5. The weighting model

### 5.1 Why surfaces, not operating systems

The question "what colour does a reader see" is answered by the **font that resolved the
glyph**, which is not a 1:1 map to OS:

- macOS and iOS collapse to one font (Apple Color Emoji) — so they must not be counted
  as two independent weights.
- Linux and Android also largely collapse to one font (Noto Color Emoji) — with Samsung
  as the significant exception.
- Windows is the reverse case: **one OS, two live fonts**, because the Segoe UI Emoji
  designs were replaced twice. See [§5.4](#54-the-case-for-two-microsoft-rows).
- A meaningful slice of reading happens inside apps that override the platform font
  entirely — Discord and X substitute Twemoji sprites regardless of OS.

So the model weights **font families**, and OS shares are only an input to deriving them.

### 5.2 Population inputs

- **Desktop developer OS**, anchored on the Stack Overflow Developer Survey 2025
  (~49,000 respondents, 177 countries): Windows 56.7% personal / 49.5% professional,
  macOS ~32.7%, Ubuntu 27.8% as the leading Linux distribution.
  - These are **multi-select** figures and sum well past 100%, so they cannot be used as
    shares directly. They establish *ordering and rough ratio*, not proportions.
  - Linux is fragmented across distributions in the survey while Windows and macOS are
    not, which systematically understates Linux if you read any single row as a share.
  - Normalised for this model to **Windows 45 / macOS 30 / Linux 25**. Windows is
    discounted from its raw 56.7% because the professional figure is materially lower
    and because WSL users partly read output in a Linux-font context.

- **Mobile**, same survey: Android personal use jumped 17.9% → 29.1% between 2024 and
  2025, overtaking Ubuntu for the first time — reported as the largest single-year OS
  gain in the survey's history. iOS/iPadOS sit lower among developers than in the
  general population.
  - Normalised to **Android 55 / iOS 45** — closer to parity than consumer market share,
    because developer iOS penetration runs above the global average.

### 5.3 Forward-looking adjustments

You asked for near-trend, not today. Three trends are applied:

- **Mobile share of reading rises.** Cloud agent sessions and phone-linked sessions mean
  more repo output is read on a handset. Modelled at **20% of all reads**, up from a
  today-figure closer to 10%.
  - This is the softest number in the model. It is also, per
    [§6](#6-sensitivity-and-known-gaps), nearly irrelevant to the answer.
- **Fluent 3D displaces Fluent 2D.** Windows 11 auto-updates and the 3D set was rolling
  out broadly through 2025. Modelled at **70% 3D / 30% 2D** of the Windows slice.
- **Windows 10 legacy Segoe is zero-weighted.** Its last emoji update was the May 2019
  Update (Emoji 12.0 era), and Windows 10 reached end of support in October 2025.
  A three-year-forward model should not carry it. It is also the one set I could not
  sample from a redistributable source, so excluding it removes a guess rather than
  discarding data.

### 5.4 The case for two Microsoft rows

You asked whether the case is strong enough. It is — but not for the split you might
expect. The interesting split is not *Windows 10 vs Windows 11*; it is
*Fluent 2D vs Fluent 3D*, both of which are Windows 11.

- **The designs are genuinely distinct, not a refresh.** For the red square:
  Fluent 2D is a flat `#F8312F`; Fluent 3D is a `#D84278 → #D83954` vertical gradient —
  a different hue family, not a shade adjustment. Purple moves further still:
  `#C790F1` (light lilac) → `#7049BB` (deep violet). Averaging these two into one
  "Microsoft" row would produce a colour that no Windows user has ever seen.
- **Both are in the field simultaneously.** The Fluent 2D designs shipped in Segoe UI
  Emoji with the Windows 11 November 2021 update; the 3D hybrid font began replacing
  them broadly during 2025. Rollout across a Windows fleet is not instantaneous, so a
  2026 model has to carry both.
- **Rendering is inconsistent even within one machine.** Apps using DirectWrite pick up
  the updated font while others fall back to older glyphs, so the split is not cleanly
  per-device.
- **Therefore**: two rows, `ms2d` and `ms3d`, with the Windows slice divided 30/70 in
  favour of 3D and the ratio trending further toward 3D over the model horizon.

**Confidence note.** The `ms3d` values come from the `fluentui-emoji` repo's Color SVGs,
which are the design source for the 3D set. Whether the shipped COLRv1 hybrid font
renders byte-identically to those SVGs is unverified. Treat `ms3d` as the least certain
column, and note that it is the column driving both caveats in
[§1](#1-headline-result).

### 5.5 Final weights

| set | weight | derivation |
|---|---|---|
| `apple` | **0.31** | 0.80 desktop × 0.30 macOS + 0.20 mobile × 0.45 iOS |
| `noto` | **0.29** | 0.80 × 0.25 Linux + 0.20 × 0.55 Android |
| `ms3d` | **0.24** | 0.80 × 0.45 Windows, × 0.70 3D share |
| `ms2d` | **0.10** | 0.80 × 0.45 Windows, × 0.30 2D share |
| `twemoji` | **0.06** | flat carve-out for sprite-substituting web apps |
| `facebook` | 0.00 | not a developer surface |
| `openmoji` | 0.00 | not a default anywhere |

Shares are computed first, then the Twemoji carve-out is taken proportionally from the
other three so the total is exactly 1.00.

---

## 6. Sensitivity and known gaps

- **The weighting barely matters.** Varying the mobile share from 10% to 35% — a range
  wider than any plausible three-year outcome — moves every block by an amount at or
  below the threshold of visibility:

  | block | mobile 10% | **mobile 20%** | mobile 35% |
  |---|---|---|---|
  | red | `#E33B41` | `#E43B3F` | `#E43B3C` |
  | orange | `#FC8328` | `#FD8526` | `#FD8823` |
  | yellow | `#FDC03A` | `#FDC139` | `#FDC337` |
  | green | `#51BC56` | `#53BC53` | `#55BA4E` |
  | blue | `#287FE2` | `#277EE2` | `#257CE2` |
  | purple | `#A456D7` | `#A655D7` | `#A953D8` |
  | brown | `#975D4B` | `#985D4A` | `#995E49` |
  | black | `#28272A` | `#29282A` | `#2A292B` |
  | white | `#E0DBE4` | `#E0DBE4` | `#DFDCE3` |

  - This is because Apple and Noto sit on opposite sides of the mobile/desktop divide in
    both directions — shifting weight toward mobile takes from Windows and gives to both
    Apple and Noto roughly evenly.
  - **Practical consequence**: arguing about weights is not where the uncertainty lives.
    Which *vendor sets are in the pool at all* dominates — dropping Fluent 3D moves red
    further than the entire mobile-share range does.

- **Samsung One UI is the largest gap.** Samsung is roughly a third of Android globally
  and ships its own emoji set, not Noto. No redistributable source was reachable, so
  Samsung's share is folded into `noto`. Direction of the resulting bias is unknown
  without sampling. This is the single most valuable thing to fix.

- **Also unsampled** — WhatsApp (own set, huge but mostly non-developer surface),
  JoyPixels, Huawei HarmonyOS.

- **Slack is folded into `apple` rather than given its own row**, on the basis that Slack
  has historically rendered Apple imagery on all platforms. If Slack has since moved to
  native platform fonts, this weight is misallocated — worth verifying if Slack is a
  primary surface for you.

- **`emoji-datasource@16.0.0` may lag the shipping fonts.** The Apple and Noto assets
  are as of that package version, not as of the current OS release. Colour-square
  designs are among the most stable emoji, so drift is unlikely but not excluded.

- **Gamut** — all outputs are clamped to sRGB. Apple's Display P3 renderings will read
  slightly more saturated on-device than the sampled sRGB values suggest.

---

## 7. Reproduction

```python
import math

VENDORS = {
 "red":    {"apple":"#D83421","noto":"#F44336","ms2d":"#F8312F","ms3d":"#D83D65",
            "twemoji":"#DD2E44","facebook":"#FA2E2F","openmoji":"#D22F27"},
 "orange": {"apple":"#FF9317","noto":"#FF9800","ms2d":"#FF6723","ms3d":"#F66343",
            "twemoji":"#F4900C","facebook":"#FC9002","openmoji":"#E27022"},
 "yellow": {"apple":"#F9C814","noto":"#FFCC32","ms2d":"#FFB02E","ms3d":"#FFAE53",
            "twemoji":"#FDCB58","facebook":"#FEDB3B","openmoji":"#FCEA2B"},
 "green":  {"apple":"#15B714","noto":"#7CB342","ms2d":"#00D26A","ms3d":"#49C48A",
            "twemoji":"#78B159","facebook":"#44C966","openmoji":"#B1CC33"},
 "blue":   {"apple":"#1A6BF3","noto":"#1976D2","ms2d":"#00A6ED","ms3d":"#407FD6",
            "twemoji":"#55ACEE","facebook":"#3CAAFB","openmoji":"#92D3F5"},
 "purple": {"apple":"#BF42FF","noto":"#AB47BC","ms2d":"#C790F1","ms3d":"#7049BB",
            "twemoji":"#AA8ED6","facebook":"#9B3BFB","openmoji":"#8967AA"},
 "brown":  {"apple":"#81502F","noto":"#B76D54","ms2d":"#A56953","ms3d":"#815258",
            "twemoji":"#C1694F","facebook":"#6E4528","openmoji":"#6A462F"},
 "black":  {"apple":"#151514","noto":"#424242","ms2d":"#000000","ms3d":"#423C48",
            "twemoji":"#31373D","facebook":"#30323C","openmoji":"#3F3F3F"},
 "white":  {"apple":"#D9D9D9","noto":"#E0E0E0","ms2d":"#FFFFFF","ms3d":"#D9C6E9",
            "twemoji":"#E6E7E8","facebook":"#F9FCFF","openmoji":"#FFFFFF"},
}

WEIGHTS = {"apple":0.3102, "noto":0.2914, "ms3d":0.2369, "ms2d":0.1015, "twemoji":0.06}

def h2r(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def r2h(c):
    return '#%02X%02X%02X' % tuple(max(0, min(255, round(x * 255))) for x in c)

def s2l(u):
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

def l2s(u):
    return u * 12.92 if u <= 0.0031308 else 1.055 * u ** (1 / 2.4) - 0.055

def oklab(rgb):
    r, g, b = (s2l(x) for x in rgb)
    l = 0.4122214708*r + 0.5363325363*g + 0.0514459929*b
    m = 0.2119034982*r + 0.6806995451*g + 0.1073969566*b
    s = 0.0883024619*r + 0.2817188376*g + 0.6299787005*b
    l, m, s = (math.copysign(abs(x) ** (1/3), x) for x in (l, m, s))
    return (0.2104542553*l + 0.7936177850*m - 0.0040720468*s,
            1.9779984951*l - 2.4285922050*m + 0.4505937099*s,
            0.0259040371*l + 0.7827717662*m - 0.8086757660*s)

def unoklab(L, a, bb):
    l = (L + 0.3963377774*a + 0.2158037573*bb) ** 3
    m = (L - 0.1055613458*a - 0.0638541728*bb) ** 3
    s = (L - 0.0894841775*a - 1.2914855480*bb) ** 3
    r =  4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    g = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    b = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    return tuple(l2s(max(0, min(1, x))) for x in (r, g, b))

def weighted(vals, w):
    pts = [(oklab(h2r(vals[k])), wt) for k, wt in w.items() if k in vals]
    tw = sum(wt for _, wt in pts)
    return r2h(unoklab(*[sum(p[i]*wt for p, wt in pts) / tw for i in range(3)]))

for block, vals in VENDORS.items():
    print(f"{block:8} {weighted(vals, WEIGHTS)}")
```

Re-fetching the source artefacts (npm tarballs, GitHub raw assets) and re-sampling is
described in [§3](#3-sampling-method); the two commands that matter are
`npm pack emoji-datasource-apple@16` and
`curl https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Red%20square/Color/red_square_color.svg`.
