import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslocoPipe } from '@ngneat/transloco';

import {
  TenantSettingsDto,
  TenantSettingsService,
  TenantSettingsUpdate,
} from '../../core/tenant/tenant-settings.service';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';

export const SETTINGS_THEMES = [
  'default', 'midnight', 'emerald', 'ruby', 'cyberpunk', 'amber',
  'lavender', 'ocean', 'sunset', 'forest', 'slate', 'gold',
] as const;

/** Fixed receipt wording, copied from apps/api/routers/receipts.py so the preview matches the print. */
export const RECEIPT_TEXT = {
  en: { bin: 'BIN:', mushak: 'Mushak 6.3 - Tax Invoice' },
  bn: { bin: 'বিআইএন:', mushak: 'মূসক ৬.৩ - কর চালান' },
} as const;

/** Modules with a translated name. Others show their key. */
const NAMED_MODULES = new Set(['pos', 'inventory']);

interface SettingsForm {
  theme_id: string;
  default_language: 'en' | 'bn';
  logo_url: string;
  legal_title_en: string;
  legal_title_bn: string;
  bin: string;
  default_vat_rate_pct: number | null;
  module_access: Record<string, boolean>;
}

function toForm(s: TenantSettingsDto): SettingsForm {
  const modules: Record<string, boolean> = {};
  for (const [key, value] of Object.entries(s.module_access ?? {})) {
    modules[key] = value === true;
  }
  return {
    theme_id: s.theme_id,
    default_language: s.default_language === 'bn' ? 'bn' : 'en',
    logo_url: s.logo_url ?? '',
    legal_title_en: s.legal_title_en ?? '',
    legal_title_bn: s.legal_title_bn ?? '',
    bin: s.bin ?? '',
    default_vat_rate_pct: Number(s.default_vat_rate_pct),
    module_access: modules,
  };
}

/** Empty text means "clear it", which the API stores as null. */
function textOrNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

@Component({
  selector: 'app-settings-page',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslocoPipe, ShopperButtonComponent],
  templateUrl: './settings-page.component.html',
  styleUrl: './settings-page.component.scss',
})
export class SettingsPageComponent implements OnInit {
  private readonly api = inject(TenantSettingsService);

  readonly themes = SETTINGS_THEMES;
  readonly receiptText = RECEIPT_TEXT;
  readonly loaded = signal(false);
  /** The logo URL that last failed to load, so the preview can say so. */
  readonly brokenLogo = signal<string | null>(null);
  readonly saving = signal(false);
  /** `text` is the API's own reason and wins over `key`. */
  readonly message = signal<{ key: string; text?: string; error: boolean } | null>(null);

  form: SettingsForm | null = null;
  private original: SettingsForm | null = null;

  ngOnInit(): void {
    this.api.load().subscribe({
      next: (s) => this.reset(s),
      error: () => this.message.set({ key: 'settings.loadFailed', error: true }),
    });
  }

  moduleKeys(): string[] {
    return this.form ? Object.keys(this.form.module_access).sort() : [];
  }

  /** Translation key for a module's name, or null when only the raw key is known. */
  moduleLabel(key: string): string | null {
    return NAMED_MODULES.has(key) ? `settings.moduleNames.${key}` : null;
  }

  /**
   * The name the receipt prints, by the same rule as the server: Bangla falls back
   * to English; empty means the shop's web address prints instead.
   */
  receiptTitle(): string {
    const f = this.form;
    if (!f) {
      return '';
    }
    const en = f.legal_title_en.trim();
    return f.default_language === 'bn' ? f.legal_title_bn.trim() || en : en;
  }

  /** A cleared VAT field counts too, so Save stays enabled and can report the range error. */
  dirtyCount(): number {
    const vatCleared = this.form?.default_vat_rate_pct === null ? 1 : 0;
    return Object.keys(this.changes()).length + vatCleared;
  }

  discard(): void {
    if (this.original) {
      this.form = structuredClone(this.original);
    }
    this.message.set(null);
  }

  /** Builds a PATCH body with only the fields the user changed. */
  changes(): TenantSettingsUpdate {
    const f = this.form;
    const o = this.original;
    if (!f || !o) {
      return {};
    }
    const out: TenantSettingsUpdate = {};
    if (f.theme_id !== o.theme_id) out.theme_id = f.theme_id;
    if (f.default_language !== o.default_language) out.default_language = f.default_language;
    for (const key of ['logo_url', 'legal_title_en', 'legal_title_bn', 'bin'] as const) {
      if (f[key].trim() !== o[key]) out[key] = textOrNull(f[key]);
    }
    if (f.default_vat_rate_pct !== o.default_vat_rate_pct && f.default_vat_rate_pct !== null) {
      out.default_vat_rate_pct = f.default_vat_rate_pct;
    }
    if (JSON.stringify(f.module_access) !== JSON.stringify(o.module_access)) {
      out.module_access = { ...f.module_access };
    }
    return out;
  }

  save(): void {
    this.message.set(null);
    const f = this.form;
    if (!f) {
      return;
    }
    const vat = f.default_vat_rate_pct;
    if (vat === null || !(vat >= 0 && vat <= 100)) {
      this.message.set({ key: 'settings.vatRange', error: true });
      return;
    }
    const body = this.changes();
    if (!Object.keys(body).length) {
      this.message.set({ key: 'settings.noChanges', error: false });
      return;
    }
    this.saving.set(true);
    this.api.update(body).subscribe({
      next: (s) => {
        this.reset(s);
        document.documentElement.setAttribute('data-theme', s.theme_id);
        this.message.set({ key: 'settings.saved', error: false });
        this.saving.set(false);
      },
      error: (err: unknown) => {
        const detail = err instanceof HttpErrorResponse ? err.error?.detail : undefined;
        this.message.set({
          key: 'settings.saveFailed',
          text: typeof detail === 'string' ? detail : undefined,
          error: true,
        });
        this.saving.set(false);
      },
    });
  }

  private reset(s: TenantSettingsDto): void {
    this.form = toForm(s);
    this.original = toForm(s);
    this.loaded.set(true);
  }
}
