import { Component, inject } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';
import { TranslocoPipe } from '@ngneat/transloco';

import { LocaleService, ShopperLang } from './core/i18n/locale.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, TranslocoPipe],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  private readonly locale = inject(LocaleService);

  setLang(lang: ShopperLang): void {
    this.locale.setLanguage(lang);
  }
}
