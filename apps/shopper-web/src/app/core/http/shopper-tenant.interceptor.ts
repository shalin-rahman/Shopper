import { HttpInterceptorFn } from '@angular/common/http';
import { environment } from '../../../environments/environment';

export const shopperTenantInterceptor: HttpInterceptorFn = (req, next) => {
  const tenant = (environment as { devTenantSubdomain?: string }).devTenantSubdomain;
  if (tenant) {
    return next(req.clone({ setHeaders: { 'X-Shopper-Tenant': tenant } }));
  }
  return next(req);
};
