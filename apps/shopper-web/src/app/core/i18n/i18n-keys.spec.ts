import en from '../../../assets/i18n/en.json';
import bn from '../../../assets/i18n/bn.json';

function flatKeys(obj: unknown, prefix = ''): string[] {
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
    return [prefix];
  }
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    flatKeys(v, prefix ? `${prefix}.${k}` : k),
  );
}

describe('i18n key parity', () => {
  it('flattens nested objects into dotted keys', () => {
    expect(flatKeys({ a: { b: 'x', c: { d: 'y' } }, e: 'z' }).sort()).toEqual(['a.b', 'a.c.d', 'e']);
  });

  it('en.json and bn.json have the same keys', () => {
    const enKeys = new Set(flatKeys(en));
    const bnKeys = new Set(flatKeys(bn));
    const missingInBn = [...enKeys].filter((k) => !bnKeys.has(k));
    const missingInEn = [...bnKeys].filter((k) => !enKeys.has(k));
    expect(missingInBn).withContext('keys missing in bn.json').toEqual([]);
    expect(missingInEn).withContext('keys missing in en.json').toEqual([]);
  });

  it('bn.json has no empty values', () => {
    const empty = flatKeys(bn).filter((k) => {
      const v = k.split('.').reduce<unknown>((o, p) => (o as Record<string, unknown>)?.[p], bn);
      return typeof v === 'string' && v.trim() === '';
    });
    expect(empty).toEqual([]);
  });
});
