# AgentMesh 10-company workflow evaluation

- Date: 2026-07-19
- Commit: `46681de`
- Requested model mode: `deterministic`
- Result: 50/50 checks passed (100.0%)
- Method: Paraphrased test knowledge derived from official public support pages. These fixtures are for AgentMesh evaluation and are not endorsed by the named companies.

| Company | Ingestion | Release | Grounded prompts | Isolation | API key |
|---|---:|---:|---:|---:|---:|
| GitHub | PASS | v1 | 2/2 | 1/1 | 1/1 |
| Spotify | PASS | v1 | 2/2 | 1/1 | 1/1 |
| Netflix | PASS | v1 | 2/2 | 1/1 | 1/1 |
| Uber | PASS | v1 | 2/2 | 1/1 | 1/1 |
| Airbnb | PASS | v1 | 2/2 | 1/1 | 1/1 |
| Dropbox | PASS | v1 | 2/2 | 1/1 | 1/1 |
| Atlassian | PASS | v1 | 2/2 | 1/1 | 1/1 |
| Shopify | PASS | v1 | 2/2 | 1/1 | 1/1 |
| Zoom | PASS | v1 | 2/2 | 1/1 | 1/1 |
| YouTube | PASS | v1 | 2/2 | 1/1 | 1/1 |

## GitHub

Document: `github-plan-billing.txt` — Impact of plan changes on billing

Official source: https://docs.github.com/en/billing/concepts/impact-of-plan-changes

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> Paid GitHub plan cancellations and downgrades take effect at the end of the current billing cycle, without proration. Paid access continues until that cycle ends. Plan upgrades take effect immediately and the upgrade charge is prorated. Adding paid seats is also immediate and prorated, while removing seats affects the next billing cycle. GitHub bills personal, organization, and enterprise accounts separately.

### github-grounded-1

Customer query: When does a paid GitHub plan cancellation take effect?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [c2160ea0-b994-4e8f-bc80-3ab563612178] Paid GitHub plan cancellations and downgrades take effect at the end of the current billing cycle, without proration. Paid access continues until that cycle ends. Plan upgrades take effect immediately and the upgrade charge is prorated. Adding paid seats is also immediate and prorated, while removing seats affects the next billing cycle. GitHub bills personal, organization, and enterprise accounts separately.

API key: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

API answer: According to the approved policy:
- [c2160ea0-b994-4e8f-bc80-3ab563612178] Paid GitHub plan cancellations and downgrades take effect at the end of the current billing cycle, without proration. Paid access continues until that cycle ends. Plan upgrades take effect immediately and the upgrade charge is prorated. Adding paid seats is also immediate and prorated, while removing seats affects the next billing cycle. GitHub bills personal, organization, and enterprise accounts separately.

### github-grounded-2

Customer query: Are GitHub plan upgrades prorated?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [c2160ea0-b994-4e8f-bc80-3ab563612178] Paid GitHub plan cancellations and downgrades take effect at the end of the current billing cycle, without proration. Paid access continues until that cycle ends. Plan upgrades take effect immediately and the upgrade charge is prorated. Adding paid seats is also immediate and prorated, while removing seats affects the next billing cycle. GitHub bills personal, organization, and enterprise accounts separately.

### github-isolation

Customer query: How do I coordinate the return of an item left on a shuttle?

Playground: `NEEDS_CLARIFICATION` — PASS; mode `deterministic`; citations `0`; Oracle supported `False`.

Answer: I cannot safely approve an answer because the approved policy evidence is missing or does not support every material claim.


## Spotify

Document: `spotify-cancel-premium.txt` — How to cancel Premium

Official source: https://support.spotify.com/article/cancel-premium/

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> To cancel Spotify Premium, open the account page, go to Manage your plan, and select Cancel subscription. Premium stays active until the next billing date and the account then changes to Spotify Free. A zero-priced free trial changes to Free immediately when canceled and cannot be reactivated. After moving to Free, the user keeps playlists and saved music and can listen with ads. A plan purchased through a partner must be canceled through that partner.

### spotify-grounded-1

Customer query: How do I cancel Spotify Premium?

Playground: `APPROVED_WITH_REWRITE` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: I can help make the policy clearer.

