/**
 * W3-D1 — the pure series maths behind scrubbing.
 *
 * Fixtures are LITERALS copied from the independent oracle
 * `docs/notes/earthsky/wave3/oracle/oracle_series.json` (never imported) and
 * from `docs/notes/earthsky/wave3/d2/consistency.json`, which the script
 * `docs/notes/earthsky/wave3/d2/consistency.py` produced by calling the repo's
 * live `core.celestial_sky.calculate_night_sky` for 3 instants x 2 places.
 *
 * The oracle states the reconstruction: Dec = lat, RA = wrap360(lon + GAST),
 * with GAST apparent. Tolerances from the oracle report (W3-O,
 * oracle_report.md): RA reconstruction 0.001 deg, Moon 0.002; the route's
 * sub-point lon/GAST tolerance is 0.005; 0.05 deg against the live path.
 */
import { describe, expect, it } from 'vitest';
import { bodiesAt, decodeSeries, horizontalOf } from '../lib/skySeries';
import { parseInstant } from '../lib/skyClock';

type RawBody = { id: string; lat: number; lon: number };
type RawSample = { at: string; gast_deg: number; sun: RawBody; moon: RawBody; planets: RawBody[] };

interface ConsistencyCase {
  label: string;
  instant: string;
  place: string;
  latitude: number;
  longitude: number;
  gastDeg: number;
  bodies: RawBody[];
  live: Record<string, { altitude: number; azimuth: number }>;
}

const EQUINOX_SIX: RawSample[] = [
  {"at":"2026-03-20T14:46:00+00:00","gast_deg":39.64937,"sun":{"id":"sun","lat":9.1e-05,"lon":-39.649388},"moon":{"id":"moon","lat":11.238252,"lon":-22.036433},"planets":[{"id":"mercury","lat":-7.425063,"lon":-59.916933},{"id":"venus","lat":6.096784,"lon":-23.101568},{"id":"mars","lat":-7.21454,"lon":-53.795934},{"id":"jupiter","lat":22.929005,"lon":66.92579},{"id":"saturn","lat":-0.308841,"lon":-35.018775},{"id":"uranus","lat":19.612297,"lon":16.450145},{"id":"neptune","lat":-0.493049,"lon":-37.502941},{"id":"pluto","lat":-22.80879,"lon":-91.270007}]},
  {"at":"2026-03-20T14:56:00+00:00","gast_deg":42.156215,"sun":{"id":"sun","lat":0.002837,"lon":-42.1499},"moon":{"id":"moon","lat":11.282281,"lon":-24.452152},"planets":[{"id":"mercury","lat":-7.426693,"lon":-62.423263},{"id":"venus","lat":6.100278,"lon":-25.60051},{"id":"mars","lat":-7.212421,"lon":-56.297709},{"id":"jupiter","lat":22.928987,"lon":64.419175},{"id":"saturn","lat":-0.308499,"lon":-37.524825},{"id":"uranus","lat":19.612355,"lon":13.943562},{"id":"neptune","lat":-0.492945,"lon":-40.009544},{"id":"pluto","lat":-22.808773,"lon":-93.776696}]},
  {"at":"2026-03-20T15:06:00+00:00","gast_deg":44.663059,"sun":{"id":"sun","lat":0.005583,"lon":-44.650411},"moon":{"id":"moon","lat":11.326286,"lon":-26.867837},"planets":[{"id":"mercury","lat":-7.428321,"lon":-64.929589},{"id":"venus","lat":6.103771,"lon":-28.099453},{"id":"mars","lat":-7.210302,"lon":-58.799484},{"id":"jupiter","lat":22.928968,"lon":61.91256},{"id":"saturn","lat":-0.308157,"lon":-40.030875},{"id":"uranus","lat":19.612413,"lon":11.436978},{"id":"neptune","lat":-0.492841,"lon":-42.516147},{"id":"pluto","lat":-22.808757,"lon":-96.283384}]},
  {"at":"2026-03-20T15:16:00+00:00","gast_deg":47.169904,"sun":{"id":"sun","lat":0.008328,"lon":-47.150922},"moon":{"id":"moon","lat":11.370266,"lon":-29.283487},"planets":[{"id":"mercury","lat":-7.429947,"lon":-67.43591},{"id":"venus","lat":6.107265,"lon":-30.598395},{"id":"mars","lat":-7.208182,"lon":-61.301259},{"id":"jupiter","lat":22.928949,"lon":59.405946},{"id":"saturn","lat":-0.307814,"lon":-42.536925},{"id":"uranus","lat":19.612471,"lon":8.930395},{"id":"neptune","lat":-0.492737,"lon":-45.022749},{"id":"pluto","lat":-22.808741,"lon":-98.790072}]},
  {"at":"2026-03-20T15:26:00+00:00","gast_deg":49.676748,"sun":{"id":"sun","lat":0.011074,"lon":-49.651434},"moon":{"id":"moon","lat":11.414221,"lon":-31.699103},"planets":[{"id":"mercury","lat":-7.431571,"lon":-69.942227},{"id":"venus","lat":6.110758,"lon":-33.097337},{"id":"mars","lat":-7.206063,"lon":-63.803035},{"id":"jupiter","lat":22.928931,"lon":56.899331},{"id":"saturn","lat":-0.307472,"lon":-45.042975},{"id":"uranus","lat":19.612529,"lon":6.423811},{"id":"neptune","lat":-0.492633,"lon":-47.529352},{"id":"pluto","lat":-22.808724,"lon":-101.296761}]},
  {"at":"2026-03-20T15:36:00+00:00","gast_deg":52.183593,"sun":{"id":"sun","lat":0.01382,"lon":-52.151946},"moon":{"id":"moon","lat":11.45815,"lon":-34.114685},"planets":[{"id":"mercury","lat":-7.433193,"lon":-72.448539},{"id":"venus","lat":6.114252,"lon":-35.596279},{"id":"mars","lat":-7.203944,"lon":-66.30481},{"id":"jupiter","lat":22.928912,"lon":54.392717},{"id":"saturn","lat":-0.307129,"lon":-47.549025},{"id":"uranus","lat":19.612586,"lon":3.917228},{"id":"neptune","lat":-0.492529,"lon":-50.035955},{"id":"pluto","lat":-22.808708,"lon":-103.803449}]},
];

