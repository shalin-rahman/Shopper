import { TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../../core/auth/auth.service';
import { TenantSettingsStore } from '../../core/tenant/tenant-settings.store';
import { LoginPageComponent } from './login-page.component';

describe('LoginPageComponent', () => {
  let auth: jasmine.SpyObj<AuthService>;
  let router: jasmine.SpyObj<Router>;
  let store: jasmine.SpyObj<TenantSettingsStore>;

  function make(next: string | null) {
    auth = jasmine.createSpyObj<AuthService>('AuthService', ['login']);
    router = jasmine.createSpyObj<Router>('Router', ['navigateByUrl']);
    router.navigateByUrl.and.resolveTo(true);
    store = jasmine.createSpyObj<TenantSettingsStore>('TenantSettingsStore', ['load']);
    store.load.and.resolveTo();
    TestBed.configureTestingModule({
      imports: [LoginPageComponent, TranslocoTestingModule.forRoot({ langs: { en: {} } })],
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
        { provide: TenantSettingsStore, useValue: store },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(next ? { next } : {}) } },
        },
      ],
    });
    return TestBed.createComponent(LoginPageComponent).componentInstance;
  }

  it('loads shop settings, then goes to the page it came from', fakeAsync(() => {
    const page = make('/invoices');
    auth.login.and.returnValue(of(undefined));
    page.username = 'rina';
    page.password = 'pw';
    page.submit();
    expect(auth.login).toHaveBeenCalledWith('rina', 'pw');
    expect(store.load).toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
    flushMicrotasks();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/invoices');
    expect(page.busy()).toBeFalse();
  }));

  it('ignores a next link that leaves the app', fakeAsync(() => {
    const page = make('//evil.example');
    auth.login.and.returnValue(of(undefined));
    page.username = 'rina';
    page.password = 'pw';
    page.submit();
    flushMicrotasks();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/');
  }));

  it('shows a bad-credentials message on 401 and clears the password', () => {
    const page = make(null);
    auth.login.and.returnValue(throwError(() => new HttpErrorResponse({ status: 401 })));
    page.username = 'rina';
    page.password = 'wrong';
    page.submit();
    expect(page.error()).toBe('login.badCredentials');
    expect(page.password).toBe('');
    expect(page.busy()).toBeFalse();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
    expect(store.load).not.toHaveBeenCalled();
  });

  it('does not call the API with an empty form', () => {
    const page = make(null);
    page.username = '  ';
    page.password = 'pw';
    page.submit();
    expect(auth.login).not.toHaveBeenCalled();
  });
});
