/**
 * Deities a working can be offered through (`deity` on POST /operator/working).
 *
 * The ids are those of the curated iconography in `knowledge/iconography.json`
 * (`core/iconography.py`); the backend paints the witness from that data and
 * captions it with the deity's names and sources. GET /iconography returns the
 * full entries. `tests/unit/test_iconography.py` checks every id here exists.
 */
export interface DeityOption {
  value: string;
  label: string;
}

export const ICONOGRAPHY_DEITY_OPTIONS: readonly DeityOption[] = [
  { value: 'avalokiteshvara', label: 'Avalokiteshvara (four-armed Chenrezig)' },
  { value: 'avalokiteshvara:thousand_armed', label: 'Avalokiteshvara (eleven-faced, thousand-armed)' },
  { value: 'green_tara', label: 'Green Tara' },
  { value: 'white_tara', label: 'White Tara' },
  { value: 'medicine_buddha', label: 'Medicine Buddha' },
  { value: 'amitabha', label: 'Amitabha Buddha' },
  { value: 'vajrasattva', label: 'Vajrasattva' },
  { value: 'cundi', label: 'Cundi Buddha Mother (Zhunti)' },
  { value: 'shakyamuni', label: 'Shakyamuni Buddha' },
  { value: 'manjushri', label: 'Manjushri' },
  { value: 'prajnaparamita', label: 'Prajnaparamita' },
  { value: 'buddha_generic', label: 'A Buddha (generic form, e.g. the 88 Buddhas)' },
];