const MOON_SEAM_SIX: RawSample[] = [
  {"at":"2026-07-01T00:00:00+00:00","gast_deg":279.065133,"sun":{"id":"sun","lat":23.118502,"lon":-179.050782},"moon":{"id":"moon","lat":-25.20704,"lon":13.349749},"planets":[{"id":"mercury","lat":18.449771,"lon":-161.360449},{"id":"venus","lat":16.439063,"lon":-135.881351},{"id":"mars","lat":20.17794,"lon":140.444396},{"id":"jupiter","lat":20.543784,"lon":-156.616123},{"id":"saturn","lat":3.397218,"lon":94.917443},{"id":"uranus","lat":20.738289,"lon":142.664024},{"id":"neptune","lat":0.497055,"lon":85.52117},{"id":"pluto","lat":-23.141717,"lon":29.261749}]},
  {"at":"2026-07-01T00:10:00+00:00","gast_deg":281.571978,"sun":{"id":"sun","lat":23.118044,"lon":178.449554},"moon":{"id":"moon","lat":-25.188849,"lon":10.932653},"planets":[{"id":"mercury","lat":18.448098,"lon":-163.86835},{"id":"venus","lat":16.43636,"lon":-138.380486},{"id":"mars","lat":20.179017,"lon":137.942686},{"id":"jupiter","lat":20.543473,"lon":-159.121415},{"id":"saturn","lat":3.397304,"lon":92.410885},{"id":"uranus","lat":20.738355,"lon":140.157544},{"id":"neptune","lat":0.49706,"lon":83.01435},{"id":"pluto","lat":-23.141767,"lon":26.754759}]},
  {"at":"2026-07-01T00:20:00+00:00","gast_deg":284.078823,"sun":{"id":"sun","lat":23.117586,"lon":175.94989},"moon":{"id":"moon","lat":-25.170603,"lon":8.515535},"planets":[{"id":"mercury","lat":18.446426,"lon":-166.376254},{"id":"venus","lat":16.433655,"lon":-140.879622},{"id":"mars","lat":20.180094,"lon":135.440976},{"id":"jupiter","lat":20.543163,"lon":-161.626706},{"id":"saturn","lat":3.397391,"lon":89.904328},{"id":"uranus","lat":20.738421,"lon":137.651064},{"id":"neptune","lat":0.497064,"lon":80.50753},{"id":"pluto","lat":-23.141818,"lon":24.247769}]},
  {"at":"2026-07-01T00:30:00+00:00","gast_deg":286.585668,"sun":{"id":"sun","lat":23.117128,"lon":173.450225},"moon":{"id":"moon","lat":-25.152302,"lon":6.098395},"planets":[{"id":"mercury","lat":18.444755,"lon":-168.884162},{"id":"venus","lat":16.430951,"lon":-143.378758},{"id":"mars","lat":20.181171,"lon":132.939267},{"id":"jupiter","lat":20.542853,"lon":-164.131998},{"id":"saturn","lat":3.397477,"lon":87.397771},{"id":"uranus","lat":20.738487,"lon":135.144583},{"id":"neptune","lat":0.497068,"lon":78.00071},{"id":"pluto","lat":-23.141869,"lon":21.740778}]},
  {"at":"2026-07-01T00:40:00+00:00","gast_deg":289.092512,"sun":{"id":"sun","lat":23.116669,"lon":170.950561},"moon":{"id":"moon","lat":-25.133946,"lon":3.681234},"planets":[{"id":"mercury","lat":18.443085,"lon":-171.392074},{"id":"venus","lat":16.428246,"lon":-145.877895},{"id":"mars","lat":20.182248,"lon":130.437557},{"id":"jupiter","lat":20.542542,"lon":-166.637289},{"id":"saturn","lat":3.397564,"lon":84.891213},{"id":"uranus","lat":20.738553,"lon":132.638103},{"id":"neptune","lat":0.497072,"lon":75.49389},{"id":"pluto","lat":-23.141919,"lon":19.233788}]},
  {"at":"2026-07-01T00:50:00+00:00","gast_deg":291.599357,"sun":{"id":"sun","lat":23.11621,"lon":168.450896},"moon":{"id":"moon","lat":-25.115534,"lon":1.26405},"planets":[{"id":"mercury","lat":18.441416,"lon":-173.89999},{"id":"venus","lat":16.425541,"lon":-148.377032},{"id":"mars","lat":20.183325,"lon":127.935848},{"id":"jupiter","lat":20.542232,"lon":-169.14258},{"id":"saturn","lat":3.39765,"lon":82.384656},{"id":"uranus","lat":20.738619,"lon":130.131623},{"id":"neptune","lat":0.497076,"lon":72.98707},{"id":"pluto","lat":-23.14197,"lon":16.726798}]},
];

