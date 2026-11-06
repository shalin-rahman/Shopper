import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

/**
 * Sends the staff token to tenant API calls. A 401 on a call that carried a token means the
 * session is over. A 401 without one is left to the caller, so a customer on a public page
 * (checkout) is not sent to /login by the startup settings call.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const tenantApi = `${environment.apiBaseUrl}/v1/tenant/`;
  if (!req.url.startsWith(tenantApi) || req.url === `${tenantApi}auth/login`) {
    return next(req);
  }
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.token();
  const sent = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;
  return next(sent).pipe(
    catchError((err: unknown) => {
      if (token && err instanceof HttpErrorResponse && err.status === 401) {
        auth.logout();
        void router.navigate(['/login'], { queryParams: { next: router.url } });
      }
      return throwError(() => err);
    }),
  );
};
