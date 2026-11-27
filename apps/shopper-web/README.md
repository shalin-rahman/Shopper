# ShopperWeb

Staff web app for Shopper. Angular 17 (standalone components, signals), Tailwind 3.4, Transloco (English and Bangla).

## Commands

Run these in `apps/shopper-web`.

| What | Command |
| --- | --- |
| Dev server | `npx ng serve` (http://localhost:4200) |
| Unit tests | `npx ng test --watch=false --browsers=ChromeHeadless` |
| Type-check | `npx tsc -p tsconfig.app.json --noEmit` |
| Build | `npx ng build` |

## Themes and styling

- There are 12 themes. Each one sets six tokens in `src/styles.scss`: `--shopper-primary`, `-bg`, `-text`, `-accent`, `-surface`, `-border`. Tokens made from these (`--shopper-muted`, `-tint`, `-focus-ring`, `-danger`) are defined there too.
- A theme also applies to any element with its own `data-theme="name"`. The theme dots in the header and the swatches on /settings use this to show other themes.
- `tailwind.config.js` maps the `shopper-*` colors to the tokens. Opacity works through `color-mix`, so `bg-shopper-primary/10` and `hover:bg-shopper-primary` are fine to use.
- Do not hardcode colors the tokens already cover. Every theme must keep working, including the dark ones (midnight, cyberpunk).
- Shared form parts (`.field`, `.notice`, `.segmented`, `.switch`, `.muted`) live in `src/styles.scss`. Component styles have a 2 kB warning budget and a 4 kB error budget.

## Layout

- The header has a top bar and a nav row under it. The nav row scrolls sideways on narrow screens, so new links never widen the page. The header is about 106 px tall, so sticky parts of a page need `lg:top-32`.
- Bangla labels are the longest. Check every new page at 360 px wide in Bangla and make sure the page does not scroll sideways.
- In a CSS grid, use `minmax(0, 1fr)` tracks so long text cannot push the page wider.

## Translations

Strings live in `src/assets/i18n/en.json` and `bn.json`. Add every key to both files.

## Login, roles and tenant settings
- Staff log in at `/login`. The token is kept in sessionStorage (`shopper.token`); its `role` claim (`cashier`, `accountant`, `manager`, `admin`) is read by `AuthService.role`.
- `/checkout/:id` (customer pay link) and `/admin/tenants` (platform admin, uses its own API key) need no staff login.
- Tenant settings: `core/tenant/tenant-settings.store.ts` is the one place that holds them. They load after login, and any staff role can read them. The user's own saved theme wins over the shop theme.
- Nav: `core/nav/nav-items.ts` lists the links. A link shows only if the user's role is allowed and its module is on. A missing `module_access` key counts as on. `moduleGuard` and `roleGuard` in `core/nav/module.guard.ts` guard the routes. This only hides things in the web app; the API does not check modules. The Admin link is not in the staff nav.
- `unsavedChangesGuard` in `core/nav/unsaved-changes.guard.ts` asks before leaving a form with unsaved changes. /settings uses it.
- Payment results: the gateway returns to the API, which sends the browser to `/checkout/result?status=success|fail|cancel`.

## Tests
- Unit: `npx ng test --watch=false --browsers=ChromeHeadless`. `core/i18n/i18n-keys.spec.ts` fails if `en.json` and `bn.json` have different keys.
- Browser: `npm run e2e` (Playwright). It starts `ng serve` on port 4300 and stubs every API call, so it needs no database. Each page is checked for sideways scroll at 360, 390 and 1440 px, and Bangla text must have no letter-spacing. Set `E2E_SHOTS=1` to save screenshots to `test-results/shots/`.
- Last run 2026-11-22: unit 97 passed, e2e 37 passed, `ng build` passed.
