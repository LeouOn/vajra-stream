/**
 * Unit tests for utility modules.
 */
import { describe, it, expect } from 'vitest';
import { API_BASE, WS_URL, BACKEND_PORT } from '../utils/api';
import { audioFeedback } from '../utils/audioFeedback';

describe('api', () => {
  it('API_BASE is a string ending with /api/v1', () => {
    expect(typeof API_BASE).toBe('string');
    expect(API_BASE).toMatch(/\/api\/v1$/);
  });

  it('WS_URL is a string starting with ws', () => {
    expect(typeof WS_URL).toBe('string');
    expect(WS_URL).toMatch(/^ws/);
  });

  it('BACKEND_PORT is a string', () => {
    expect(typeof BACKEND_PORT).toBe('string');
  });
});

describe('audioFeedback', () => {
  it('is an instance of AudioFeedbackEngine', () => {
    expect(audioFeedback).toBeDefined();
    expect(typeof audioFeedback.playClick).toBe('function');
    expect(typeof audioFeedback.playTick).toBe('function');
  });

  it('can be enabled and disabled', () => {
    audioFeedback.disable();
    expect(audioFeedback.enabled).toBe(false);
    audioFeedback.enable();
    expect(audioFeedback.enabled).toBe(true);
  });

  it('playTick does not throw when disabled', () => {
    audioFeedback.disable();
    expect(() => audioFeedback.playTick()).not.toThrow();
    audioFeedback.enable();
  });

  it('playClick does not throw when disabled', () => {
    audioFeedback.disable();
    expect(() => audioFeedback.playClick()).not.toThrow();
    audioFeedback.enable();
  });

  it('playSuccess does not throw', () => {
    expect(() => audioFeedback.playSuccess()).not.toThrow();
  });

  it('playError does not throw', () => {
    expect(() => audioFeedback.playError()).not.toThrow();
  });

  it('playDialAdjust does not throw', () => {
    expect(() => audioFeedback.playDialAdjust(50, 0, 100)).not.toThrow();
  });

  it('playTabChange does not throw', () => {
    expect(() => audioFeedback.playTabChange()).not.toThrow();
  });
});
