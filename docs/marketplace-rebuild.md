# Motorlane marketplace rebuild

## Implemented

- New React visual system across marketplace, vehicle detail, renter workspace, owner workspace, authentication and account pages.
- Studio vehicle hero with layered landscape, CSS depth/hover motion and integrated location/date/type search.
- Right-hand three-line navigation menu, outside-click and Escape dismissal.
- Vehicle cards with prominent rate/name/location, verified review average and count, and account-persisted favorites.
- Dedicated saved collection, rental calendar and checkout route. Checkout collects renter contact details, pickup notes and rental-condition acknowledgement before requesting.
- Optional owner-editable description, transmission, seats, model year and pickup instructions. Existing records are not filled with invented specifications.
- Customer next-trip overview, status summaries, recent/current/upcoming rentals.
- Owner fleet search/status filters, listing editor, requests/handoffs, maintenance, completed booking-value chart and CSV export.
- Professional downloadable booking summary using the booked rate snapshot.

## Deliberate boundaries

Checkout sends an owner-approved rental request. Online payment processing, paid insurance and tax invoicing are not connected, and the UI does not imply that money was collected. Favorites are a saved collection, not a multi-vehicle purchase cart. The hero is an AI-created studio render with CSS depth, not a WebGL vehicle configurator.

## Validation

Frontend production build, lint and 5 existing unit tests pass. 18 Django API/account/rental tests pass using isolated SQLite because the development MySQL user cannot create a test database. Both additive migrations applied successfully to the running MySQL database.

Headless Chrome checked main renter routes at 1440, 768 and 390 pixels, and owner routes at desktop and 390 pixels. No observed horizontal page overflow or JavaScript errors after fixes. Tested menu dismissal, favorite persistence/restoration, fleet search, CSV download and checkout navigation/validation/request payload. Checkout UI submission was intercepted to avoid creating a real rental request; server creation is covered by isolated database tests. PDF rendered and visually inspected.

## Generated hero asset

Built-in imagegen tool. Active asset: `frontend/src/assets/studio-splendor.png`.

The hero uses a newly generated realistic black Hero Honda Splendor studio render with chrome components, spoked wheels, and red/blue tank stripes. Its transparent background sits over a light ivory and pale-blue studio scene. CSS provides hover motion; this is not a rotatable 3D model. The earlier car render is retained as an unused design asset.

Dashboard metric cards now use meaningful SVG icons, and connected-account rows use the multicolor Google logo.

The original user-uploaded vehicle photographs remain the listing images.