According to the approved policy:
- [2c1a721c-b325-495a-9273-22ed81ef3acd] To cancel Spotify Premium, open the account page, go to Manage your plan, and select Cancel subscription. Premium stays active until the next billing date and the account then changes to Spotify Free. A zero-priced free trial changes to Free immediately when canceled and cannot be reactivated. After moving to Free, the user keeps playlists and saved music and can listen with ads. A plan purchased through a partner must be canceled through that partner.

API key: `APPROVED_WITH_REWRITE` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

API answer: I can help make the policy clearer.

According to the approved policy:
- [2c1a721c-b325-495a-9273-22ed81ef3acd] To cancel Spotify Premium, open the account page, go to Manage your plan, and select Cancel subscription. Premium stays active until the next billing date and the account then changes to Spotify Free. A zero-priced free trial changes to Free immediately when canceled and cannot be reactivated. After moving to Free, the user keeps playlists and saved music and can listen with ads. A plan purchased through a partner must be canceled through that partner.

### spotify-grounded-2

Customer query: Will I keep my playlists after Premium ends?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [2c1a721c-b325-495a-9273-22ed81ef3acd] To cancel Spotify Premium, open the account page, go to Manage your plan, and select Cancel subscription. Premium stays active until the next billing date and the account then changes to Spotify Free. A zero-priced free trial changes to Free immediately when canceled and cannot be reactivated. After moving to Free, the user keeps playlists and saved music and can listen with ads. A plan purchased through a partner must be canceled through that partner.

### spotify-isolation

Customer query: Can a merchant reverse an order refund after it is issued?

Playground: `NEEDS_CLARIFICATION` — PASS; mode `deterministic`; citations `0`; Oracle supported `False`.

Answer: I cannot safely approve an answer because the approved policy evidence is missing or does not support every material claim.


## Netflix

Document: `netflix-charged-after-canceling.txt` — Charged after canceling Netflix

Official source: https://help.netflix.com/en/node/124418

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> To finish a Netflix cancellation, use the cancel-plan page and select Finish Cancellation. The account closes at the end of the current billing cycle and should not be charged again. If a charge appears after cancellation, the account may have been accidentally restarted by someone with access. Cancel again, change the password, and select the option to sign out of all devices so another person cannot restart the account.

### netflix-grounded-1

Customer query: When does my Netflix account close after cancellation?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [47b07854-66ee-4c9f-ab9f-dc07e203f6c2] To finish a Netflix cancellation, use the cancel-plan page and select Finish Cancellation. The account closes at the end of the current billing cycle and should not be charged again. If a charge appears after cancellation, the account may have been accidentally restarted by someone with access. Cancel again, change the password, and select the option to sign out of all devices so another person cannot restart the account.

API key: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

API answer: According to the approved policy:
- [47b07854-66ee-4c9f-ab9f-dc07e203f6c2] To finish a Netflix cancellation, use the cancel-plan page and select Finish Cancellation. The account closes at the end of the current billing cycle and should not be charged again. If a charge appears after cancellation, the account may have been accidentally restarted by someone with access. Cancel again, change the password, and select the option to sign out of all devices so another person cannot restart the account.

### netflix-grounded-2

Customer query: Why might I be charged after canceling Netflix and what should I do?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [47b07854-66ee-4c9f-ab9f-dc07e203f6c2] To finish a Netflix cancellation, use the cancel-plan page and select Finish Cancellation. The account closes at the end of the current billing cycle and should not be charged again. If a charge appears after cancellation, the account may have been accidentally restarted by someone with access. Cancel again, change the password, and select the option to sign out of all devices so another person cannot restart the account.

### netflix-isolation

Customer query: Is an initial marketplace app purchase refundable within 30 days?

Playground: `NEEDS_CLARIFICATION` — PASS; mode `deterministic`; citations `0`; Oracle supported `False`.

Answer: I cannot safely approve an answer because the approved policy evidence is missing or does not support every material claim.


## Uber

Document: `uber-shuttle-lost-items.txt` — Lost items on shuttle trips

Official source: https://help.uber.com/riders/article/lost-items?nodeId=c4946b77-835c-49cb-b85c-5a4611a1da17

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> For an item lost on an Uber shuttle trip, contact support and provide the trip details plus a brief description of the lost item. Uber will reach out to the driver and try to coordinate the item's return. The customer needs to sign in to get help with the lost-item report.

