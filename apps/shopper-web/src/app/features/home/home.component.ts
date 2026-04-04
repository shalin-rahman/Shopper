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
  private readonly locale = inject(LocaleService);

  readonly sampleAmount = 12_34_567.89;

  formattedCurrency(): string {
    return this.locale.formatCurrency(this.sampleAmount);
  }

  formattedDecimal(): string {
    return this.locale.formatDecimal(this.sampleAmount);
  }
}
