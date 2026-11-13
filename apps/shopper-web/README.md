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
- Known gaps (2026-11-13), planned in the [master plan](../../docs/superpowers/plans/2026-11-13-master-plan.md):
  - Tenant settings load at app start, before login, and the API lets only managers read them, so most staff never get the shop's theme or language (A1, B1).
  - Every nav link shows to every role, and modules switched off in settings still show (B2). With `module_access = {}` the settings page shows no module switches (B2).
  - Several pages still have English-only text (B4, B5).
