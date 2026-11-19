# The World in a Day — 18 November 2026

[![make.fun · news-image-20261118](https://make.fun/badge/news-image-20261118.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![rank](https://make.fun/badge/news-image-20261118/Sazharr911/news-image-20261118/rank.svg)](https://make.fun/bounty/news-image-20261118/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![reward](https://make.fun/badge/news-image-20261118/Sazharr911/news-image-20261118/reward.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)

An entry for the make.fun bounty [Sum up 18 November's world news in
one image](https://make.fun/bounty/news-image-20261118): a single
1024×1024 broadsheet front page for **Wednesday 18 November 2026**,
drawn entirely in code, carrying **43 stories from 6 continents**.

## Running it

The page ships as a finished PNG, and the runtime program only copies
it into place:

```sh
python3 main.py
```

That writes `/output/entry.png` (`MAKEFUN_OUT` overrides the path).
`main.py` uses only the Python standard library: it checks the PNG
signature, the 1024×1024 dimensions, the 1 MiB size cap and the IEND
trailer, copies `entry.png`, then verifies the copy byte-for-byte and
exits 0. The competition server has no Pillow and no system fonts, so
no drawing happens at runtime.

To redraw the image from scratch (needs Pillow and the DejaVu fonts,
local machine only):

```sh
python3 draw.py
```

`draw.py` is deterministic — fixed geometry, no randomness, no clock,
no network — so every run produces the same bytes.

## What is on the page

A masthead with the date set huge — **WEDNESDAY 18 NOVEMBER 2026** —
then 14 numbered, illustrated panels, a world map with numbered pins
for panels 1–13, and a 29-item list of further stories. The panels,
grouped by region:

**Asia**

1. Xi and Putin meet in Shenzhen; the first Trump–Xi–Putin trilateral
   is set for Thursday at APEC.
11. Trump holds his first Quad summit, in Manila; a Philippines trade
    deal Manila calls an economic understanding.

**Middle East**

2. US jets strike an IRGC missile site on Qeshm Island; Iran answers
   with drones at US sites in Kuwait and Bahrain — all intercepted.
8. Trump's Board of Peace faults Israel and Hamas; Israeli tanks cross
   the Yellow Line; 950,000 displaced Palestinians in flood-prone
   ground.

**Europe**

3. Ukraine hits the Kerch Bridge for a third time in a week; a road
   span collapses into the strait.
12. The EU proposes a €45bn loan for Ukraine, repaid only after Russia
    pays war reparations.

**Americas**

4. Democrat Mary Peltola wins Alaska's Senate race; Democrats take a
   56–44 majority, their ninth flip of the midterms.
5. The US loses measles-elimination status after 26 years; 5,412 cases
   in 2026, the highest since 1991. Mexico and Bolivia lose status too.
9. Nvidia's quarterly sales double to $115.8bn; the board will not
   reinstate ousted CEO Jensen Huang.
10. Anthropic raises $81.3bn in the largest stock offering on record.

**Africa**

6. Ebola in DR Congo tops 11,000 cases with about 5,400 deaths, the
   second-largest outbreak on record.

**Oceania**

13. Category 5 Cyclone Xavier hits the Northern Cook Islands.

**Global**

7. COP31 in Antalya deadlocked over a fossil-fuel phase-out; talks
   close Friday.
14. Voyager 1 reaches one light-day from Earth, the first human-made
    object to do so.

## Also on Wednesday 18 November (15–43)

15. Russia fires 365 drones and missiles at Ukraine's power grid
16. Russia, Ukraine agree the largest prisoner swap
17. Rubio: 'no need' for major Iran combat
18. Houthis launch five drones at Saudi pipeline pumping stations
19. Iran vows a 'more crushing' reply; a third US carrier joins the Gulf
20. UK sanctions eight Israeli settlement firms
21. Kahana elected Knesset speaker 66–52, a Netanyahu opponent
22. Ethiopia, Eritrea mass forces on the border
23. Turkish court bans İmamoğlu from politics
24. Five EU states plan migrant return hubs in Rwanda
25. Tens of thousands join French pay protests
26. World Court to rule on the Myanmar genocide case
27. Canada, China cut tariffs after Carney–Xi talks
28. EU approves a trade deal with Indonesia
29. UK inflation rises to 3.6%
30. Australian unemployment jumps to 4.9%
31. Japan exports jump 20.5% on chips
32. Equinor hit by cyberattack as gas stays costly
33. Waymo suspends driverless freeway rides after the California ban
34. House Democrats nominate Jeffries for Speaker
35. US, Venezuela renew military ties
36. Salvadoran troops destroy a Haitian gang leader's home
37. Florida pastor convicted in the Moïse assassination plot
38. Isolated Awa group emerges in the Brazilian Amazon
39. Bangladesh unrest: clashes, arson, garment strikes
40. Iraq resumes oil exports via Turkey after a 12-year break,
    120,000 barrels a day
41. Fiji declares a national disaster over drought
42. GTA VI launches after a 13-year wait
43. Chelsea beat PSG 1–0; Alcaraz beats Medvedev at the ATP Finals

## Research and verification

Every item was reported on or for Wednesday 18 November 2026; the
research notes and per-story sources are in `STORIES.md` (Level
Headlines' Daily Brief, One Turn's world-news page, Zark News' Daily
Briefing, Just Security's Early Edition, Open Chronicle's Global News
Brief, and Human Synthesis). Contested claims are attributed on the
page itself.

The committed `entry.png` is 1024 × 1024 px, 240,443 bytes, sha256
`951b4af345c2b89f62439de87aa40ba06524d68618c338c478f17dd3288f3a27`.