const EQUINOX_RA: Record<string, Record<string, number>> = {
  "2026-03-20T14:46:00+00:00": {"sun":359.999982,"moon":17.612937,"mercury":339.732437,"venus":16.547802,"mars":345.853436,"jupiter":106.57516,"saturn":4.630595,"uranus":56.099515,"neptune":2.146429,"pluto":308.379363},
  "2026-03-20T14:56:00+00:00": {"sun":0.006315,"moon":17.704063,"mercury":339.732952,"venus":16.555705,"mars":345.858506,"jupiter":106.57539,"saturn":4.63139,"uranus":56.099777,"neptune":2.146671,"pluto":308.379519},
  "2026-03-20T15:06:00+00:00": {"sun":0.012648,"moon":17.795222,"mercury":339.73347,"venus":16.563606,"mars":345.863575,"jupiter":106.575619,"saturn":4.632184,"uranus":56.100037,"neptune":2.146912,"pluto":308.379675},
  "2026-03-20T15:16:00+00:00": {"sun":0.018982,"moon":17.886417,"mercury":339.733994,"venus":16.571509,"mars":345.868645,"jupiter":106.57585,"saturn":4.632979,"uranus":56.100299,"neptune":2.147155,"pluto":308.379832},
  "2026-03-20T15:26:00+00:00": {"sun":0.025314,"moon":17.977645,"mercury":339.734521,"venus":16.579411,"mars":345.873713,"jupiter":106.576079,"saturn":4.633773,"uranus":56.100559,"neptune":2.147396,"pluto":308.379987},
  "2026-03-20T15:36:00+00:00": {"sun":0.031647,"moon":18.068908,"mercury":339.735054,"venus":16.587314,"mars":345.878783,"jupiter":106.57631,"saturn":4.634568,"uranus":56.100821,"neptune":2.147638,"pluto":308.380144},
};

const MOON_SEAM_RA: Record<string, Record<string, number>> = {
  "2026-07-01T00:00:00+00:00": {"sun":100.014351,"moon":292.414882,"mercury":117.704684,"venus":143.183782,"mars":59.509529,"jupiter":122.44901,"saturn":13.982576,"uranus":61.729157,"neptune":4.586303,"pluto":308.326882},
  "2026-07-01T00:10:00+00:00": {"sun":100.021532,"moon":292.504631,"mercury":117.703628,"venus":143.191492,"mars":59.514664,"jupiter":122.450563,"saturn":13.982863,"uranus":61.729522,"neptune":4.586328,"pluto":308.326737},
  "2026-07-01T00:20:00+00:00": {"sun":100.028713,"moon":292.594358,"mercury":117.702569,"venus":143.199201,"mars":59.519799,"jupiter":122.452117,"saturn":13.983151,"uranus":61.729887,"neptune":4.586353,"pluto":308.326592},
  "2026-07-01T00:30:00+00:00": {"sun":100.035893,"moon":292.684063,"mercury":117.701506,"venus":143.20691,"mars":59.524935,"jupiter":122.45367,"saturn":13.983439,"uranus":61.730251,"neptune":4.586378,"pluto":308.326446},
  "2026-07-01T00:40:00+00:00": {"sun":100.043073,"moon":292.773746,"mercury":117.700438,"venus":143.214617,"mars":59.530069,"jupiter":122.455223,"saturn":13.983725,"uranus":61.730615,"neptune":4.586402,"pluto":308.3263},
  "2026-07-01T00:50:00+00:00": {"sun":100.050253,"moon":292.863407,"mercury":117.699367,"venus":143.222325,"mars":59.535205,"jupiter":122.456777,"saturn":13.984013,"uranus":61.73098,"neptune":4.586427,"pluto":308.326155},
};

