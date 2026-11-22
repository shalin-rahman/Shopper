import { NAV_ITEMS } from '../src/app/core/nav/nav-items';
import { expect, test } from './fixtures';

const WIDTHS = [360, 390, 1440];
const ROUTES = [...new Set([...NAV_ITEMS.map((n) => n.path), '/settings'])];

for (const width of WIDTHS) {
  test.describe(`${width} px, Bangla`, () => {
    test.use({ viewport: { width, height: 800 } });

    for (const path of ROUTES) {
      test(`${path} has no sideways scroll`, async ({ page, pageErrors }) => {
        await page.goto(path);
        await expect(page.locator('main')).toBeVisible();
        await expect(page.locator('html')).toHaveAttribute('lang', 'bn-BD');
        await page.waitForLoadState('networkidle');

        if (process.env['E2E_SHOTS']) {
          const name = path === '/' ? 'home' : path.slice(1);
          await page.screenshot({ path: `test-results/shots/${width}-${name}.png`, fullPage: true });
        }

        const { scrollWidth, innerWidth, wide } = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
          // Leaf-most elements past the right edge, to name the culprit in the failure.
          wide: [...document.querySelectorAll('body *')]
            .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1)
            .filter((el) => {
              for (let p = el.parentElement; p; p = p.parentElement) {
                if (['auto', 'scroll', 'hidden', 'clip'].includes(getComputedStyle(p).overflowX)) return false;
              }
              return true;
            })
            .filter((el) => ![...el.children].some((c) => c.getBoundingClientRect().right > window.innerWidth + 1))
            .slice(0, 5)
            .map((el) => `${el.tagName.toLowerCase()}.${[...el.classList].join('.')} "${el.textContent?.trim().slice(0, 30)}"`),
        }));
        expect(scrollWidth, `page is ${scrollWidth - innerWidth} px too wide: ${wide.join(' | ')}`).toBeLessThanOrEqual(innerWidth);

        const spaced = await page.evaluate(() =>
          [...document.querySelectorAll('body *')]
            .filter((el) => el.closest(':lang(bn)') && getComputedStyle(el).letterSpacing !== 'normal')
            .filter((el) => !el.matches('.field__control--figures'))
            .slice(0, 5)
            .map((el) => `${el.tagName.toLowerCase()} "${el.textContent?.trim().slice(0, 30)}"`),
        );
        expect(spaced, 'Bangla text with letter-spacing').toEqual([]);
        expect(pageErrors).toEqual([]);
      });
    }
  });
}

test.describe('settings at 360 px', () => {
  test.use({ viewport: { width: 360, height: 800 } });

  test('saving one changed field sends only that field', async ({ page, settingsPatches }) => {
    await page.goto('/settings');
    const bin = page.locator('input[name="bin"]');
    await expect(bin).toHaveValue('123');
    await bin.fill('456');
    await page.locator('button[type="submit"]').click();

    await expect.poll(() => settingsPatches.length).toBe(1);
    expect(settingsPatches[0]).toEqual({ bin: '456' });
  });
});
