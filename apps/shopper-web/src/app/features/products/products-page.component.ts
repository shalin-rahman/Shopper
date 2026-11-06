import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslocoPipe } from '@ngneat/transloco';

import { LocaleService } from '../../core/i18n/locale.service';
import { Product, ProductService, filterProducts } from './product.service';

import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';

@Component({
  selector: 'app-products-page',
  standalone: true,
  imports: [
    CommonModule, 
    FormsModule, 
    TranslocoPipe, 
    ShopperButtonComponent, 
    ShopperDataGridComponent
  ],
  templateUrl: './products-page.component.html',
})
export class ProductsPageComponent implements OnInit {
  private readonly productsApi = inject(ProductService);
  readonly locale = inject(LocaleService);

  readonly items = signal<Product[]>([]);
  readonly loadError = signal<string | null>(null);
  readonly saving = signal(false);
  readonly formError = signal<string | null>(null);
  readonly query = signal('');
  readonly visible = computed(() => filterProducts(this.items(), this.query()));
  /** Ids with a marketplace change in flight, so a second click can't race the first. */
  readonly toggling = signal<ReadonlySet<string>>(new Set());

  sku = '';
  nameEn = '';
  nameBn = '';
  sellPrice: number | null = null;
  vatRate = 0;

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loadError.set(null);
    this.productsApi.list().subscribe({
      next: (rows) => this.items.set(rows),
      error: () => this.loadError.set('products.loadFailed'),
    });
  }

  labelName(p: Product): string {
    return this.locale.activeLang() === 'bn' ? p.name_bn : p.name_en;
  }

  submit(): void {
    this.formError.set(null);
    const sku = this.sku.trim();
    const nameEn = this.nameEn.trim();
    const nameBn = this.nameBn.trim();
    if (!sku || !nameEn || !nameBn) {
      this.formError.set('products.formRequired');
      return;
    }
    this.saving.set(true);
    this.productsApi
      .create({
        sku,
        name_en: nameEn,
        name_bn: nameBn,
        sell_price: this.sellPrice,
        vat_rate_pct: this.vatRate,
      })
      .subscribe({
        next: () => {
          this.sku = '';
          this.nameEn = '';
          this.nameBn = '';
          this.sellPrice = null;
          this.vatRate = 0;
          this.saving.set(false);
          this.reload();
        },
        error: () => {
          this.saving.set(false);
          this.formError.set('products.saveFailed');
        },
      });
  }

  toggleMarketplace(p: Product): void {
    if (this.toggling().has(p.id)) return;
    this.toggling.update((s) => new Set(s).add(p.id));
    const done = () =>
      this.toggling.update((s) => {
        const next = new Set(s);
        next.delete(p.id);
        return next;
      });
    this.productsApi.setMarketplace(p.id, !p.marketplace_enabled).subscribe({
      next: (updated) => {
        this.items.update((rows) => rows.map((r) => (r.id === updated.id ? updated : r)));
        done();
      },
      error: () => {
        this.loadError.set('products.marketplaceFailed');
        done();
      },
    });
  }

  deactivate(p: Product): void {
    if (!confirm(`Deactivate ${p.sku}?`)) {
      return;
    }
    this.productsApi.deactivate(p.id).subscribe({
      next: () => this.reload(),
      error: () => this.loadError.set('products.loadFailed'),
    });
  }
}