const INTERP_EQUINOX_THREE: RawSample[] = [
  {"at":"2026-03-20T14:46:00+00:00","gast_deg":39.64937,"sun":{"id":"sun","lat":9.1e-05,"lon":-39.649388},"moon":{"id":"moon","lat":11.238252,"lon":-22.036433},"planets":[{"id":"mercury","lat":-7.425063,"lon":-59.916933},{"id":"venus","lat":6.096784,"lon":-23.101568},{"id":"mars","lat":-7.21454,"lon":-53.795934},{"id":"jupiter","lat":22.929005,"lon":66.92579},{"id":"saturn","lat":-0.308841,"lon":-35.018775},{"id":"uranus","lat":19.612297,"lon":16.450145},{"id":"neptune","lat":-0.493049,"lon":-37.502941},{"id":"pluto","lat":-22.80879,"lon":-91.270007}]},
  {"at":"2026-03-20T14:56:00+00:00","gast_deg":42.156215,"sun":{"id":"sun","lat":0.002837,"lon":-42.1499},"moon":{"id":"moon","lat":11.282281,"lon":-24.452152},"planets":[{"id":"mercury","lat":-7.426693,"lon":-62.423263},{"id":"venus","lat":6.100278,"lon":-25.60051},{"id":"mars","lat":-7.212421,"lon":-56.297709},{"id":"jupiter","lat":22.928987,"lon":64.419175},{"id":"saturn","lat":-0.308499,"lon":-37.524825},{"id":"uranus","lat":19.612355,"lon":13.943562},{"id":"neptune","lat":-0.492945,"lon":-40.009544},{"id":"pluto","lat":-22.808773,"lon":-93.776696}]},
  {"at":"2026-03-20T15:06:00+00:00","gast_deg":44.663059,"sun":{"id":"sun","lat":0.005583,"lon":-44.650411},"moon":{"id":"moon","lat":11.326286,"lon":-26.867837},"planets":[{"id":"mercury","lat":-7.428321,"lon":-64.929589},{"id":"venus","lat":6.103771,"lon":-28.099453},{"id":"mars","lat":-7.210302,"lon":-58.799484},{"id":"jupiter","lat":22.928968,"lon":61.91256},{"id":"saturn","lat":-0.308157,"lon":-40.030875},{"id":"uranus","lat":19.612413,"lon":11.436978},{"id":"neptune","lat":-0.492841,"lon":-42.516147},{"id":"pluto","lat":-22.808757,"lon":-96.283384}]},
];

const INTERP_MOON_THREE: RawSample[] = [
  {"at":"2026-07-01T00:00:00+00:00","gast_deg":279.065133,"sun":{"id":"sun","lat":23.118502,"lon":-179.050782},"moon":{"id":"moon","lat":-25.20704,"lon":13.349749},"planets":[{"id":"mercury","lat":18.449771,"lon":-161.360449},{"id":"venus","lat":16.439063,"lon":-135.881351},{"id":"mars","lat":20.17794,"lon":140.444396},{"id":"jupiter","lat":20.543784,"lon":-156.616123},{"id":"saturn","lat":3.397218,"lon":94.917443},{"id":"uranus","lat":20.738289,"lon":142.664024},{"id":"neptune","lat":0.497055,"lon":85.52117},{"id":"pluto","lat":-23.141717,"lon":29.261749}]},
  {"at":"2026-07-01T00:10:00+00:00","gast_deg":281.571978,"sun":{"id":"sun","lat":23.118044,"lon":178.449554},"moon":{"id":"moon","lat":-25.188849,"lon":10.932653},"planets":[{"id":"mercury","lat":18.448098,"lon":-163.86835},{"id":"venus","lat":16.43636,"lon":-138.380486},{"id":"mars","lat":20.179017,"lon":137.942686},{"id":"jupiter","lat":20.543473,"lon":-159.121415},{"id":"saturn","lat":3.397304,"lon":92.410885},{"id":"uranus","lat":20.738355,"lon":140.157544},{"id":"neptune","lat":0.49706,"lon":83.01435},{"id":"pluto","lat":-23.141767,"lon":26.754759}]},
  {"at":"2026-07-01T00:20:00+00:00","gast_deg":284.078823,"sun":{"id":"sun","lat":23.117586,"lon":175.94989},"moon":{"id":"moon","lat":-25.170603,"lon":8.515535},"planets":[{"id":"mercury","lat":18.446426,"lon":-166.376254},{"id":"venus","lat":16.433655,"lon":-140.879622},{"id":"mars","lat":20.180094,"lon":135.440976},{"id":"jupiter","lat":20.543163,"lon":-161.626706},{"id":"saturn","lat":3.397391,"lon":89.904328},{"id":"uranus","lat":20.738421,"lon":137.651064},{"id":"neptune","lat":0.497064,"lon":80.50753},{"id":"pluto","lat":-23.141818,"lon":24.247769}]},
];

