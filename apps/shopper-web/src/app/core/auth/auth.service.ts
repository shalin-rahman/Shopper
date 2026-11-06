import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../../environments/environment';

export const SHOPPER_TOKEN_STORAGE = 'shopper.token';

interface TokenClaims {
  uid?: string;
  tid?: string;
  role?: string;
  exp?: number;
}

function readClaims(token: string | null): TokenClaims | null {
  if (!token) return null;
  try {
    const part = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(part.padEnd(part.length + ((4 - (part.length % 4)) % 4), '=')));
  } catch {
    return null;
  }
}

function loadToken(): string | null {
  try {
    return sessionStorage.getItem(SHOPPER_TOKEN_STORAGE);
  } catch {
    return null;
  }
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly raw = signal<string | null>(loadToken());

  /** The token, or null when there is none or it has expired. */
  readonly token = computed(() => {
    const token = this.raw();
    const claims = readClaims(token);
    if (!claims) return null;
    if (claims.exp !== undefined && claims.exp * 1000 <= Date.now()) return null;
    return token;
  });
  readonly role = computed(() => readClaims(this.token())?.role ?? null);

  isLoggedIn(): boolean {
    // Reload on each check, so a token that expired since the last change counts as gone.
    this.raw.set(loadToken());
    return this.token() !== null;
  }

  login(username: string, password: string): Observable<void> {
    return this.http
      .post<{ access_token: string }>(`${environment.apiBaseUrl}/v1/tenant/auth/login`, {
        username: username.trim(),
        password,
      })
      .pipe(
        map((res) => {
          sessionStorage.setItem(SHOPPER_TOKEN_STORAGE, res.access_token);
          this.raw.set(res.access_token);
        }),
      );
  }

  logout(): void {
    try {
      sessionStorage.removeItem(SHOPPER_TOKEN_STORAGE);
    } catch {
      // Storage blocked; the in-memory token is still cleared.
    }
    this.raw.set(null);
  }
}
