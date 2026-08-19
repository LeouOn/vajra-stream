import { describe, it, expect } from 'vitest';
import {
  resolveTargetCoords,
  latLonToVec3,
  planetToLatLon,
  createArcCurve,
  toneFromFrequencies,
  COUNTRY_COORDS,
} from '../../components/3D/worldEmanationHelpers';
import * as THREE from 'three';

describe('worldEmanationHelpers', () => {
  describe('resolveTargetCoords', () => {
    it('resolves direct country names', () => {
      expect(resolveTargetCoords('Japan')).toEqual(COUNTRY_COORDS['japan']);
      expect(resolveTargetCoords('france')).toEqual(COUNTRY_COORDS['france']);
      expect(resolveTargetCoords('Brazil')).toEqual(COUNTRY_COORDS['brazil']);
    });

    it('resolves substring, compound, and city matches', () => {
      expect(resolveTargetCoords('Prayers for Tokyo')).toEqual(COUNTRY_COORDS['tokyo']);
      expect(resolveTargetCoords('Healing for the people in Kathmandu')).toEqual(COUNTRY_COORDS['kathmandu']);
      expect(resolveTargetCoords('East Java, Indonesia')).toEqual(COUNTRY_COORDS['java']);
      expect(resolveTargetCoords('Earthquake near Tokyo, Japan')).toEqual(COUNTRY_COORDS['tokyo']);
      expect(resolveTargetCoords('Kigali, Rwanda')).toEqual(COUNTRY_COORDS['kigali']);
      expect(resolveTargetCoords('Los Angeles, California')).toEqual(COUNTRY_COORDS['los angeles']);
      expect(resolveTargetCoords('Relief in Gaza')).toEqual(COUNTRY_COORDS['gaza']);
    });

    it('returns null for unresolvable and global intentions (honesty rule)', () => {
      expect(resolveTargetCoords('all beings')).toBeNull();
      expect(resolveTargetCoords('all sentient beings')).toBeNull();
      expect(resolveTargetCoords('the field')).toBeNull();
      expect(resolveTargetCoords('')).toBeNull();
      expect(resolveTargetCoords(null)).toBeNull();
      expect(resolveTargetCoords('random unknown intention 12345')).toBeNull();
    });
  });

  describe('latLonToVec3', () => {
    it('converts equator and prime meridian to vector on sphere surface', () => {
      const v = latLonToVec3(0, 0, 2);
      expect(v.length()).toBeCloseTo(2, 5);
      expect(v.y).toBeCloseTo(0, 5);
    });

    it('converts North Pole (90 lat) to positive Y vector', () => {
      const v = latLonToVec3(90, 0, 2);
      expect(v.y).toBeCloseTo(2, 5);
      expect(v.x).toBeCloseTo(0, 5);
      expect(v.z).toBeCloseTo(0, 5);
    });
  });

  describe('planetToLatLon', () => {
    it('projects Aries 0° to prime meridian and 0° latitude', () => {
      const [lat, lon] = planetToLatLon(0);
      expect(lat).toBeCloseTo(0, 5);
      expect(lon).toBeCloseTo(-180, 5);
    });

    it('projects Cancer 90° to maximum northern obliquity ~23.44°', () => {
      const [lat] = planetToLatLon(90);
      expect(lat).toBeCloseTo(23.44, 2);
    });
  });

  describe('createArcCurve', () => {
    it('creates quadratic bezier curve with elevated midpoint', () => {
      const start = new THREE.Vector3(2, 0, 0);
      const end = new THREE.Vector3(0, 2, 0);
      const curve = createArcCurve(start, end, 0.5);

      expect(curve.v0.length()).toBeCloseTo(2.05, 2);
      expect(curve.v2.length()).toBeCloseTo(2.05, 2);
      expect(curve.v1.length()).toBeCloseTo(2.55, 2);
    });
  });

  describe('toneFromFrequencies', () => {
    it('returns the canonical cyan fallback for no frequencies', () => {
      expect(toneFromFrequencies(undefined)).toBe('#38bdf8');
      expect(toneFromFrequencies([])).toBe('#38bdf8');
    });

    it('selects the dominant (max) frequency when several are present', () => {
      expect(toneFromFrequencies([174, 285, 528, 396])).toBe('#22c55e');
    });

    it('maps Solfeggio bands to a coherent palette', () => {
      expect(toneFromFrequencies([174])).toBe('#a78bfa');
      expect(toneFromFrequencies([396])).toBe('#818cf8');
      expect(toneFromFrequencies([417])).toBe('#6366f1');
      expect(toneFromFrequencies([528])).toBe('#22c55e');
      expect(toneFromFrequencies([639])).toBe('#22d3ee');
      expect(toneFromFrequencies([741])).toBe('#8b5cf6');
      expect(toneFromFrequencies([852])).toBe('#d946ef');
      expect(toneFromFrequencies([963])).toBe('#fbbf24');
    });

    it('any positive frequency produces a valid color', () => {
      for (const hz of [60, 100, 200, 350, 440, 500, 600, 700, 800, 900, 1000, 1200]) {
        expect(toneFromFrequencies([hz])).toMatch(/^#[0-9a-f]{6}$/);
      }
    });
  });
});