const CONSISTENCY_CASES: ConsistencyCase[] = [
  {
    label: "equinox-2026", instant: "2026-03-20T14:46:00Z", place: "San Francisco",
    latitude: 37.7749, longitude: -122.4194, gastDeg: 39.64937,
    bodies: [
      {"id":"sun","lat":9.1e-05,"lon":-39.649388},
      {"id":"moon","lat":11.238252,"lon":-22.036433},
      {"id":"mercury","lat":-7.425063,"lon":-59.916933},
      {"id":"venus","lat":6.096784,"lon":-23.101568},
      {"id":"mars","lat":-7.21454,"lon":-53.795934},
      {"id":"jupiter","lat":22.929005,"lon":66.92579},
      {"id":"saturn","lat":-0.308841,"lon":-35.018775},
      {"id":"uranus","lat":19.612297,"lon":16.450145},
      {"id":"neptune","lat":-0.493049,"lon":-37.502941},
      {"id":"pluto","lat":-22.80879,"lon":-91.270007},
    ],
    live: {
      sun: {"altitude":5.71,"azimuth":94.44},
      moon: {"altitude":-1.17,"azimuth":74.79},
      mercury: {"altitude":16.42,"azimuth":113.51},
      venus: {"altitude":-3.57,"azimuth":79.46},
      mars: {"altitude":12.06,"azimuth":109.15},
      jupiter: {"altitude":-28.66,"azimuth":350.19},
      saturn: {"altitude":1.87,"azimuth":91.84},
      uranus: {"altitude":-20.81,"azimuth":41.52},
      neptune: {"altitude":3.71,"azimuth":93.51},
      pluto: {"altitude":22.71,"azimuth":148.88},
    },
  },
  {
    label: "equinox-2026", instant: "2026-03-20T14:46:00Z", place: "Sydney",
    latitude: -33.8688, longitude: 151.2093, gastDeg: 39.64937,
    bodies: [
      {"id":"sun","lat":9.1e-05,"lon":-39.649388},
      {"id":"moon","lat":11.238252,"lon":-22.036433},
      {"id":"mercury","lat":-7.425063,"lon":-59.916933},
      {"id":"venus","lat":6.096784,"lon":-23.101568},
      {"id":"mars","lat":-7.21454,"lon":-53.795934},
      {"id":"jupiter","lat":22.929005,"lon":66.92579},
      {"id":"saturn","lat":-0.308841,"lon":-35.018775},
      {"id":"uranus","lat":19.612297,"lon":16.450145},
      {"id":"neptune","lat":-0.493049,"lon":-37.502941},
      {"id":"pluto","lat":-22.80879,"lon":-91.270007},
    ],
    live: {
      sun: {"altitude":-54.63,"azimuth":161.01},
      moon: {"altitude":-66.54,"azimuth":196.85},
      mercury: {"altitude":-39.26,"azimuth":138.55},
      venus: {"altitude":-61.73,"azimuth":192.01},
      mars: {"altitude":-42.57,"azimuth":145.29},
      jupiter: {"altitude":-8.1,"azimuth":292.23},
      saturn: {"altitude":-55.33,"azimuth":169.01},
      uranus: {"altitude":-47.54,"azimuth":262.26},
      neptune: {"altitude":-54.68,"azimuth":164.81},
      pluto: {"altitude":-7.91,"azimuth":124.38},
    },
  },
  {
    label: "moon-seam-day", instant: "2026-07-01T00:00:00Z", place: "San Francisco",
    latitude: 37.7749, longitude: -122.4194, gastDeg: 279.065133,
    bodies: [
      {"id":"sun","lat":23.118502,"lon":-179.050782},
      {"id":"moon","lat":-25.20704,"lon":13.349749},
      {"id":"mercury","lat":18.449771,"lon":-161.360449},
      {"id":"venus","lat":16.439063,"lon":-135.881351},
      {"id":"mars","lat":20.17794,"lon":140.444396},
      {"id":"jupiter","lat":20.543784,"lon":-156.616123},
      {"id":"saturn","lat":3.397218,"lon":94.917443},
      {"id":"uranus","lat":20.738289,"lon":142.664024},
      {"id":"neptune","lat":0.497055,"lon":85.52117},
      {"id":"pluto","lat":-23.141717,"lon":29.261749},
    ],
    live: {
      sun: {"altitude":39.82,"azimuth":270.04},
      moon: {"altitude":-50.65,"azimuth":84.53},
      mercury: {"altitude":50.99,"azimuth":251.3},
      venus: {"altitude":65.59,"azimuth":212.71},
      mars: {"altitude":6.84,"azimuth":290.28},
      jupiter: {"altitude":55.81,"azimuth":249.47},
      saturn: {"altitude":-36.23,"azimuth":311.36},
      uranus: {"altitude":8.83,"azimuth":289.45},
      neptune: {"altitude":-43.86,"azimuth":319.47},
      pluto: {"altitude":-61.71,"azimuth":66.99},
    },
  },
  {
    label: "moon-seam-day", instant: "2026-07-01T00:00:00Z", place: "Sydney",
    latitude: -33.8688, longitude: 151.2093, gastDeg: 279.065133,
    bodies: [
      {"id":"sun","lat":23.118502,"lon":-179.050782},
      {"id":"moon","lat":-25.20704,"lon":13.349749},
      {"id":"mercury","lat":18.449771,"lon":-161.360449},
      {"id":"venus","lat":16.439063,"lon":-135.881351},
      {"id":"mars","lat":20.17794,"lon":140.444396},
      {"id":"jupiter","lat":20.543784,"lon":-156.616123},
      {"id":"saturn","lat":3.397218,"lon":94.917443},
      {"id":"uranus","lat":20.738289,"lon":142.664024},
      {"id":"neptune","lat":0.497055,"lon":85.52117},
      {"id":"pluto","lat":-23.141717,"lon":29.261749},
    ],
    live: {
      sun: {"altitude":26.37,"azimuth":30.61},
      moon: {"altitude":-18.65,"azimuth":219.84},
      mercury: {"altitude":20.88,"azimuth":48.39},
      venus: {"altitude":4.38,"azimuth":66.85},
      mars: {"altitude":34.99,"azimuth":347.64},
      jupiter: {"altitude":16.33,"azimuth":50.42},
      saturn: {"altitude":25.27,"azimuth":293.32},
      uranus: {"altitude":34.79,"azimuth":350.26},
      neptune: {"altitude":19.69,"azimuth":284.56},
      pluto: {"altitude":-10.66,"azimuth":232.56},
    },
  },
  {
    label: "reference-instant", instant: "2026-10-22T02:00:00Z", place: "San Francisco",
    latitude: 37.7749, longitude: -122.4194, gastDeg: 60.525374,
    bodies: [
      {"id":"sun","lat":-11.007857,"lon":146.134973},
      {"id":"moon","lat":-8.166358,"lon":-82.026291},
      {"id":"mercury","lat":-20.950958,"lon":166.816606},
      {"id":"venus","lat":-18.577703,"lon":146.828615},
      {"id":"mars","lat":18.117215,"lon":75.840007},
      {"id":"jupiter","lat":14.468023,"lon":85.046805},
      {"id":"saturn","lat":1.457574,"lon":-50.312277},
      {"id":"uranus","lat":20.982867,"lon":2.575479},
      {"id":"neptune","lat":-0.383032,"lon":-57.844113},
      {"id":"pluto","lat":-23.630336,"lon":-114.080202},
    ],
    live: {
      sun: {"altitude":-7.85,"azimuth":262.12},
      moon: {"altitude":30.59,"azimuth":131.83},
      mercury: {"altitude":1.38,"azimuth":241.89},
      venus: {"altitude":-11.83,"azimuth":255.55},
      mars: {"altitude":-31.53,"azimuth":339.55},
      jupiter: {"altitude":-31.74,"azimuth":328.32},
      saturn: {"altitude":14.97,"azimuth":100.02},
      uranus: {"altitude":-11.77,"azimuth":51.38},
      neptune: {"altitude":19.59,"azimuth":106.54},
      pluto: {"altitude":28.1,"azimuth":171.34},
    },
  },
  {
    label: "reference-instant", instant: "2026-10-22T02:00:00Z", place: "Sydney",
    latitude: -33.8688, longitude: 151.2093, gastDeg: 60.525374,
    bodies: [
      {"id":"sun","lat":-11.007857,"lon":146.134973},
      {"id":"moon","lat":-8.166358,"lon":-82.026291},
      {"id":"mercury","lat":-20.950958,"lon":166.816606},
      {"id":"venus","lat":-18.577703,"lon":146.828615},
      {"id":"mars","lat":18.117215,"lon":75.840007},
      {"id":"jupiter","lat":14.468023,"lon":85.046805},
      {"id":"saturn","lat":1.457574,"lon":-50.312277},
      {"id":"uranus","lat":20.982867,"lon":2.575479},
      {"id":"neptune","lat":-0.383032,"lon":-57.844113},
      {"id":"pluto","lat":-23.630336,"lon":-114.080202},
    ],
    live: {
      sun: {"altitude":66.67,"azimuth":347.33},
      moon: {"altitude":-24.38,"azimuth":119.47},
      mercury: {"altitude":71.1,"azimuth":50.88},
      venus: {"altitude":74.22,"azimuth":344.56},
      mars: {"altitude":1.49,"azimuth":293.09},
      jupiter: {"altitude":10.7,"azimuth":295.66},
      saturn: {"altitude":-51.85,"azimuth":143.58},
      uranus: {"altitude":-59.49,"azimuth":253.17},
      neptune: {"altitude":-46.23,"azimuth":135.42},
      pluto: {"altitude":9.26,"azimuth":112.31},
    },
  },
];