### uber-grounded-1

Customer query: What details should I provide for an item lost on an Uber shuttle?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [83b34930-7c32-437e-a738-e463f19d04f3] For an item lost on an Uber shuttle trip, contact support and provide the trip details plus a brief description of the lost item. Uber will reach out to the driver and try to coordinate the item's return. The customer needs to sign in to get help with the lost-item report.

API key: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

API answer: According to the approved policy:
- [83b34930-7c32-437e-a738-e463f19d04f3] For an item lost on an Uber shuttle trip, contact support and provide the trip details plus a brief description of the lost item. Uber will reach out to the driver and try to coordinate the item's return. The customer needs to sign in to get help with the lost-item report.

### uber-grounded-2

Customer query: Will Uber contact the shuttle driver about my lost item?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [83b34930-7c32-437e-a738-e463f19d04f3] For an item lost on an Uber shuttle trip, contact support and provide the trip details plus a brief description of the lost item. Uber will reach out to the driver and try to coordinate the item's return. The customer needs to sign in to get help with the lost-item report.

### uber-isolation

Customer query: Does downgrading a cloud storage plan leave me with 2 GB?

Playground: `NEEDS_CLARIFICATION` — PASS; mode `deterministic`; citations `0`; Oracle supported `False`.

Answer: I cannot safely approve an answer because the approved policy evidence is missing or does not support every material claim.


## Airbnb

Document: `airbnb-guest-cancellation.txt` — Understanding home cancellation policies as a guest

Official source: https://www.airbnb.com/help/article/4052

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> Cancellation terms for an Airbnb home reservation are set by the host and can vary by listing. The applicable terms appear on the listing, during checkout, and in the confirmation email. In Trips, a guest can start cancellation and review a detailed refund breakdown before confirming. Airbnb initiates an eligible refund as soon as the guest cancels, but the bank controls posting time. If the host cancels, the guest receives a full refund and help finding a similar place regardless of the listing policy.

### airbnb-grounded-1

Customer query: Can I see my Airbnb refund amount before I cancel?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [01e67dc7-415d-4776-a676-ddc7cf9f7d5e] Cancellation terms for an Airbnb home reservation are set by the host and can vary by listing. The applicable terms appear on the listing, during checkout, and in the confirmation email. In Trips, a guest can start cancellation and review a detailed refund breakdown before confirming. Airbnb initiates an eligible refund as soon as the guest cancels, but the bank controls posting time. If the host cancels, the guest receives a full refund and help finding a similar place regardless of the listing policy.

API key: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

API answer: According to the approved policy:
- [01e67dc7-415d-4776-a676-ddc7cf9f7d5e] Cancellation terms for an Airbnb home reservation are set by the host and can vary by listing. The applicable terms appear on the listing, during checkout, and in the confirmation email. In Trips, a guest can start cancellation and review a detailed refund breakdown before confirming. Airbnb initiates an eligible refund as soon as the guest cancels, but the bank controls posting time. If the host cancels, the guest receives a full refund and help finding a similar place regardless of the listing policy.

### airbnb-grounded-2

Customer query: What refund do I get if my Airbnb host cancels?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [01e67dc7-415d-4776-a676-ddc7cf9f7d5e] Cancellation terms for an Airbnb home reservation are set by the host and can vary by listing. The applicable terms appear on the listing, during checkout, and in the confirmation email. In Trips, a guest can start cancellation and review a detailed refund breakdown before confirming. Airbnb initiates an eligible refund as soon as the guest cancels, but the bank controls posting time. If the host cancels, the guest receives a full refund and help finding a similar place regardless of the listing policy.

### airbnb-isolation

Customer query: Where is the button for canceling a video membership?

Playground: `NEEDS_CLARIFICATION` — PASS; mode `deterministic`; citations `0`; Oracle supported `False`.

Answer: I cannot safely approve an answer because the approved policy evidence is missing or does not support every material claim.


## Dropbox

Document: `dropbox-subscription-refunds.txt` — Dropbox subscription refunds

