const memStore = new Map();
const localStoragePolyfill = {
  getItem: (k) => (memStore.has(k) ? memStore.get(k) : null),
  setItem: (k, v) => memStore.set(k, String(v)),
  removeItem: (k) => memStore.delete(k),
  clear: () => memStore.clear(),
  key: (i) => Array.from(memStore.keys())[i] || null,
  get length() { return memStore.size; },
};
try { globalThis.localStorage = localStoragePolyfill; } catch {}
try { global.localStorage = localStoragePolyfill; } catch {}