const PLANET_IDS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];
const RA_TOL_DEG = 0.001;
const MOON_RA_TOL_DEG = 0.002; // oracle_report.md: Moon RA is the worst case
const INTERP_TOL_DEG = 5e-5; // client step 603 s; oracle measures Moon 1.3e-5 there
const LIVE_TOL_DEG = 0.05;

function wrap360(deg: number): number {
  const x = deg % 360;
  return x < 0 ? x + 360 : x;
}

function lonDelta(a: number, b: number): number {
  return Math.abs(((a - b + 540) % 360) - 180);
}

function separationDeg(alt1: number, az1: number, alt2: number, az2: number): number {
  const rad = Math.PI / 180;
  const a1 = alt1 * rad;
  const a2 = alt2 * rad;
  const dz = lonDelta(az1, az2) * rad;
  const c = Math.sin(a1) * Math.sin(a2) + Math.cos(a1) * Math.cos(a2) * Math.cos(dz);
  return Math.acos(Math.min(1, Math.max(-1, c))) / rad;
}

function rawSeries(samples: RawSample[], stepSeconds = 600): Record<string, unknown> {
  return {
    ephemeris: 'swisseph 2.10.03',
    sidereal_time: 'apparent',
    start: samples[0].at,
    end: samples[samples.length - 1].at,
    step_seconds: stepSeconds,
    count: samples.length,
    samples,
    provenance: { computed: 'computed' },
  };
}

function clonePayload(): Record<string, unknown> {
  return JSON.parse(JSON.stringify(rawSeries(INTERP_EQUINOX_THREE))) as Record<string, unknown>;
}

function sampleAt(raw: Record<string, unknown>, index: number): Record<string, unknown> {
  const samples = raw.samples as Record<string, unknown>[];
  return samples[index];
}

