# RevenueCat / Apple IAP Configuration

## App Store Connect — Subscription Group
- **Group Name:** RAX AI Subscriptions
- **Group ID URL:** https://appstoreconnect.apple.com/apps/6771876490/distribution/subscription-groups/22105771
- **App ID (ASC):** 6771876490
- **Bundle ID:** com.sarangocabrera.raxai

## Product IDs (EXACT — used in code)

| Plan    | Product ID              | Price       | Duration | Status            |
|---------|-------------------------|-------------|----------|-------------------|
| Premium | `raxai_premium_monthly` | $5.99 / mo  | 1 month  | Lista para enviar |
| Pro     | `raxai_pro_monthly1`    | $9.99 / mo  | 1 month  | Lista para enviar |

## RevenueCat Entitlement IDs (to be created)
- `premium` → attach product `raxai_premium_monthly`
- `pro`     → attach product `raxai_pro_monthly1`

## RevenueCat Offering (to be created)
- ID: `default` (current offering)
- Packages:
  - `$rc_monthly_premium` → `raxai_premium_monthly`
  - `$rc_monthly_pro`     → `raxai_pro_monthly1`

## API Keys (pending)
- Public iOS SDK Key: `appl_xxxxx` (waiting from user)
- App Store Connect API Key (.p8): pending
- Issuer ID: pending
- Key ID: pending
