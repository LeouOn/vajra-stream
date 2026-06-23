/**
 * logger.test.ts — verifies the centralized logger wraps console.* correctly.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { logger, createLogger } from '../logger';

describe('logger', () => {
  let debugSpy: ReturnType<typeof vi.spyOn>;
  let infoSpy: ReturnType<typeof vi.spyOn>;
  let warnSpy: ReturnType<typeof vi.spyOn>;
  let errorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
    infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('prefixes messages with [vajra] + ISO timestamp', () => {
    logger.error('hello');
    expect(errorSpy).toHaveBeenCalledTimes(1);
    const args = errorSpy.mock.calls[0];
    expect(typeof args[0]).toBe('string');
    // ISO 8601 sanity check (rough — must start with a date and contain a 'T')
    expect(args[0] as string).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(args[1]).toBe('[vajra]');
    expect(args[2]).toBe('hello');
  });

  it('routes to correct console method per level', () => {
    logger.debug('d');
    logger.info('i');
    logger.warn('w');
    logger.error('e');
    expect(debugSpy).toHaveBeenCalledTimes(1);
    expect(infoSpy).toHaveBeenCalledTimes(1);
    expect(warnSpy).toHaveBeenCalledTimes(1);
    expect(errorSpy).toHaveBeenCalledTimes(1);
  });

  it('forwards multiple args unchanged', () => {
    const obj = { foo: 'bar' };
    const err = new Error('boom');
    logger.error('failed:', obj, err);
    const args = errorSpy.mock.calls[0];
    expect(args[2]).toBe('failed:');
    expect(args[3]).toBe(obj);
    expect(args[4]).toBe(err);
  });

  it('with() nests context in prefix', () => {
    const log = logger.with('ScalarTab');
    log.info('connecting');
    expect(infoSpy.mock.calls[0][1]).toBe('[vajra:ScalarTab]');
  });

  it('with() chains: A.with("B") gives [vajra:A:B]', () => {
    const log = logger.with('ScalarTab').with('useEffect');
    log.warn('retry');
    expect(warnSpy.mock.calls[0][1]).toBe('[vajra:ScalarTab:useEffect]');
  });

  it('createLogger returns a logger with root context', () => {
    const log = createLogger('MyComponent');
    log.warn('uh oh');
    expect(warnSpy.mock.calls[0][1]).toBe('[vajra:MyComponent]');
  });

  it('createLogger result can chain further .with()', () => {
    const log = createLogger('ScalarTab').with('inner');
    log.error('nested');
    expect(errorSpy.mock.calls[0][1]).toBe('[vajra:ScalarTab:inner]');
  });
});