function bodyOf(raw: Record<string, unknown>, index: number, key: 'sun' | 'moon'): Record<string, unknown> {
  return sampleAt(raw, index)[key] as Record<string, unknown>;
}

function planetOf(raw: Record<string, unknown>, index: number, planet: number): Record<string, unknown> {
  return (sampleAt(raw, index).planets as Record<string, unknown>[])[planet];
}

describe('decodeSeries', () => {
  it('accepts the oracle-shaped payload and preserves the sample count', () => {
    const series = decodeSeries(rawSeries(EQUINOX_SIX));
    expect(series.count).toBe(6);
    expect(series.samples).toHaveLength(6);
    expect(series.stepSeconds).toBe(600);
    expect(series.siderealTime).toBe('apparent');
    expect(series.samples[0].atMs).toBe(parseInstant(EQUINOX_SIX[0].at));
    expect(series.samples[0].sun).toEqual(EQUINOX_SIX[0].sun);
    expect(series.samples[0].planets.map((p) => p.id)).toEqual(PLANET_IDS);
  });

  it('enforces the 288-sample cap', () => {
    const samples: RawSample[] = [];
    for (let i = 0; i < 289; i += 1) {
      const base = EQUINOX_SIX[0];
      samples.push({
        ...base,
        at: new Date(parseInstant(EQUINOX_SIX[0].at) + i * 600_000).toISOString(),
      });
    }
    expect(() => decodeSeries(rawSeries(samples))).toThrow(/count/);
  });

  it('names the path of the first bad field', () => {
    const mutations: [string, (raw: Record<string, unknown>) => void, RegExp][] = [
      ['ephemeris missing', (raw) => delete raw.ephemeris, /ephemeris/],
      ['sidereal_time not apparent', (raw) => (raw.sidereal_time = 'mean'), /sidereal_time/],
      ['start not an instant', (raw) => (raw.start = '2026-03-20'), /start/],
      ['step below 60 s', (raw) => (raw.step_seconds = 59), /step_seconds/],
      ['step above 3600 s', (raw) => (raw.step_seconds = 3601), /step_seconds/],
      ['count mismatch', (raw) => (raw.count = 4), /count/],
      ['samples not an array', (raw) => (raw.samples = {}), /samples/],
      ['sample at not an instant', (raw) => (sampleAt(raw, 1).at = 'soon'), /samples\[1\]\.at/],
      [
        'instants not increasing',
        (raw) => (sampleAt(raw, 1).at = sampleAt(raw, 0).at as string),
        /samples\[1\]\.at/,
      ],
      ['gast out of range', (raw) => (sampleAt(raw, 0).gast_deg = 400), /samples\[0\]\.gast_deg/],
      ['sun lat out of range', (raw) => (bodyOf(raw, 0, 'sun').lat = 91), /samples\[0\]\.sun\.lat/],
      ['moon lon not finite', (raw) => (bodyOf(raw, 0, 'moon').lon = Number.NaN), /samples\[0\]\.moon\.lon/],
      ['seven planets', (raw) => (sampleAt(raw, 0).planets = (sampleAt(raw, 0).planets as unknown[]).slice(0, 7)), /samples\[0\]\.planets/],
      ['wrong planet id', (raw) => (planetOf(raw, 0, 0).id = 'ceres'), /samples\[0\]\.planets/],
      ['planet lat not a number', (raw) => (planetOf(raw, 0, 3).lat = '22'), /samples\[0\]\.planets\[3\]\.lat/],
      ['provenance missing', (raw) => delete raw.provenance, /provenance/],
    ];
    for (const [label, mutate, path] of mutations) {
      const raw = clonePayload();
      mutate(raw);
      expect(() => decodeSeries(raw), label).toThrow(path);
    }
  });

  it('rejects a non-uniform step and a reversed window', () => {
    const uneven = clonePayload();
    (uneven.samples as Record<string, unknown>[])[2].at = new Date(
      parseInstant(INTERP_EQUINOX_THREE[1].at) + 601_000,
    ).toISOString();
    expect(() => decodeSeries(uneven)).toThrow(/samples\[2\]\.at/);

    const reversed = clonePayload();
    reversed.end = '2026-03-20T14:45:00+00:00';
    expect(() => decodeSeries(reversed)).toThrow(/end/);
  });
});