Official source: https://help.dropbox.com/plans/refund

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> In most cases, payments for Dropbox subscriptions, Dropbox Dash subscriptions, and team-member licenses are not refundable. Customers with a billing error should use their available support options; purchases made through a device storefront should be handled by that storefront. Customers in the EU, UK, or Turkey can request a refund for eligible Dropbox Plus, Family, Professional, or Essentials subscriptions if they cancel within 14 days of purchase. A direct-debit chargeback must be processed by the customer's bank.

### dropbox-grounded-1

Customer query: Are Dropbox subscription payments normally refundable?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [c83d72be-dedf-4cbd-8a58-4c557011984a] In most cases, payments for Dropbox subscriptions, Dropbox Dash subscriptions, and team-member licenses are not refundable. Customers with a billing error should use their available support options; purchases made through a device storefront should be handled by that storefront. Customers in the EU, UK, or Turkey can request a refund for eligible Dropbox Plus, Family, Professional, or Essentials subscriptions if they cancel within 14 days of purchase. A direct-debit chargeback must be processed by the customer's bank.

API key: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

API answer: According to the approved policy:
- [c83d72be-dedf-4cbd-8a58-4c557011984a] In most cases, payments for Dropbox subscriptions, Dropbox Dash subscriptions, and team-member licenses are not refundable. Customers with a billing error should use their available support options; purchases made through a device storefront should be handled by that storefront. Customers in the EU, UK, or Turkey can request a refund for eligible Dropbox Plus, Family, Professional, or Essentials subscriptions if they cancel within 14 days of purchase. A direct-debit chargeback must be processed by the customer's bank.

### dropbox-grounded-2

Customer query: Can a UK customer get a Dropbox refund within 14 days?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [c83d72be-dedf-4cbd-8a58-4c557011984a] In most cases, payments for Dropbox subscriptions, Dropbox Dash subscriptions, and team-member licenses are not refundable. Customers with a billing error should use their available support options; purchases made through a device storefront should be handled by that storefront. Customers in the EU, UK, or Turkey can request a refund for eligible Dropbox Plus, Family, Professional, or Essentials subscriptions if they cancel within 14 days of purchase. A direct-debit chargeback must be processed by the customer's bank.

### dropbox-isolation

Customer query: Who sets the refund terms for a home reservation?

Playground: `NEEDS_CLARIFICATION` — PASS; mode `deterministic`; citations `0`; Oracle supported `False`.

Answer: I cannot safely approve an answer because the approved policy evidence is missing or does not support every material claim.


## Atlassian

Document: `atlassian-request-refund.txt` — Request an Atlassian refund

Official source: https://support.atlassian.com/subscriptions-and-billing/docs/request-a-refund/

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> An initial Atlassian app purchase can be refunded when the request is made within 30 days of purchase. For a monthly cloud subscription, a refund is available only during the first paid month after the trial. A new annual cloud subscription can be refunded only within 30 days of its first purchase. Cloud renewals and upgrades cannot be refunded. Marketplace apps follow the same conditions, although a vendor can approve an exception outside the standard period.

### atlassian-grounded-1

Customer query: When can an initial Atlassian app purchase be refunded?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [2e5bb455-3291-4e41-bd0b-73ef46b34bd6] An initial Atlassian app purchase can be refunded when the request is made within 30 days of purchase. For a monthly cloud subscription, a refund is available only during the first paid month after the trial. A new annual cloud subscription can be refunded only within 30 days of its first purchase. Cloud renewals and upgrades cannot be refunded. Marketplace apps follow the same conditions, although a vendor can approve an exception outside the standard period.

API key: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

API answer: According to the approved policy:
- [2e5bb455-3291-4e41-bd0b-73ef46b34bd6] An initial Atlassian app purchase can be refunded when the request is made within 30 days of purchase. For a monthly cloud subscription, a refund is available only during the first paid month after the trial. A new annual cloud subscription can be refunded only within 30 days of its first purchase. Cloud renewals and upgrades cannot be refunded. Marketplace apps follow the same conditions, although a vendor can approve an exception outside the standard period.

### atlassian-grounded-2

