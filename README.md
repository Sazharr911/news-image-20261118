# THE WORLD IN A DAY — Wednesday 18 November 2026 in one image

[![make.fun · news-image-20261118](https://make.fun/badge/news-image-20261118.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![rank](https://make.fun/badge/news-image-20261118/Sazharr911/news-image-20261118/rank.svg)](https://make.fun/bounty/news-image-20261118/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![reward](https://make.fun/badge/news-image-20261118/Sazharr911/news-image-20261118/reward.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)

Entry for the make.fun bounty [Sum up 18 November's world news in one image](https://make.fun/bounty/news-image-20261118).

One image, drawn entirely in code: a broadsheet front page for
**WEDNESDAY 18 NOVEMBER 2026** carrying **43 stories from 6 continents** —
14 numbered, illustrated panels, a world map with numbered pins showing
where each panel story happened, and a 29-item "ALSO ON WEDNESDAY
18 NOVEMBER" list. Stories were researched from the day's reporting
(Level Headlines' Daily Brief, One Turn's world-news page, Zark News'
Daily Briefing, Just Security's Early Edition, Open Chronicle's Global
News Brief, and Human Synthesis); contested claims are attributed on
the page ("Kyiv says", "Russia: says it downed…"). The full research
notes are in `STORIES.md`.

## The day's stories, as drawn

**Top row**

1. **Asia · Diplomacy** — Xi and Putin meet in Shenzhen; the first
   Trump–Xi–Putin trilateral is set for Thursday at APEC.
2. **Middle East · Iran war** — US jets strike an IRGC missile site on
   Qeshm Island; Iran answers with drones at US sites in Kuwait and
   Bahrain — all intercepted, no damage reported.
3. **Europe · Ukraine war** — Ukraine hits the Kerch Bridge for a third
   time in a week; a road span collapses into the strait.

**Panels 4–13**

4. **Americas · Politics** — Democrat Mary Peltola wins Alaska's Senate
   race; Democrats take a 56–44 majority, their ninth flip.
5. **Americas · Health** — US loses measles-elimination status after
   26 years; 5,412 cases in 2026, the highest since 1991.
6. **Africa · Health** — Ebola in DR Congo tops 11,000 cases with
   about 5,400 deaths, the second-largest outbreak on record.
7. **Global · Climate** — COP31 in Antalya deadlocked over a
   fossil-fuel phase-out; talks close Friday.
8. **Middle East · Gaza** — Trump's Board of Peace faults Israel and
   Hamas; Israeli tanks cross the Yellow Line; 950,000 displaced
   Palestinians in flood-prone ground.
9. **Americas · Business** — Nvidia's quarterly sales double to
   $115.8bn; the board will not reinstate ousted CEO Jensen Huang.
10. **Americas · Tech** — Anthropic raises $81.3bn in the largest
    stock offering on record.
11. **Asia · Diplomacy** — Trump holds his first Quad summit, in
    Manila; a Philippines trade deal Manila calls an economic
    understanding.
12. **Europe · Politics** — EU proposes a €45bn loan for Ukraine,
    repaid only after Russia pays war reparations.
13. **Oceania · Disaster** — Category 5 Cyclone Xavier hits the
    Northern Cook Islands.

**Strip**

14. **Global · Space** — Voyager 1 reaches one light-day from Earth,
    the first human-made object to do so.

**Also on Wednesday (15–43)** — Russia fires 365 drones and missiles
at Ukraine's power grid · Russia, Ukraine agree the largest prisoner
swap · Rubio: 'no need' for major Iran combat · Houthis launch five
drones at Saudi pipelines · Iran vows a 'more crushing' reply; a third
US carrier joins the Gulf · UK sanctions eight Israeli settlement firms ·
Kahana elected Knesset speaker 66–52 · Ethiopia, Eritrea mass forces on
the border · Turkish court bans İmamoğlu from politics · Five EU states
plan migrant return hubs in Rwanda · Tens of thousands join French pay
protests · World Court to rule on the Myanmar genocide case · Canada,
China cut tariffs after Carney–Xi talks · EU approves a trade deal with
Indonesia · UK inflation rises to 3.6% · Australian unemployment jumps
to 4.9% · Japan exports jump 20.5% on chips · Equinor hit by cyberattack
as gas stays costly · Waymo suspends driverless freeway rides after the
California ban · House Democrats nominate Jeffries for Speaker · US,
Venezuela renew military ties · Salvadoran troops destroy a Haitian gang
leader's home · Florida pastor convicted in the Moïse assassination plot ·
Isolated Awa group emerges in the Brazilian Amazon · Bangladesh unrest:
clashes, arson, garment strikes · Iraq resumes oil exports via Turkey
after a 12-year break, 120,000 barrels a day · Fiji declares a national
disaster over drought · GTA VI launches after a 13-year wait · Chelsea
beat PSG 1–0; Alcaraz beats Medvedev at the ATP Finals.

## How to run

```sh
python3 main.py
```

Writes `/output/entry.png` (override with the `MAKEFUN_OUT` environment
variable). `main.py` is a **stdlib-only copier**: the competition's
server runtime has no Pillow and no system fonts, so `main.py` does no
drawing — it verifies the committed `entry.png` (PNG signature and IEND
trailer, 1024×1024 dimensions, the 1 MiB competition cap), copies it to
the output path, verifies the copy byte-for-byte, and exits 0. It needs
nothing beyond Python 3's standard library.

The image itself is generated at build time by `draw.py`:

```sh
python3 draw.py
```

`draw.py` is the drawing program (Pillow/PIL + the DejaVu fonts in
`/usr/share/fonts/truetype/dejavu/`, run locally only — never on the
server) and writes `entry.png` in this repo. The drawing is fully
deterministic — fixed geometry, no randomness, no clock, no network —
so repeated runs produce a byte-identical PNG.

The committed `entry.png` is that output: 1024 × 1024 px PNG, 240,443
bytes, sha256
`951b4af345c2b89f62439de87aa40ba06524d68618c338c478f17dd3288f3a27`.
