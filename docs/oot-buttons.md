# Ocarina of Time: Xbox and PlayStation buttons (fork feature)

This repository ([nxnativeOoT](https://github.com/matheusvhs/nxnativeOoT)) is upstream [nxnative](https://github.com/seedds/nxnative) at `bd979ced`, plus one feature ported from [Flavio's fork](https://github.com/flaviopz/nxnative) (commit `c487f2a6`): button overlays that make Ocarina of Time show the buttons of the Xbox or PlayStation controller you play with. Everything else — the game's profile, the shader chain, the host — is upstream's; the old fork's other changes (its 30 fps cap, memory switches, rewriter patches and performance notes) are **not** in this branch.

## What it does

The Mac app build runs the profile's `button_mods/make_mods.py`, which makes two RomFS overlays from **your own game's files** — nothing of the game is in the repository; `xbox.png` and `ps5.png` are drawings of the real controllers:

- `xbox/`: an Xbox Series pad's labels (B A Y X, LB/RB, LT/RT, Menu/View)
- `ps/`: a DualSense / DualShock 4's (circle, cross, triangle, square, L1/R1, L2/R2, Options/Create)

Each overlay recolours the symbol font's button glyphs, the HUD and ocarina button textures, and the "Controles básicos" screen's controller art and callout lines. Labels follow the button's position, because nxnative maps an Xbox or PlayStation pad by position: the right button is the game's A, so it shows B (Xbox) or the circle (PlayStation).

## Building

The overlays are made during the Mac app build (`scripts/build_ipa_from_nsp.py <game files> --platform mac-app`) and packed as `Resources/button_mods`. The generator needs these Python packages, besides the ones the build itself needs:

```
python3 -m pip install numpy pillow scipy shapely fonttools astc-encoder-py "backports.zstd; python_version < '3.14'"
```

Without them the build warns, lists the missing packages, and packs the app without the overlays (the game keeps its own buttons).

## Which overlay runs

When the game mounts its RomFS, the host picks the overlay once per start:

- an Xbox or PlayStation pad connected at start → that family's overlay (`xbox/` or `ps/`), read through IOKit by the Mac front end (`pad_family_mac.h`)
- a Nintendo pad, or no pad → the game's own buttons
- `DM_BUTTONS=xbox|ps|nintendo` (or `DM_BOTOES`) forces the choice; `auto` or unset detects it
- `DM_BUTTON_MODS=<folder>` names the folder holding the overlays; the Mac launcher sets it to the app's `Resources/button_mods`

A folder named by `DM_ROMFS_OVERLAY` still wins: manual overlay roots come first in the search order, the button mod last. Swapping controllers mid-game does not switch buttons; the choice is made once, when the RomFS mounts. The feature has not been validated in gameplay on this branch yet.
