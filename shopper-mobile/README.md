# shopper_mobile

Flutter POS app for Shopper. It keeps products and sales in a local database (drift) and sends finished sales to the API with offline-punch.

## Commands
- `flutter pub get`
- `flutter test` and `flutter analyze` (both passed on 2026-10-24)
- `flutter run`

## Status against the API (2026-11-13)
The app does not yet work against the real API. Its tests pass because they use mocks.
- The base URL is fixed to `https://api.shopper.com/v1`, and no tenant is sent. The API reads the tenant from the host, so every call is refused.
- Login posts `{email, password}` to `/v1/auth/login`. The API takes `{username, password}` at `/v1/tenant/auth/login` and returns only `access_token`.
- `/auth/refresh`, `/auth/me`, `/products` and `/orders` do not exist in the API.

Fix: master plan sessions E1 to E4 ([plan](../docs/superpowers/plans/2026-11-13-master-plan.md)). After E1 the app is run with `--dart-define=SHOPPER_API_URL=...` and the login screen asks for a shop code, username and password.
