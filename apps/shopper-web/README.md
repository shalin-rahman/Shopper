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
