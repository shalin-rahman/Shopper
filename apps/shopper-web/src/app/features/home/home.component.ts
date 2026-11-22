import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@ngneat/transloco';

import { LocaleService } from '../../core/i18n/locale.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [TranslocoPipe, RouterLink],
  templateUrl: './home.component.html',
})
export class HomeComponent {
  readonly locale = inject(LocaleService);

  readonly stats: { label: string; value: number; icon: string; trend: string; trendKey?: string }[] = [
    { label: 'home.stats.sales', value: 450230.50, icon: '📈', trend: '+12%' },
    { label: 'home.stats.activeInvoices', value: 128, icon: '📄', trend: '+5' },
    { label: 'home.stats.inventoryValue', value: 890400.00, icon: '📦', trend: '', trendKey: 'home.trendStable' },
    { label: 'home.stats.vatDue', value: 67000.25, icon: '🏦', trend: '-2%' },
  ];

  readonly sampleAmount = 12_34_567.89;

  formattedCurrency(amt: number): string {
    return this.locale.formatCurrency(amt);
  }

  formattedDecimal(): string {
    return this.locale.formatDecimal(this.sampleAmount);
  }
}
