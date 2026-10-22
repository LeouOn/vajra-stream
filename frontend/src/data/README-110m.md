# land-110m.json — Natural Earth 110 m land, compact ring JSON

- **Source:** Natural Earth `ne_110m_land.geojson` via the official GitHub
  mirror `nvkelso/natural-earth-vector` (`geojson/ne_110m_land.geojson`,
  branch `master`, retrieved 2026-10-22T01:39:10Z, HTTP 200, 138,160 bytes,
  raw sha256 `9e0729ee253ca7d7a5c4ae9395fb1902264c5377c52e224d13dd85010e2835d9`).
  Full provenance: `docs/notes/earthsky/wave0/land/dataset-record.md`.
- **Licence: public domain.** Verbatim from
  <https://www.naturalearthdata.com/about/terms-of-use/>:
  > All versions of Natural Earth raster + vector map data found on this
  > website are in the public domain. You may use the maps in any manner,
  > including modifying the content and design, electronic dissemination, and
  > offset printing. The primary authors, Tom Patterson and Nathaniel Vaughn
  > Kelso, and all other contributors renounce all financial claim to the maps
  > and invites you to use them for personal, educational, and commercial
  > purposes.
  >
  > No permission is needed to use Natural Earth. Crediting the authors is
  > unnecessary.
- **Converter:** `docs/notes/earthsky/wave0/land/convert_land.py` (W0-1,
  deterministic — byte-identical output on re-run), setting `decimals = 3`
  (0.001 deg ≈ 111 m at the equator; finer than the 110 m data's own
  generalization and 1/88 of a 4096-px texture texel).
- **This file:** 68,754 bytes;
  sha256 `5a819ebb0d519434a6a7d6021ccaa6130c1060e22f86cee230a244a3e7bea308`
  (verified by `sha256sum` and by a fresh `convert_land.py` re-run producing
  byte-identical output, W1-D2). 127 polygons (one hole ring: the Caspian
  Sea), 5,132 vertices, integers in units of 10^-3 degrees (see `decodeLand`
  in `src/lib/earth.ts`).