Customer query: Are Atlassian cloud renewals and upgrades refundable?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [2e5bb455-3291-4e41-bd0b-73ef46b34bd6] An initial Atlassian app purchase can be refunded when the request is made within 30 days of purchase. For a monthly cloud subscription, a refund is available only during the first paid month after the trial. A new annual cloud subscription can be refunded only within 30 days of its first purchase. Cloud renewals and upgrades cannot be refunded. Marketplace apps follow the same conditions, although a vendor can approve an exception outside the standard period.

### atlassian-isolation

Customer query: How do I recover a playlist after changing to a free music plan?

Playground: `NEEDS_CLARIFICATION` — PASS; mode `deterministic`; citations `0`; Oracle supported `False`.

Answer: I cannot safely approve an answer because the approved policy evidence is missing or does not support every material claim.


## Shopify

Document: `shopify-refunding-orders.txt` — Refunding Shopify orders

Official source: https://help.shopify.com/en/manual/orders/refund-cancel-order

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> A customer seeking a refund for an order placed with a Shopify-powered store must contact that store directly. A merchant can issue a full or partial refund from the Orders page in Shopify admin and can choose the original payment method, store credit, or both where supported. The merchant can optionally restock items and notify the customer. After a refund is initiated, the merchant cannot cancel or reverse that refund. A mistaken refund must be handled by creating a new draft order and collecting payment again.

### shopify-grounded-1

Customer query: As a customer, who do I contact for a refund from a Shopify store?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [9d4b2423-5485-4904-82d4-fb5258a9cb32] A customer seeking a refund for an order placed with a Shopify-powered store must contact that store directly. A merchant can issue a full or partial refund from the Orders page in Shopify admin and can choose the original payment method, store credit, or both where supported. The merchant can optionally restock items and notify the customer. After a refund is initiated, the merchant cannot cancel or reverse that refund. A mistaken refund must be handled by creating a new draft order and collecting payment again.

API key: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

API answer: According to the approved policy:
- [9d4b2423-5485-4904-82d4-fb5258a9cb32] A customer seeking a refund for an order placed with a Shopify-powered store must contact that store directly. A merchant can issue a full or partial refund from the Orders page in Shopify admin and can choose the original payment method, store credit, or both where supported. The merchant can optionally restock items and notify the customer. After a refund is initiated, the merchant cannot cancel or reverse that refund. A mistaken refund must be handled by creating a new draft order and collecting payment again.

### shopify-grounded-2

Customer query: Can a Shopify merchant reverse a refund after issuing it?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [9d4b2423-5485-4904-82d4-fb5258a9cb32] A customer seeking a refund for an order placed with a Shopify-powered store must contact that store directly. A merchant can issue a full or partial refund from the Orders page in Shopify admin and can choose the original payment method, store credit, or both where supported. The merchant can optionally restock items and notify the customer. After a refund is initiated, the merchant cannot cancel or reverse that refund. A mistaken refund must be handled by creating a new draft order and collecting payment again.

### shopify-isolation

Customer query: Will an annual meeting subscription remain active through its term?

Playground: `NEEDS_CLARIFICATION` — PASS; mode `deterministic`; citations `0`; Oracle supported `False`.

Answer: I cannot safely approve an answer because the approved policy evidence is missing or does not support every material claim.


## Zoom

Document: `zoom-subscription-cancellation.txt` — Zoom subscription cancellation and renewal charges

Official source: https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0083524

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> A canceled monthly Zoom subscription remains active until the end of the current billing period. A canceled annual subscription remains active until the end of the current subscription term. When the subscription expires, the account changes to Zoom Basic and future automatic renewals stop. A subscription purchased through Apple, Google Play, or another reseller must be canceled with that third-party provider; Zoom Support cannot cancel or refund it. Subscription charges that have already been processed are non-refundable under Zoom's terms.

### zoom-grounded-1

Customer query: Who handles cancellation if I bought Zoom through Apple or Google Play?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [a4b6939f-f1d9-43ba-a657-f1cbd3350bd0] A canceled monthly Zoom subscription remains active until the end of the current billing period. A canceled annual subscription remains active until the end of the current subscription term. When the subscription expires, the account changes to Zoom Basic and future automatic renewals stop. A subscription purchased through Apple, Google Play, or another reseller must be canceled with that third-party provider; Zoom Support cannot cancel or refund it. Subscription charges that have already been processed are non-refundable under Zoom's terms.

API key: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

