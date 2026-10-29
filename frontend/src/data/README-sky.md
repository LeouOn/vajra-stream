# Star data: stars-v65.json, star-names.json, constellation-lines.json

Byte-for-byte copies of the wave-0 datasets (row W0-2), converted
deterministically from their sources by a converter script
(`convert_stars.py`): `stars-v65.json` and
`star-names.json`. `constellation-lines.json` is the same crosswalk as wave 0,
regenerated in row W2-A2 so repeated d3-celestial ids append instead of
overwrite (see the Serpens note below); its bytes therefore differ from the
wave-0 output. The licence quotes are reproduced below; the full provenance
record, the licence survey and the converter scripts are kept in the
maintainer's working notes, which are not part of this repository.

The d3-celestial source has **89 features for 88 constellations**: `Ser`
appears twice (Serpens Caput, 9 vertices; Serpens Cauda, 6). The wave-0
converter keyed a dict by id, so Cauda overwrote Caput and one 9-vertex chain
was lost (884 of 893 vertices). Row W2-A2 regenerates the same crosswalk with
a follow-up script (`fix_lines.py`), appending repeated ids:
`Ser` now carries both polylines and all 893 vertices are present.

| file | sha256 | bytes | contents |
|---|---|---|---|
| `stars-v65.json` | `fa4d28d5cde0ba294a6af804e01d36d964ea4618e3de2a0e542038bf6b0af68f` | 297,738 | 8,404 stars `[[hr, ra_deg, dec_deg, vmag, bv\|null], …]`, J2000 |
| `star-names.json` | `1edca3ae2be16c2ed4694495236dcb132d2161d9d225c31436842a3e0c25ff9e` | 13,615 | 338 IAU WGSN names `[{"name","hr","vmag"}]` |
| `constellation-lines.json` | `9f34bb45cc3c053f34618a10d150eecee43796c185a7cc17876eaf4721fc14e3` | 5,473 | d3-celestial figures crosswalked to HR ids: `{"crosswalk","tolerance_arcsec":180,"constellations":{"And":[[hr,…],…]}}`; 88 constellations, 150 polylines, 893 vertices, all resolved |

## Licences (verbatim, with URLs)

**Yale Bright Star Catalogue, 5th revised ed. (CDS V/50)** — the stars. Terms
of use, <https://cds.unistra.fr/vizier-org/licences_vizier.html>:

> "The data retrieved with VizieR are free of usage in a scientific context ;
> however, as it is the usage in scientific publication, the original authors
> and publication references including the publisher have to be explicitely
> cited (see section Code of conduct of scientific research )."

(The same terms page opens with a sentence on VizieR's purpose, "essentially
dedicated to a scientific usage", omitted above; the binding sentence is quoted
in full.)

Acknowledgement: "This research has made use of the VizieR catalogue access
tool, CDS, Strasbourg, France (DOI: 10.26093/cds/vizier)." Original
description: Hoffleit & Warren 1991, *The Bright Star Catalogue*, 5th revised
edition (CDS V/50).

**IAU Catalogue of Star Names** — the names,
<https://www.pas.rochester.edu/~emamajek/WGSN/IAU-CSN.txt> (official WGSN
list). Header, verbatim:

> "All IAU-produced products (Images, Videos, Texts) are released under
> Creative Commons Attribution (i.e. free to use in all perpetuity,
> world-wide, as long as the source is mentioned)."

**d3-celestial** — the constellation figures,
<https://github.com/ofrohn/d3-celestial> `LICENSE`, verbatim in full:

> Copyright (c) 2015, Olaf Frohn
> All rights reserved.
>
> Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
>
> 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
>
> 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
>
> 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
>
> THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## What the figures derive from (stated plainly, not softened)

The polylines in `constellation-lines.json` are d3-celestial's constellation
figures. Those figures derive from the IAU / Sky & Telescope constellation
figures (Sinnott & Fienberg; the underlying IAU chart's Wikimedia Commons
metadata reports CC BY 3.0). That chain is **third-party evidence**: we could
not verify a licence grant from Sky & Telescope itself, and the reported
CC BY 3.0 is metadata about the IAU chart, not a grant we hold. The maintainer
chose d3-celestial's BSD-3 redistribution knowing this chain (decision
2026-10-22). Stellarium's GPL figures were rejected for licensing reasons and
are not used. The crosswalk from d3-celestial's coordinate vertices to HR ids
(nearest star within 3 arcminutes; 893/893 resolved) is documented in the
wave-0 provenance record (maintainer's notes, not in this repository).

## Parse hazard (for anyone re-deriving the star file)

The V/50 declination sign sits in **column 84**, outside the documented I2
degree field (cols 85–86). Reading only the field mirrors the entire southern
hemisphere onto positive declinations while every count still looks sane.
The wave-0 converter (`convert_stars.py`, `parse_bsc5`) reads column 84 for
the sign; anyone re-deriving the file must do the same.
