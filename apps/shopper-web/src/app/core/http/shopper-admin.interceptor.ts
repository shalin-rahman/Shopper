import { HttpInterceptorFn } from '@angular/common/http';

/** Session-only storage for platform admin API key (never commit real keys). */
export const SHOPPER_ADMIN_KEY_STORAGE = 'shopper.adminKey';

export const shopperAdminInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.includes('/v1/admin')) {
    return next(req);
  }
  const key = sessionStorage.getItem(SHOPPER_ADMIN_KEY_STORAGE)?.trim();
  if (!key) {
    return next(req);
  }
  return next(req.clone({ setHeaders: { 'X-Shopper-Admin-Key': key } }));
};
