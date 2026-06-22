---
id: mwb_20260622_dr_monetization_models_for_a_craft
evidence_bundle_id: bundle_20260615_intent_research_20260614_what_monetization_and
target_page: meatywiki/decisions/monetization_models_for_a_craft_pattern.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_what_monetization_and_marketplace_mechanics_subs: Combines
  the low competitive take-rate ceiling (clm_026, clm_029), the conversion advantage of gated subscriptions
  (clm_'
key_claims:
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf08
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_026
  - clm_029
  - clm_020
  - clm_033
  - clm_038
  - clm_032
  - clm_027
  - clm_028
  - clm_013
  - clm_039
  - clm_042
  - clm_046
  - clm_036
  - clm_023
  - clm_025
  - clm_018
  - clm_044
  - clm_024
  - clm_034
  - clm_021
  - clm_012
  - clm_015
  - clm_016
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Monetization Models for a Craft Pattern Marketplace and 3D Crochet OS

## Context

- SelFee is Ribblr's personal smart-fee mechanism that gives a seller control over their marketplace sale fees. [claim:clm_001]
- Sellers can earn up to 100% off their sale fee, eliminating the marketplace fee on pattern sales entirely. [claim:clm_002]
- Points are earned each time another person uses the seller's SelFee link, tying the discount to sharing personal shop and pattern links. [claim:clm_003]
- Collecting 10,000 points instantly grants 10% off the sale fee and rolls 1,000 points forward into the next month. [claim:clm_004]
- New users receive a 1,000-point welcome bonus in their first month of using SelFee. [claim:clm_005]
- SelFee point-earning applies to both pattern sales and finished 'makes', extending the program beyond pattern listings. [claim:clm_006]
- Opening a Ribblr shop is free, with no listing or shop fees; sellers pay only a single fee when a sale is made. [claim:clm_007]
- Ribblr advertises zero listing, shop, and Ribbuild fees, charging only a single fee per sale that can be removed entirely via SelFee. [claim:clm_008]
- SelFee is Ribblr's personal 'smart fee' that gives designers control over sale fees and can reduce the sale fee by up to 100%, eliminating the fee entirely. [claim:clm_009]
- SelFee discounts are earned through a points system tied to sharing personal shop/pattern links, where accumulated points unlock instant sale-fee discounts (e.g., 10,000 points = 10% off). [claim:clm_010]
- Ribblr positions SelFee as a designer-controlled fee mechanism layered on its interactive (Ribbuild) pattern-selling format. [claim:clm_011]
- Ravelry runs as a profitable four-person company, indicating a lean operation rather than a venture-scaled marketplace. [claim:clm_012]
- Pattern-sales commission scales from free up to a capped $20/month based on monthly sales volume, designed to undercut e-Junkie and Payloadz. [claim:clm_013]
- Since inception over 1.3 million patterns had been sold through the platform, making pattern sales a meaningful income source. [claim:clm_014]
- Ravelry runs a custom in-house ad-serving system to serve its own ads and avoid paying any third-party fees or commissions. [claim:clm_015]
- Advertising is a major revenue stream backed by roughly 180 million monthly page views and about 1,500 active advertisers, half of whom spend under $15/month. [claim:clm_016]
- Amazon affiliate book commissions of roughly 7-8% are part of Ravelry's diversified income. [claim:clm_017]
- A paid 'Ravelry Extra' for forum image uploads is priced at $5/year, partly to cap usage and recoup storage/bandwidth costs. [claim:clm_018]
- Ravelry supplements income with voluntary user donations (since 2007) and an online shop selling branded and craft-related merchandise. [claim:clm_019]
- Hard-paywall apps achieve a 12.11% median download-to-paid conversion versus just 2.18% for freemium apps, showing forced-commitment models convert downloads to payers at a far higher rate. [claim:clm_020]
- Trials lasting 17-32 days have the highest median trial-to-paid conversion at 45.7%, indicating longer trials let users experience value and strengthen purchase intent. [claim:clm_021]
- The median app converts downloads to trial starts at 6.2%, while top-decile (P90) apps reach a 20.3% trial-start rate, more than three times the median. [claim:clm_022]
- High-priced apps see a median download-to-trial conversion of 9.8% versus 4.3% for low-priced apps, suggesting buyers of expensive apps are more intent-driven. [claim:clm_023]
- The report's benchmarks draw on data from roughly 75,000 subscription apps and over $10B in tracked revenue across iOS and Android. [claim:clm_024]
- Apps with higher price points see better Day 35 download-to-paid conversion, with a median of 2.7% compared to 1.5% for low-priced apps. [claim:clm_025]
- Ribblr's pattern sale fee ranges from FREE to 4% per sale, with the standard tier starting at 4%. [claim:clm_026]
- Ribblr applies a minimum sale fee of 25 cents on patterns and 50 cents on finished makes (or local-currency equivalent). [claim:clm_027]
- A 50-cent designer royalty is collected on each finished-make sale and paid to the designer whose pattern was used. [claim:clm_028]
- Through the $elFee program, sellers may be able to reduce their pattern sale fee to nil (0%). [claim:clm_029]
- Tips carry a 5% tip service fee, and Stripe payment processing fees may be charged separately on top. [claim:clm_030]
- Listing and the Ribbuild pattern-creation tool are free, as are US/UK pattern translation, smart sizing, unit conversion, and photo/video uploads. [claim:clm_031]
- The spec proposes three monetization mechanics: a marketplace cut on pattern sales with designer storefronts, a subscription tier for pro features, and add-on packs. [claim:clm_032]
- The proposed subscription tier gates specific 'pro' capabilities: 3D preview, advanced import/parsing, and pattern generation. [claim:clm_033]
- The spec positions the product as 'Ravelry + interactive pattern runner + CAD-lite for amigurumi.' [claim:clm_034]
- The spec flags pattern IP/copyright from importing patterns 'from anywhere' as the #1 business landmine and recommends designer opt-in, licensing, or bounded user-private imports. [claim:clm_035]
- The spec names Ribblr and My Row Counter as the dominant existing 'pattern + tracking' competitors, warning that shipping a basic pattern library plus counters means competing in a 'red ocean.' [claim:clm_036]
- The spec recommends 3D-to-pattern generation as a Phase 3 capability, to be tackled only after pattern execution/playback and structural 3D visualization are nailed. [claim:clm_037]
- The spec identifies the 3D visualizer plus reverse-pattern-from-3D as the novel, defensible wedge differentiating KnitWit from existing pattern-tracking apps. [claim:clm_038]
- Patreon's standard 10% platform fee applies to creators who publish their creator page after August 4, 2025. [claim:clm_039]
- Creators who published their page on or before August 4, 2025 keep their existing (legacy) platform pricing and see no price change from this policy. [claim:clm_040]
- A legacy-plan creator who unpublishes their page (or has it unpublished by Patreon) switches to the standard 10% pricing upon republishing. [claim:clm_041]
- Patreon's platform fee ranges between 5% and 12% of successfully processed sales plus applicable taxes, depending on the creator's platform plan. [claim:clm_042]
- For USD payouts above $3, the credit card / Apple Pay payment processing rate is 2.9% plus $0.30 per transaction. [claim:clm_043]
- The standard 10% platform fee grants access to all core Patreon features, including a hosted creator page, monthly/annual memberships, digital product sales, video hosting, community tools, and audience/growth insights. [claim:clm_044]
- A 2.5% currency conversion fee applies to any payment made in a currency different from the creator's payout currency. [claim:clm_045]
- The App Store Small Business Program offers a reduced 15% commission rate on paid apps and In-App Purchases. [claim:clm_046]
- Existing developers who earned up to 1 million USD in proceeds in the prior calendar year, plus developers new to the App Store, qualify for the program and reduced commission. [claim:clm_047]
- Eligibility requires no more than 1 million USD in total proceeds (sales net of Apple's commission and certain taxes/adjustments) during the 12 fiscal months within the previous calendar year, and no more than 1 million USD during the current year, including Associated Developer Accounts. [claim:clm_048]
- If a participating developer exceeds the 1 million USD threshold during the current calendar year, the standard commission rate applies to future sales. [claim:clm_049]

## Decision

The recommended monetization mix is a low (0-5%) marketplace cut on the designer storefront to stay competitive with Ribblr, combined with a hard-gated 'KnitWit Pro' subscription carrying the 3D-preview, advanced-import, and pattern-gen value, because the high-margin pro subscription cross-subsidizes the necessarily-thin marketplace take while the differentiated 3D wedge is precisely what commands subscription pricing. [claim:clm_inf05]

## Rationale

- Combines the low competitive take-rate ceiling (clm_026, clm_029), the conversion advantage of gated subscriptions (clm_020), and the spec's identification of 3D/reverse-pattern as the defensible wedge (clm_038) gated to pro (clm_033); the mix lets subscription revenue carry margin the marketplace cut cannot. [claim:clm_inf05]
- Ribblr's minimums (clm_027) and royalty (clm_028) make the effective take on a low-priced pattern much higher than the headline 0-4% (clm_026); dropping the per-sale minimum is a concrete competitive lever on cheap patterns while preserving margin on expensive ones. [claim:clm_inf09]
- Directly aggregates the documented rates: Ribblr 0-4% (clm_026, clm_029), Ravelry capped at $20/mo (clm_013), Patreon 10% standard within a 5-12% band (clm_039, clm_042), Apple SBP 15% (clm_046); the spread defines the band and shows craft-native incumbents anchor the low end. [claim:clm_inf01]
- Ribblr (named by the spec as the dominant competitor, clm_036) charges 0-4% and reaches 0% via SelFee (clm_026, clm_029), and Ravelry's cap (clm_013) is similarly low; a new entrant pricing pattern sales much higher than this established craft-native floor would be undercut, so the competitive ceiling on the marketplace cut is low single digits. [claim:clm_inf02]
- RevenueCat data shows hard paywalls (clm_020) and higher prices (clm_023, clm_025) convert far better; the spec's pro features (clm_033) are differentiated/high-intent, so gating them behind a committed paywall aligns with the measured conversion advantage rather than diluting them in freemium. [claim:clm_inf03]
- Subscription has direct precedent (Ravelry Extra clm_018, Patreon memberships clm_044, RevenueCat corpus clm_024); marketplace cut has precedent but low craft rates (clm_026, clm_013) vs higher generic (clm_039); no source documents a working a-la-carte 'add-on pack' outcome, so it is unproven relative to the spec's proposal (clm_032). [claim:clm_inf04]
- Pro features (clm_033) and the 3D wedge (clm_038) serve the pattern-runner/CAD-lite consumer experience (clm_034), distinct from the designer-royalty/sale transaction (clm_028); value-based pricing logic says recover that cost from the consumer subscription, not the designer's marketplace cut. [claim:clm_inf06]
- The spec implies a pro upsell off a free base (clm_032, clm_033) which reads freemium, but clm_020 shows freemium underperforms; clm_021 shows 17-32 day trials maximize trial-to-paid (45.7%), so a trial-gated hybrid resolves the tension. High impact because it sets the conversion ceiling. [claim:clm_inf07]
- Ravelry stays lean and leans on advertising/diversified income with a low capped commission (clm_012, clm_013, clm_015, clm_016); Ribblr's cut is also low (clm_026); a 3D/CAD product has far higher compute/dev cost, so a thin marketplace cut cannot be the primary engine and subscription must lead. [claim:clm_inf08]

## Consequences

- Pricing-sensitivity note: because Ribblr enforces fixed-cent minimum sale fees (25c patterns / 50c makes) plus a 50c designer royalty, low-priced pattern sales already carry a high effective percentage take, so KnitWit can safely adopt a small flat-percentage cut with no per-sale minimum to undercut Ribblr on cheap patterns while still profiting on higher-priced storefront items. [claim:clm_inf09]
- Across the four benchmarked craft/maker platforms the documented designer take-rate spans roughly 0-4% (Ribblr, reducible to 0% via SelFee), a sub-$20/month volume cap on Ravelry pattern sales, 10% standard on Patreon (5-12% range), and 15-30% on Apple's App Store, implying a craft-pattern-marketplace cut should land in a 0-15% band with the craft-native floor (Ribblr/Ravelry) far below the generic-platform ceiling (Patreon/Apple). [claim:clm_inf01]
- A KnitWit designer-storefront cut materially above Ribblr's 0-4% effective rate would face acute price-sensitivity risk, because the dominant direct competitor already lets designers reach a 0% sale fee via SelFee, making any double-digit cut uncompetitive for the pattern-sales surface specifically. [claim:clm_inf02]
- The 5-15x conversion gap between forced-commitment and freemium models (12.11% hard-paywall vs 2.18% freemium download-to-paid; higher-priced apps converting at 2.7% vs 1.5% on Day 35) implies KnitWit's '3D/import/gen' pro tier should monetize via a paid trial or hard-gated subscription rather than an open freemium funnel, since the pro features are exactly the high-intent, high-value capabilities that justify a higher price point. [claim:clm_inf03]
- Mapping the spec's three mechanics to precedent: the pro-subscription tier is the most validated (mirrors Ravelry Extras, Patreon memberships, and RevenueCat's subscription benchmarks), the marketplace cut is validated in principle but pricing-constrained (Ribblr/Ravelry/Patreon/Apple all take a cut, but craft-native rates are low), and the add-on packs are the least precedented and therefore unproven for craft-app monetization in this evidence set. [claim:clm_inf04]
- The 3D-preview and pattern-generation 'pro' capabilities align better with subscription than with the marketplace cut because their value accrues to the maker/consumer running and visualizing a pattern, not to the designer's per-sale transaction, so attaching their cost to a per-sale marketplace commission would mis-price the value and depress designer participation. [claim:clm_inf06]
- There is an apparent contradiction between the spec's freemium-flavored 'pro tier' framing and the RevenueCat evidence that freemium converts downloads to paid at only 2.18% versus 12.11% for hard paywalls; the likely resolution is a hybrid (free pattern-running and library, hard-gated 3D/gen behind a long 17-32 day trial), and the decision impact is high because it directly determines the product's paid-conversion ceiling. [claim:clm_inf07]
- Ravelry's lean four-person, advertising-and-low-commission model and Ribblr's 0-4%/SelFee model jointly demonstrate that pattern-marketplace commissions alone are insufficient to fund a capital-intensive 3D/CAD product, implying KnitWit must lead with subscription (and possibly advertising at scale) rather than expect the marketplace cut to be the primary revenue engine. [claim:clm_inf08]

## Links

- [[claim:clm_026]]
- [[claim:clm_029]]
- [[claim:clm_020]]
- [[claim:clm_033]]
- [[claim:clm_038]]
- [[claim:clm_032]]
- [[claim:clm_027]]
- [[claim:clm_028]]
- [[claim:clm_013]]
- [[claim:clm_039]]
- [[claim:clm_042]]
- [[claim:clm_046]]
- [[claim:clm_036]]
- [[claim:clm_023]]
- [[claim:clm_025]]
- [[claim:clm_018]]
- [[claim:clm_044]]
- [[claim:clm_024]]
- [[claim:clm_034]]
- [[claim:clm_021]]
- [[claim:clm_012]]
- [[claim:clm_015]]
- [[claim:clm_016]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
