import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { provideTransloco } from '@ngneat/transloco';

import { AppComponent } from './app.component';
import { shopperTenantInterceptor } from './core/http/shopper-tenant.interceptor';
import { ShopperTranslocoHttpLoader } from './core/i18n/transloco-loader';

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideHttpClient(withInterceptors([shopperTenantInterceptor])),
        provideHttpClientTesting(),
        provideRouter([]),
        provideTransloco({
          config: {
            availableLangs: ['en', 'bn'],
            defaultLang: 'en',
            reRenderOnLangChange: true,
            prodMode: true,
          },
          loader: ShopperTranslocoHttpLoader,
        }),
      ],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
