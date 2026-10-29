# land-50m.json

Natural Earth 1:50m land polygons, converted to the integer-ring format used
by `frontend/src/lib/earth.ts`.

- **Source**: Natural Earth `ne_50m_land` (v5.x), converted in wave-0 row
  W0-1. The full provenance record and the converter script are kept in the
  maintainer's working notes, which are not part of this repository.
- **Licence: public domain.** Verbatim, from
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

- **sha256**: `b5699b5db7fda49813c23a069927207247ecfc7952932c194e24930c15e97373`
  (byte-for-byte copy of the wave-0 converter's output, verified with
  `cmp`).
- **How it was made**: a small converter script, `convert_land.py`
  (deterministic; identical output bytes on re-run) with **decimals = 2** —
  0.01° ≈ 1.11 km, chosen to fit the 800 KB budget (688,309 bytes; 3 decimals
  would measure 809,898 bytes, over budget).
- **Integer-ring format**: coordinates are integers in units of 10^-decimals
  degrees (EPSG:4326): integer 1234 at decimals = 2 means 1.23°.
  `{"v":1,"kind":"land","decimals":2,"polys":[{"o":[x0,y0,x1,y1,...],"h":[[...],...]}]}` —
  `o` is the outer ring, each entry of `h` a hole ring (this file has exactly
  one hole, the Caspian Sea). Duplicate consecutive vertices produced by
  rounding are dropped. No ring crosses the antimeridian; Antarctica's ring
  includes the run along latitude −90 from longitude +180 to −180, sampled at
  sub-1.5° steps, so the fill reaches the bottom edge of an equirectangular
  map without a seam jump.
- **Contents**: 1,421 polygons, 60,254 outer-ring vertices + 391 hole
  vertices = 60,645 in total.
