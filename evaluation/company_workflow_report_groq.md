# AgentMesh 10-company workflow evaluation

- Date: 2026-07-19
- Commit: `46681de`
- Requested model mode: `groq`
- Result: 30/30 checks passed (100.0%)
- Method: Paraphrased test knowledge derived from official public support pages. These fixtures are for AgentMesh evaluation and are not endorsed by the named companies.

| Company | Ingestion | Release | Grounded prompts | Isolation | API key |
|---|---:|---:|---:|---:|---:|
| GitHub | PASS | v1 | 1/1 | 0/0 | 1/1 |
| Spotify | PASS | v1 | 1/1 | 0/0 | 1/1 |
| Netflix | PASS | v1 | 1/1 | 0/0 | 1/1 |
| Uber | PASS | v1 | 1/1 | 0/0 | 1/1 |
| Airbnb | PASS | v1 | 1/1 | 0/0 | 1/1 |
| Dropbox | PASS | v1 | 1/1 | 0/0 | 1/1 |
| Atlassian | PASS | v1 | 1/1 | 0/0 | 1/1 |
| Shopify | PASS | v1 | 1/1 | 0/0 | 1/1 |
| Zoom | PASS | v1 | 1/1 | 0/0 | 1/1 |
| YouTube | PASS | v1 | 1/1 | 0/0 | 1/1 |

## GitHub

Document: `github-plan-billing.txt` — Impact of plan changes on billing

Official source: https://docs.github.com/en/billing/concepts/impact-of-plan-changes

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> Paid GitHub plan cancellations and downgrades take effect at the end of the current billing cycle, without proration. Paid access continues until that cycle ends. Plan upgrades take effect immediately and the upgrade charge is prorated. Adding paid seats is also immediate and prorated, while removing seats affects the next billing cycle. GitHub bills personal, organization, and enterprise accounts separately.

### github-grounded-1

Customer query: When does a paid GitHub plan cancellation take effect?

Playground: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

Answer: Paid GitHub plan cancellations take effect at the end of the current billing cycle, without proration.

API key: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

API answer: Paid GitHub plan cancellations take effect at the end of the current billing cycle, without proration.


## Spotify

Document: `spotify-cancel-premium.txt` — How to cancel Premium

Official source: https://support.spotify.com/article/cancel-premium/

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> To cancel Spotify Premium, open the account page, go to Manage your plan, and select Cancel subscription. Premium stays active until the next billing date and the account then changes to Spotify Free. A zero-priced free trial changes to Free immediately when canceled and cannot be reactivated. After moving to Free, the user keeps playlists and saved music and can listen with ads. A plan purchased through a partner must be canceled through that partner.

### spotify-grounded-1

Customer query: How do I cancel Spotify Premium?

Playground: `APPROVED_WITH_REWRITE` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

Answer: I can help make the policy clearer.

To cancel Spotify Premium, open the account page, go to Manage your plan, and select Cancel subscription.

API key: `APPROVED_WITH_REWRITE` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

API answer: I can help make the policy clearer.

To cancel Spotify Premium, open the account page, go to Manage your plan, and select Cancel subscription.


## Netflix

Document: `netflix-charged-after-canceling.txt` — Charged after canceling Netflix

Official source: https://help.netflix.com/en/node/124418

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> To finish a Netflix cancellation, use the cancel-plan page and select Finish Cancellation. The account closes at the end of the current billing cycle and should not be charged again. If a charge appears after cancellation, the account may have been accidentally restarted by someone with access. Cancel again, change the password, and select the option to sign out of all devices so another person cannot restart the account.

### netflix-grounded-1

Customer query: When does my Netflix account close after cancellation?

Playground: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

Answer: The account closes at the end of the current billing cycle and should not be charged again [81ae5667-b14d-4195-a441-f5a6bf391915].

API key: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

API answer: The account closes at the end of the current billing cycle and should not be charged again [81ae5667-b14d-4195-a441-f5a6bf391915].


## Uber

Document: `uber-shuttle-lost-items.txt` — Lost items on shuttle trips

Official source: https://help.uber.com/riders/article/lost-items?nodeId=c4946b77-835c-49cb-b85c-5a4611a1da17

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> For an item lost on an Uber shuttle trip, contact support and provide the trip details plus a brief description of the lost item. Uber will reach out to the driver and try to coordinate the item's return. The customer needs to sign in to get help with the lost-item report.

### uber-grounded-1

Customer query: What details should I provide for an item lost on an Uber shuttle?

Playground: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

Answer: For an item lost on an Uber shuttle trip, contact support and provide the trip details plus a brief description of the lost item [2dc6f87b-fcb0-4583-b23e-3567d4153ee7].

API key: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

API answer: For an item lost on an Uber shuttle trip, contact support and provide the trip details plus a brief description of the lost item. [2dc6f87b-fcb0-4583-b23e-3567d4153ee7]


## Airbnb

Document: `airbnb-guest-cancellation.txt` — Understanding home cancellation policies as a guest

Official source: https://www.airbnb.com/help/article/4052

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> Cancellation terms for an Airbnb home reservation are set by the host and can vary by listing. The applicable terms appear on the listing, during checkout, and in the confirmation email. In Trips, a guest can start cancellation and review a detailed refund breakdown before confirming. Airbnb initiates an eligible refund as soon as the guest cancels, but the bank controls posting time. If the host cancels, the guest receives a full refund and help finding a similar place regardless of the listing policy.

### airbnb-grounded-1

Customer query: Can I see my Airbnb refund amount before I cancel?

Playground: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

Answer: In Trips, a guest can start cancellation and review a detailed refund breakdown before confirming [31201fab-7d74-47f7-a513-546b3669a30c].

