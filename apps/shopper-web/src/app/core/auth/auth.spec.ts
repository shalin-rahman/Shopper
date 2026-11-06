import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';

import { SHOPPER_TOKEN_STORAGE, AuthService } from './auth.service';
import { authInterceptor } from './auth.interceptor';
import { authGuard } from './auth.guard';

function fakeToken(claims: object): string {
  const body = btoa(JSON.stringify(claims)).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
  return `x.${body}.sig`;
}

const future = () => Math.floor(Date.now() / 1000) + 3600;

describe('auth', () => {
  let auth: AuthService;
  let http: HttpTestingController;
  let client: HttpClient;
  let router: Router;

  beforeEach(() => {
    sessionStorage.removeItem(SHOPPER_TOKEN_STORAGE);
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
    client = TestBed.inject(HttpClient);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    http.verify();
    sessionStorage.removeItem(SHOPPER_TOKEN_STORAGE);
  });

  it('logs in, keeps the token and reads the role', () => {
    const token = fakeToken({ role: 'manager', exp: future() });
    auth.login(' rina ', 'pw').subscribe();

    const req = http.expectOne('/api/v1/tenant/auth/login');
    expect(req.request.body).toEqual({ username: 'rina', password: 'pw' });
    expect(req.request.headers.has('Authorization')).toBeFalse();
    req.flush({ access_token: token });

    expect(sessionStorage.getItem(SHOPPER_TOKEN_STORAGE)).toBe(token);
    expect(auth.token()).toBe(token);
    expect(auth.role()).toBe('manager');
  });

  it('treats an expired token as logged out', () => {
    sessionStorage.setItem(SHOPPER_TOKEN_STORAGE, fakeToken({ role: 'admin', exp: 1 }));
    expect(auth.isLoggedIn()).toBeFalse();
    expect(auth.role()).toBeNull();
  });

  it('treats a garbled token as logged out', () => {
    sessionStorage.setItem(SHOPPER_TOKEN_STORAGE, 'not-a-jwt');
    expect(auth.isLoggedIn()).toBeFalse();
  });

  it('adds the bearer token to tenant calls only', () => {
    const token = fakeToken({ role: 'admin', exp: future() });
    sessionStorage.setItem(SHOPPER_TOKEN_STORAGE, token);
    auth.isLoggedIn();

    client.get('/api/v1/tenant/invoices').subscribe();
    client.get('/api/v1/storefront/checkout/1').subscribe();
    client.get('https://evil.example/v1/tenant/x').subscribe();

    expect(http.expectOne('/api/v1/tenant/invoices').request.headers.get('Authorization')).toBe(`Bearer ${token}`);
    expect(http.expectOne('/api/v1/storefront/checkout/1').request.headers.has('Authorization')).toBeFalse();
    expect(http.expectOne('https://evil.example/v1/tenant/x').request.headers.has('Authorization')).toBeFalse();
  });

  it('logs out and goes to /login on a 401', () => {
    sessionStorage.setItem(SHOPPER_TOKEN_STORAGE, fakeToken({ role: 'admin', exp: future() }));
    auth.isLoggedIn();
    const go = spyOn(router, 'navigate').and.resolveTo(true);

    client.get('/api/v1/tenant/invoices').subscribe({ error: () => undefined });
    http.expectOne('/api/v1/tenant/invoices').flush({ detail: 'x' }, { status: 401, statusText: 'Unauthorized' });

    expect(auth.token()).toBeNull();
    expect(go.calls.mostRecent().args[0]).toEqual(['/login']);
  });

  it('leaves a 401 alone when no token was sent', () => {
    const go = spyOn(router, 'navigate').and.resolveTo(true);

    client.get('/api/v1/tenant/settings').subscribe({ error: () => undefined });
    http.expectOne('/api/v1/tenant/settings').flush({ detail: 'x' }, { status: 401, statusText: 'Unauthorized' });

    expect(go).not.toHaveBeenCalled();
  });

  it('guard sends a guest to /login with the page to come back to', () => {
    const out = TestBed.runInInjectionContext(() => authGuard({} as never, { url: '/invoices' } as never));
    expect(out instanceof UrlTree).toBeTrue();
    expect(router.serializeUrl(out as UrlTree)).toBe('/login?next=%2Finvoices');
  });

  it('guard lets a logged-in user through', () => {
    sessionStorage.setItem(SHOPPER_TOKEN_STORAGE, fakeToken({ role: 'admin', exp: future() }));
    const out = TestBed.runInInjectionContext(() => authGuard({} as never, { url: '/invoices' } as never));
    expect(out).toBeTrue();
  });
});
