/**
 * Deterministic pseudo-random generator.
 *
 * Mock data must be byte-identical on the server and the client, otherwise
 * React hydrates a mismatched tree. A seeded mulberry32 keeps the dataset
 * stable across builds and renders while still looking organic.
 */

export function createRng(seed: number) {
  let state = seed >>> 0;

  return function next(): number {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type Rng = () => number;

export const pick = <T>(rng: Rng, items: readonly T[]): T =>
  items[Math.floor(rng() * items.length)] as T;

export const pickMany = <T>(rng: Rng, items: readonly T[], count: number): T[] => {
  const pool = [...items];
  const out: T[] = [];
  for (let i = 0; i < count && pool.length > 0; i++) {
    out.push(pool.splice(Math.floor(rng() * pool.length), 1)[0] as T);
  }
  return out;
};

/** Inclusive integer range. */
export const intIn = (rng: Rng, min: number, max: number): number =>
  Math.floor(rng() * (max - min + 1)) + min;

/** Float range. */
export const floatIn = (rng: Rng, min: number, max: number, digits = 1): number => {
  const factor = 10 ** digits;
  return Math.round((min + rng() * (max - min)) * factor) / factor;
};

/** True with the given probability. */
export const chance = (rng: Rng, probability: number): boolean => rng() < probability;

/** Bell-ish distribution around a midpoint — used for runtime/memory samples. */
export const around = (rng: Rng, midpoint: number, spread: number): number =>
  midpoint + (rng() + rng() - 1) * spread;