API answer: According to the approved policy:
- [a4b6939f-f1d9-43ba-a657-f1cbd3350bd0] A canceled monthly Zoom subscription remains active until the end of the current billing period. A canceled annual subscription remains active until the end of the current subscription term. When the subscription expires, the account changes to Zoom Basic and future automatic renewals stop. A subscription purchased through Apple, Google Play, or another reseller must be canceled with that third-party provider; Zoom Support cannot cancel or refund it. Subscription charges that have already been processed are non-refundable under Zoom's terms.

### zoom-grounded-2

Customer query: How long does a canceled annual Zoom subscription stay active?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [a4b6939f-f1d9-43ba-a657-f1cbd3350bd0] A canceled monthly Zoom subscription remains active until the end of the current billing period. A canceled annual subscription remains active until the end of the current subscription term. When the subscription expires, the account changes to Zoom Basic and future automatic renewals stop. A subscription purchased through Apple, Google Play, or another reseller must be canceled with that third-party provider; Zoom Support cannot cancel or refund it. Subscription charges that have already been processed are non-refundable under Zoom's terms.

### zoom-isolation

Customer query: What trip details are needed to find an item on a shuttle?

Playground: `NEEDS_CLARIFICATION` — PASS; mode `deterministic`; citations `0`; Oracle supported `False`.

Answer: I cannot safely approve an answer because the approved policy evidence is missing or does not support every material claim.


## YouTube

Document: `youtube-cancel-premium.txt` — Cancel YouTube Premium

Official source: https://support.google.com/youtube/answer/6308278?hl=en

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> To cancel YouTube Premium on the web, open youtube.com/paid_memberships, choose Manage membership, select Deactivate, continue to cancel, give a reason, and confirm. Cancellation stops future renewal charges, but Premium benefits continue until the end of the current billing period. A membership billed through Apple must be managed in the Apple account, while one billed through Google Play must be managed in Google Play settings. Canceling does not produce a refund for the unused part of the current billing period.

### youtube-grounded-1

Customer query: How do I cancel YouTube Premium on the web?

Playground: `APPROVED_WITH_REWRITE` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: I can help make the policy clearer.

According to the approved policy:
- [0d4587f3-54e5-495b-9cbd-cb10cd529d58] To cancel YouTube Premium on the web, open youtube.com/paid_memberships, choose Manage membership, select Deactivate, continue to cancel, give a reason, and confirm. Cancellation stops future renewal charges, but Premium benefits continue until the end of the current billing period. A membership billed through Apple must be managed in the Apple account, while one billed through Google Play must be managed in Google Play settings. Canceling does not produce a refund for the unused part of the current billing period.

API key: `APPROVED_WITH_REWRITE` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

API answer: I can help make the policy clearer.

According to the approved policy:
- [0d4587f3-54e5-495b-9cbd-cb10cd529d58] To cancel YouTube Premium on the web, open youtube.com/paid_memberships, choose Manage membership, select Deactivate, continue to cancel, give a reason, and confirm. Cancellation stops future renewal charges, but Premium benefits continue until the end of the current billing period. A membership billed through Apple must be managed in the Apple account, while one billed through Google Play must be managed in Google Play settings. Canceling does not produce a refund for the unused part of the current billing period.

### youtube-grounded-2

Customer query: Do YouTube Premium benefits stop immediately when I cancel?

Playground: `APPROVED` — PASS; mode `deterministic`; citations `1`; Oracle supported `True`.

Answer: According to the approved policy:
- [0d4587f3-54e5-495b-9cbd-cb10cd529d58] To cancel YouTube Premium on the web, open youtube.com/paid_memberships, choose Manage membership, select Deactivate, continue to cancel, give a reason, and confirm. Cancellation stops future renewal charges, but Premium benefits continue until the end of the current billing period. A membership billed through Apple must be managed in the Apple account, while one billed through Google Play must be managed in Google Play settings. Canceling does not produce a refund for the unused part of the current billing period.

### youtube-isolation

Customer query: Can an organization remove paid code-hosting seats with proration?

Playground: `NEEDS_CLARIFICATION` — PASS; mode `deterministic`; citations `0`; Oracle supported `False`.

Answer: I cannot safely approve an answer because the approved policy evidence is missing or does not support every material claim.
