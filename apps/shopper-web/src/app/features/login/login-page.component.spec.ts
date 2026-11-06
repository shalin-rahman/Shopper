import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../../core/auth/auth.service';
import { LoginPageComponent } from './login-page.component';

describe('LoginPageComponent', () => {
  let auth: jasmine.SpyObj<AuthService>;
  let router: jasmine.SpyObj<Router>;

  function make(next: string | null) {
    auth = jasmine.createSpyObj<AuthService>('AuthService', ['login']);
    router = jasmine.createSpyObj<Router>('Router', ['navigateByUrl']);
    router.navigateByUrl.and.resolveTo(true);
    TestBed.configureTestingModule({
      imports: [LoginPageComponent, TranslocoTestingModule.forRoot({ langs: { en: {} } })],
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(next ? { next } : {}) } },
        },
      ],
    });
    return TestBed.createComponent(LoginPageComponent).componentInstance;
  }

  it('goes to the page it came from after login', () => {
    const page = make('/invoices');
    auth.login.and.returnValue(of(undefined));
    page.username = 'rina';
    page.password = 'pw';
    page.submit();
    expect(auth.login).toHaveBeenCalledWith('rina', 'pw');
    expect(router.navigateByUrl).toHaveBeenCalledWith('/invoices');
  });

  it('ignores a next link that leaves the app', () => {
    const page = make('//evil.example');
    auth.login.and.returnValue(of(undefined));
    page.username = 'rina';
    page.password = 'pw';
    page.submit();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/');
  });

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
  });

  it('does not call the API with an empty form', () => {
    const page = make(null);
    page.username = '  ';
    page.password = 'pw';
    page.submit();
    expect(auth.login).not.toHaveBeenCalled();
  });
});
