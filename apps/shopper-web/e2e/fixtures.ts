import { test as base, expect } from '@playwright/test';

/** Same shape as the DTO in settings-page.component.spec.ts, with every module on so all pages open. */
export const SETTINGS = {
  tenant_id: 't1',
  theme_id: 'default',
  default_language: 'en',
  logo_url: null,
  legal_title_en: 'Acme Ltd',
  legal_title_bn: null,
  bin: '123',
  default_vat_rate_pct: '15.00',
  module_access: {},
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
};

function fakeJwt(role: string): string {
  const b64 = (o: object) => Buffer.from(JSON.stringify(o)).toString('base64url');
  const exp = Math.floor(Date.now() / 1000) + 3600;
  return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64({ uid: 'u1', tid: 't1', role, exp })}.sig`;
}

type Fixtures = {
  /** Bodies of PATCH /settings calls, in order. */
  settingsPatches: Record<string, unknown>[];
  /** Uncaught errors thrown in the page. */
  pageErrors: string[];
};

export const test = base.extend<Fixtures>({
  settingsPatches: async ({}, use) => {
    await use([]);
  },
  pageErrors: async ({ page }, use) => {
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await use(errors);
  },
  page: async ({ page, settingsPatches }, use) => {
    const token = fakeJwt('manager');
    await page.addInitScript((t) => {
      sessionStorage.setItem('shopper.token', t);
      localStorage.setItem('shopper.lang', 'bn');
    }, token);

    await page.route('**/api/v1/tenant/**', async (route) => {
      const req = route.request();
      if (new URL(req.url()).pathname.endsWith('/v1/tenant/settings')) {
        if (req.method() === 'PATCH') {
          const body = req.postDataJSON() as Record<string, unknown>;
          settingsPatches.push(body);
          return route.fulfill({ json: { ...SETTINGS, ...body } });
        }
        return route.fulfill({ json: SETTINGS });
      }
      return route.fulfill({ json: [] });
    });
    await use(page);
  },
});

export { expect };