describe('bodiesAt', () => {
  it('reconstructs RA = wrap360(lon + GAST) for 12 oracle samples (6 equinox + 6 Moon seam day)', () => {
    let checked = 0;
    const sets: [string, RawSample[], Record<string, Record<string, number>>][] = [
      ['equinox', EQUINOX_SIX, EQUINOX_RA],
      ['moon-seam-day', MOON_SEAM_SIX, MOON_SEAM_RA],
    ];
    for (const [label, samples, expected] of sets) {
      expect(samples.length).toBeGreaterThanOrEqual(6);
      const series = decodeSeries(rawSeries(samples));
      for (const sample of samples) {
        const bodies = bodiesAt(series, parseInstant(sample.at));
        expect(bodies).toHaveLength(10);
        const byId = new Map(bodies.map((body) => [body.id, body]));
        const inputs = [sample.sun, sample.moon, ...sample.planets];
        for (const input of inputs) {
          const got = byId.get(input.id);
          expect(got, `${label} ${sample.at} ${input.id}`).toBeDefined();
          if (!got) continue;
          expect(got.dec).toBeCloseTo(input.lat, 12);
          const raTolerance = input.id === 'moon' ? MOON_RA_TOL_DEG : RA_TOL_DEG;
          expect(lonDelta(got.ra, expected[sample.at][input.id])).toBeLessThanOrEqual(raTolerance);
          checked += 1;
        }
      }
    }
    expect(checked).toBe(120);
  });

  it('reproduces the stored midpoint from samples 1200 s apart, per body', () => {
    const maxima: Record<string, number> = {};
    for (const samples of [INTERP_EQUINOX_THREE, INTERP_MOON_THREE]) {
      // Feed only the 1200 s-apart pair (A, C) and ask for the instant of the
      // stored B in between: a true interpolation, not a node lookup.
      const series = decodeSeries(rawSeries([samples[0], samples[2]], 1200));
      const middle = samples[1];
      const bodies = bodiesAt(series, parseInstant(middle.at));
      const inputs = [middle.sun, middle.moon, ...middle.planets];
      for (const input of inputs) {
        const got = bodies.find((body) => body.id === input.id);
        expect(got).toBeDefined();
        if (!got) continue;
        const ra = wrap360(input.lon + middle.gast_deg);
        const err = Math.max(
          Math.abs(got.lat - input.lat),
          lonDelta(got.lon, input.lon),
          lonDelta(got.ra, ra),
        );
        maxima[input.id] = Math.max(maxima[input.id] ?? 0, err);
        expect(err, `${middle.at} ${input.id}`).toBeLessThanOrEqual(INTERP_TOL_DEG);
      }
    }
    // The measured table is part of the row's return. The oracle's linear-
    // interpolation table (interp_error.md) at the client step: 300 s 3.3e-6,
    // 600 s 1.3e-5, 603 s 1.3e-5, 900 s 2.9e-5 (all Moon worst). This test
    // interpolates a 1200 s bracket, twice the client step, so the same 5e-5
    // bar is a stricter test of the same maths.
    console.log('interpolation max error per body (deg, 1200 s bracket):', JSON.stringify(maxima));
    expect(Object.keys(maxima)).toHaveLength(10);
  });

  it('interpolates the +-180 longitude seam and the 360->0 gast seam continuously', () => {
    const dome = (lon: number, gast: number): RawSample => {
      const body = (id: string): RawBody => ({ id, lat: 1, lon });
      const planets = PLANET_IDS.map((id) => body(id));
      return { at: '2026-01-01T00:00:00Z', gast_deg: gast, sun: body('sun'), moon: body('moon'), planets };
    };
    const first = dome(179.9, 359.9);
    const second = dome(-179.9, 0.1);
    second.at = '2026-01-01T00:10:00+00:00';
    const series = decodeSeries(rawSeries([first, second]));
    const midpoint = bodiesAt(series, parseInstant(first.at) + 300_000);
    for (const body of midpoint) {
      // A raw (non-wrap-aware) interpolation would put every body at lon 0.
      expect(Math.abs(body.lon)).toBeGreaterThanOrEqual(179.999999);
      // RA at the seam is 180 (lon -180 + gast 0 -> wrap360 = 180).
      expect(lonDelta(body.ra, 180)).toBeLessThanOrEqual(1e-9);
    }
  });

  it('accepts the window edges and rejects instants outside it', () => {
    const series = decodeSeries(rawSeries(INTERP_EQUINOX_THREE));
    const start = series.samples[0].atMs;
    const end = series.samples[series.samples.length - 1].atMs;
    expect(bodiesAt(series, start)).toHaveLength(10);
    expect(bodiesAt(series, end)).toHaveLength(10);
    expect(() => bodiesAt(series, start - 1)).toThrow(RangeError);
    expect(() => bodiesAt(series, end + 1)).toThrow(RangeError);
  });
});

describe('horizontalOf', () => {
  it('agrees with the live backend path within 0.05 deg for 10 bodies x 6 (instant, place) cases', () => {
    const maxima: Record<string, number> = {};
    let checked = 0;
    for (const testCase of CONSISTENCY_CASES) {
      for (const body of testCase.bodies) {
        const raised = {
          id: body.id,
          lat: body.lat,
          lon: body.lon,
          ra: wrap360(body.lon + testCase.gastDeg),
          dec: body.lat,
        };
        const got = horizontalOf(raised, testCase.gastDeg, testCase.latitude, testCase.longitude);
        const expected = testCase.live[body.id];
        const sep = separationDeg(got.alt, got.az, expected.altitude, expected.azimuth);
        maxima[body.id] = Math.max(maxima[body.id] ?? 0, sep);
        expect(sep, `${testCase.label} ${testCase.place} ${body.id}`).toBeLessThanOrEqual(LIVE_TOL_DEG);
        checked += 1;
      }
    }
    console.log('max separation from the live path (deg):', JSON.stringify(maxima));
    expect(checked).toBe(60);
    // The Moon is the row's stated parallax suspect; measure it, do not assume.
    expect(maxima.moon).toBeLessThanOrEqual(LIVE_TOL_DEG);
  });
});
