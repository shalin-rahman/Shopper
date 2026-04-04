import { DOCUMENT } from '@angular/common';
import { Injectable, inject } from '@angular/core';
import { TranslocoService } from '@ngneat/transloco';

export type ShopperLang = 'en' | 'bn';

@Injectable({ providedIn: 'root' })
export class LocaleService {
  private readonly doc = inject(DOCUMENT);
  private readonly transloco = inject(TranslocoService);

  private readonly storageKey = 'shopper.lang';

  /** Bangla and English are LTR; return `rtl` when you add Arabic/Hebrew, etc. */
  textDirectionFor(lang: ShopperLang): 'ltr' | 'rtl' {
    return 'ltr';
  }

  /** Restore language before first paint when possible. */
  hydrateFromStorage(): void {
    const raw = localStorage.getItem(this.storageKey);
    if (raw === 'bn' || raw === 'en') {
      this.setLanguage(raw, { persist: false });
    }
  }

  setLanguage(lang: ShopperLang, opts: { persist?: boolean } = {}): void {
    const persist = opts.persist ?? true;
    this.transloco.setActiveLang(lang);

    const html = this.doc.documentElement;
    html.setAttribute('lang', lang === 'bn' ? 'bn-BD' : 'en-BD');
    html.setAttribute('dir', this.textDirectionFor(lang));

    if (persist) {
      localStorage.setItem(this.storageKey, lang);
    }
  }

  activeLang(): ShopperLang {
    const lang = this.transloco.getActiveLang();
    return lang === 'bn' ? 'bn' : 'en';
  }

  /** Bangladesh Taka (৳) with locale-aware digits and grouping. */
  formatCurrency(value: number): string {
    const lang = this.activeLang();
    const locale = lang === 'bn' ? 'bn-BD' : 'en-BD';
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: 'BDT',
      currencyDisplay: 'narrowSymbol',
    }).format(value);
  }

  /**
   * South Asian grouping (lakh/crore style) for financial figures in English UI.
   * For Bangla active language, uses bn-BD native grouping.
   */
  formatDecimal(value: number, fractionDigits = 2): string {
    const lang = this.activeLang();
    if (lang === 'bn') {
      return new Intl.NumberFormat('bn-BD', {
        minimumFractionDigits: fractionDigits,
        maximumFractionDigits: fractionDigits,
      }).format(value);
    }
    return new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    }).format(value);
  }

  formatDate(value: Date, pattern: 'short' | 'medium' = 'medium'): string {
    const lang = this.activeLang();
    const locale = lang === 'bn' ? 'bn-BD' : 'en-BD';
    const dateStyle = pattern === 'short' ? 'short' : 'medium';
    return new Intl.DateTimeFormat(locale, { dateStyle }).format(value);
  }
}
