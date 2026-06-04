/**
 * Unit tests for crystalStore — crystal grid + programming + meditation.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useCrystalStore } from '../stores/crystalStore';

describe('useCrystalStore', () => {
  beforeEach(() => {
    localStorage.clear();
    useCrystalStore.setState({
      crystals: [],
      gridConfig: {
        type: 'double-hexagon',
        crystalType: 'quartz',
        radius: 4,
        showEnergyField: true,
        intention: 'May all beings be happy',
        crystalCount: 13,
      },
      programming: {
        isActive: false,
        crystalIndex: null,
        intention: '',
        step: 0,
        startTime: null,
      },
      attunement: {
        isActive: false,
        step: 0,
        totalSteps: 7,
        chakras: ['root', 'sacral', 'solar_plexus', 'heart', 'throat', 'third_eye', 'crown'],
        currentChakra: 'root',
      },
      meditation: {
        isActive: false,
        duration: 300,
        elapsed: 0,
        breathPhase: 'inhale',
        breathCount: 0,
      },
    });
  });

  describe('gridConfig', () => {
    it('setGridConfig merges partial config', () => {
      useCrystalStore.getState().setGridConfig({ type: 'star', crystalType: 'amethyst' });
      const cfg = useCrystalStore.getState().gridConfig;
      expect(cfg.type).toBe('star');
      expect(cfg.crystalType).toBe('amethyst');
      expect(cfg.radius).toBe(4);
    });

    it('setGridType / setCrystalType / setIntention mutate single field', () => {
      useCrystalStore.getState().setGridType('grid');
      useCrystalStore.getState().setCrystalType('rose-quartz');
      useCrystalStore.getState().setIntention('Peace and love');
      const cfg = useCrystalStore.getState().gridConfig;
      expect(cfg.type).toBe('grid');
      expect(cfg.crystalType).toBe('rose-quartz');
      expect(cfg.intention).toBe('Peace and love');
    });
  });

  describe('crystal inventory', () => {
    it('addCrystal adds with id, addedAt, programmed=false', () => {
      useCrystalStore.getState().addCrystal({ name: 'Quartz Point', type: 'quartz' });
      const cs = useCrystalStore.getState().crystals;
      expect(cs).toHaveLength(1);
      expect(cs[0].id).toBeTypeOf('number');
      expect(cs[0].name).toBe('Quartz Point');
      expect(cs[0].programmed).toBe(false);
      expect(cs[0].lastCharged).toBe(null);
      expect(cs[0].addedAt).toBeTruthy();
    });

    it('removeCrystal filters by id', async () => {
      useCrystalStore.getState().addCrystal({ name: 'A' });
      await new Promise(r => setTimeout(r, 2));
      useCrystalStore.getState().addCrystal({ name: 'B' });
      const idA = useCrystalStore.getState().crystals.find(c => c.name === 'A').id;
      useCrystalStore.getState().removeCrystal(idA);
      expect(useCrystalStore.getState().crystals).toHaveLength(1);
      expect(useCrystalStore.getState().crystals[0].name).toBe('B');
    });

    it('updateCrystal merges into matching id', () => {
      useCrystalStore.getState().addCrystal({ name: 'Original' });
      const id = useCrystalStore.getState().crystals[0].id;
      useCrystalStore.getState().updateCrystal(id, { name: 'Renamed', programmed: true });
      const c = useCrystalStore.getState().crystals[0];
      expect(c.name).toBe('Renamed');
      expect(c.programmed).toBe(true);
    });
  });

  describe('programming ritual', () => {
    it('startProgramming initializes state', () => {
      useCrystalStore.getState().startProgramming(0, 'Healing');
      const p = useCrystalStore.getState().programming;
      expect(p.isActive).toBe(true);
      expect(p.crystalIndex).toBe(0);
      expect(p.intention).toBe('Healing');
      expect(p.step).toBe(0);
      expect(p.startTime).toBeTruthy();
    });

    it('advanceProgrammingStep increments step', () => {
      useCrystalStore.getState().startProgramming(0, 'X');
      useCrystalStore.getState().advanceProgrammingStep();
      useCrystalStore.getState().advanceProgrammingStep();
      expect(useCrystalStore.getState().programming.step).toBe(2);
    });

    it('completeProgramming resets', () => {
      useCrystalStore.getState().startProgramming(0, 'X');
      useCrystalStore.getState().advanceProgrammingStep();
      useCrystalStore.getState().completeProgramming();
      const p = useCrystalStore.getState().programming;
      expect(p.isActive).toBe(false);
      expect(p.crystalIndex).toBe(null);
      expect(p.intention).toBe('');
      expect(p.step).toBe(0);
    });
  });

  describe('attunement', () => {
    it('startAttunement resets to step 0, currentChakra=root', () => {
      useCrystalStore.setState({
        attunement: { isActive: false, step: 5, totalSteps: 7, chakras: ['root','sacral','solar_plexus','heart','throat','third_eye','crown'], currentChakra: 'heart' },
      });
      useCrystalStore.getState().startAttunement();
      const a = useCrystalStore.getState().attunement;
      expect(a.isActive).toBe(true);
      expect(a.step).toBe(0);
      expect(a.currentChakra).toBe('root');
    });

    it('advanceAttunementStep progresses chakras', () => {
      useCrystalStore.getState().startAttunement();
      useCrystalStore.getState().advanceAttunementStep();
      expect(useCrystalStore.getState().attunement.currentChakra).toBe('sacral');
      useCrystalStore.getState().advanceAttunementStep();
      expect(useCrystalStore.getState().attunement.currentChakra).toBe('solar_plexus');
    });

    it('advanceAttunementStep ends attunement at last step', () => {
      useCrystalStore.getState().startAttunement();
      for (let i = 0; i < 6; i++) {
        useCrystalStore.getState().advanceAttunementStep();
      }
      useCrystalStore.getState().advanceAttunementStep();
      const a = useCrystalStore.getState().attunement;
      expect(a.isActive).toBe(false);
      expect(a.step).toBe(0);
    });

    it('stopAttunement resets without progressing', () => {
      useCrystalStore.getState().startAttunement();
      useCrystalStore.getState().stopAttunement();
      const a = useCrystalStore.getState().attunement;
      expect(a.isActive).toBe(false);
      expect(a.step).toBe(0);
    });
  });

  describe('meditation breath cycle', () => {
    it('startMeditation initializes', () => {
      useCrystalStore.getState().startMeditation(60);
      const m = useCrystalStore.getState().meditation;
      expect(m.isActive).toBe(true);
      expect(m.duration).toBe(60);
      expect(m.elapsed).toBe(0);
      expect(m.breathPhase).toBe('inhale');
      expect(m.breathCount).toBe(0);
    });

    it('updateMeditation computes inhale phase (0-4s)', () => {
      useCrystalStore.getState().startMeditation(60);
      useCrystalStore.getState().updateMeditation(2);
      expect(useCrystalStore.getState().meditation.breathPhase).toBe('inhale');
    });

    it('updateMeditation computes hold phase (4-8s)', () => {
      useCrystalStore.getState().startMeditation(60);
      useCrystalStore.getState().updateMeditation(6);
      expect(useCrystalStore.getState().meditation.breathPhase).toBe('hold');
    });

    it('updateMeditation computes exhale phase (8-12s)', () => {
      useCrystalStore.getState().startMeditation(60);
      useCrystalStore.getState().updateMeditation(10);
      expect(useCrystalStore.getState().meditation.breathPhase).toBe('exhale');
    });

    it('updateMeditation cycles breathCount at 12s boundaries', () => {
      useCrystalStore.getState().startMeditation(120);
      useCrystalStore.getState().updateMeditation(11);
      expect(useCrystalStore.getState().meditation.breathCount).toBe(0);
      useCrystalStore.getState().updateMeditation(13);
      expect(useCrystalStore.getState().meditation.breathCount).toBe(1);
    });

    it('stopMeditation resets', () => {
      useCrystalStore.getState().startMeditation(60);
      useCrystalStore.getState().updateMeditation(10);
      useCrystalStore.getState().stopMeditation();
      const m = useCrystalStore.getState().meditation;
      expect(m.isActive).toBe(false);
      expect(m.elapsed).toBe(0);
    });
  });

  describe('crystal library lookups', () => {
    it('crystalLibrary has 8 crystals', () => {
      const lib = useCrystalStore.getState().crystalLibrary;
      expect(lib).toHaveLength(8);
    });

    it('getCrystalByType returns matching crystal', () => {
      const c = useCrystalStore.getState().getCrystalByType('amethyst');
      expect(c).toBeDefined();
      expect(c.id).toBe('amethyst');
      expect(c.chakras).toContain('third_eye');
    });

    it('getCrystalByType returns undefined for unknown type', () => {
      expect(useCrystalStore.getState().getCrystalByType('unobtanium')).toBeUndefined();
    });

    it('getCrystalsByChakra filters by chakra', () => {
      const heart = useCrystalStore.getState().getCrystalsByChakra('heart');
      expect(heart.length).toBeGreaterThan(0);
      expect(heart.every(c => c.chakras.includes('heart'))).toBe(true);
    });

    it('getCrystalsByProperty filters by property', () => {
      const prot = useCrystalStore.getState().getCrystalsByProperty('protection');
      expect(prot.length).toBeGreaterThan(0);
      expect(prot.every(c => c.properties.includes('protection'))).toBe(true);
    });
  });
});