API key: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

API answer: In Trips, a guest can start cancellation and review a detailed refund breakdown before confirming [31201fab-7d74-47f7-a513-546b3669a30c].


## Dropbox

Document: `dropbox-subscription-refunds.txt` — Dropbox subscription refunds

Official source: https://help.dropbox.com/plans/refund

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> In most cases, payments for Dropbox subscriptions, Dropbox Dash subscriptions, and team-member licenses are not refundable. Customers with a billing error should use their available support options; purchases made through a device storefront should be handled by that storefront. Customers in the EU, UK, or Turkey can request a refund for eligible Dropbox Plus, Family, Professional, or Essentials subscriptions if they cancel within 14 days of purchase. A direct-debit chargeback must be processed by the customer's bank.

### dropbox-grounded-1

Customer query: Are Dropbox subscription payments normally refundable?

Playground: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

Answer: In most cases, payments for Dropbox subscriptions, Dropbox Dash subscriptions, and team-member licenses are not refundable.

API key: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

API answer: In most cases, payments for Dropbox subscriptions, Dropbox Dash subscriptions, and team-member licenses are not refundable.


## Atlassian

Document: `atlassian-request-refund.txt` — Request an Atlassian refund

Official source: https://support.atlassian.com/subscriptions-and-billing/docs/request-a-refund/

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> An initial Atlassian app purchase can be refunded when the request is made within 30 days of purchase. For a monthly cloud subscription, a refund is available only during the first paid month after the trial. A new annual cloud subscription can be refunded only within 30 days of its first purchase. Cloud renewals and upgrades cannot be refunded. Marketplace apps follow the same conditions, although a vendor can approve an exception outside the standard period.

### atlassian-grounded-1

Customer query: When can an initial Atlassian app purchase be refunded?

Playground: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

Answer: An initial Atlassian app purchase can be refunded when the request is made within 30 days of purchase.

API key: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

API answer: An initial Atlassian app purchase can be refunded when the request is made within 30 days of purchase.


## Shopify

Document: `shopify-refunding-orders.txt` — Refunding Shopify orders

Official source: https://help.shopify.com/en/manual/orders/refund-cancel-order

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> A customer seeking a refund for an order placed with a Shopify-powered store must contact that store directly. A merchant can issue a full or partial refund from the Orders page in Shopify admin and can choose the original payment method, store credit, or both where supported. The merchant can optionally restock items and notify the customer. After a refund is initiated, the merchant cannot cancel or reverse that refund. A mistaken refund must be handled by creating a new draft order and collecting payment again.

### shopify-grounded-1

Customer query: As a customer, who do I contact for a refund from a Shopify store?

Playground: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

Answer: A customer seeking a refund for an order placed with a Shopify-powered store must contact that store directly. [563f1c1e-3b76-455f-a66c-c563a457ac4e]

API key: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

API answer: A customer seeking a refund for an order placed with a Shopify-powered store must contact that store directly. [563f1c1e-3b76-455f-a66c-c563a457ac4e]


## Zoom

Document: `zoom-subscription-cancellation.txt` — Zoom subscription cancellation and renewal charges

Official source: https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0083524

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> A canceled monthly Zoom subscription remains active until the end of the current billing period. A canceled annual subscription remains active until the end of the current subscription term. When the subscription expires, the account changes to Zoom Basic and future automatic renewals stop. A subscription purchased through Apple, Google Play, or another reseller must be canceled with that third-party provider; Zoom Support cannot cancel or refund it. Subscription charges that have already been processed are non-refundable under Zoom's terms.

### zoom-grounded-1

Customer query: Who handles cancellation if I bought Zoom through Apple or Google Play?

Playground: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

Answer: A subscription purchased through Apple, Google Play, or another reseller must be canceled with that third-party provider; Zoom Support cannot cancel or refund it. [afd4c66d-9c9c-4d48-aa0d-ecda021d00a5]

API key: `APPROVED` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

API answer: A subscription purchased through Apple, Google Play, or another reseller must be canceled with that third-party provider; Zoom Support cannot cancel or refund it. [afd4c66d-9c9c-4d48-aa0d-ecda021d00a5]


## YouTube

Document: `youtube-cancel-premium.txt` — Cancel YouTube Premium

Official source: https://support.google.com/youtube/answer/6308278?hl=en

Ingestion: upload `READY_FOR_REVIEW`, job `COMPLETED`, version `READY_FOR_REVIEW`, chunks `1`, extraction error `None`.

Uploaded text:

> To cancel YouTube Premium on the web, open youtube.com/paid_memberships, choose Manage membership, select Deactivate, continue to cancel, give a reason, and confirm. Cancellation stops future renewal charges, but Premium benefits continue until the end of the current billing period. A membership billed through Apple must be managed in the Apple account, while one billed through Google Play must be managed in Google Play settings. Canceling does not produce a refund for the unused part of the current billing period.

### youtube-grounded-1

Customer query: How do I cancel YouTube Premium on the web?

Playground: `APPROVED_WITH_REWRITE` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

Answer: I can help make the policy clearer.

To cancel YouTube Premium on the web, open youtube.com/paid_memberships, choose Manage membership, select Deactivate, continue to cancel, give a reason, and confirm [8997a46c-6d5b-460a-be1f-3361b96e112c].

API key: `APPROVED_WITH_REWRITE` — PASS; mode `groq`; citations `1`; Oracle supported `True`.

API answer: I can help make the policy clearer.

To cancel YouTube Premium on the web, open youtube.com/paid_memberships, choose Manage membership, select Deactivate, continue to cancel, give a reason, and confirm [8997a46c-6d5b-460a-be1f-3361b96e112c].
