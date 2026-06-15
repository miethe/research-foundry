---
schema_version: '0.1'
type: research_report
report_id: report_20260615_as_of_mid_2026_what_is
title: Mobile Crochet App Competitive Landscape and Whitespace Map (2026)
intent_id: intent_research_20260614_as_of_mid_2026_what_is
evidence_bundle_id: pending
created_at: '2026-06-15T09:36:38-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# Mobile Crochet App Competitive Landscape and Whitespace Map (2026)

## Executive summary

The pattern+counter mobile segment is a 'red ocean': Ribblr, knitCompanion, Pattern Keeper, My Row Counter and Stitch Fiddle compete on overlapping features (PDF import, stitch/row counting, charting, Ravelry sync) and differentiate mainly on price and platform, leaving feature-level differentiation largely exhausted within 2D playback. **Inference:** [claim:clm_inf03]
Across all six surveyed mobile/web incumbents (Ribblr, My Row Counter, Pattern Keeper, knitCompanion, Stitch Fiddle, and the Ravelry third-party connector ecosystem) none ships interactive 3D preview or guided physical-assembly, confirming the design-spec wedge ('see what I'm making', 'can't get lost', 'assemble/modify confidently') is unoccupied whitespace in the mobile category. **Inference:** [claim:clm_inf01]
Every tool in the corpus that offers true interactive 3D crochet preview (CrochetPARADE, crogen) or 3D-mesh-to-pattern generation (AmiGo) is non-mobile - browser-desktop, Tkinter/Blender desktop, or an academic pipeline - so the 3D capability and the mobile form factor are currently disjoint, which is precisely the gap a mobile interactive-3D product would close. **Inference:** [claim:clm_inf02]
The design-spec claim that Ravelry has no official native mobile app and the ecosystem is third-party connectors is CONFIRMED by current evidence: Ravelry's own directory states there is no first-party app and lists connectors (knitCompanion, Row Counter, YarnBuddy, Pocket Crochet, Ravelgurumi, Yarn Squirrel, Stitch Fiddle) built by third parties. **Inference:** [claim:clm_inf04]
The 3D/guided-assembly wedge is more durable than a feature within the red-ocean charting segment because it requires a vertically integrated stack - Crochet IR + stitch-graph + approximate-3D layout + mobile renderer - that no incumbent has assembled and that the existing 3D tools deliberately scoped to non-mobile, raising the replication cost above a simple feature copy. **Inference:** [claim:clm_inf12]

## Capability matrix

| Competitor | Interactive pattern playback | 3D / visual preview | Pattern import (PDF/web/video/chart) | Counters | Project/yarn inventory | Marketplace/community | Platform (iOS/Android) | Evidence |
|------------|------------------------------|---------------------|--------------------------------------|----------|------------------------|-----------------------|------------------------|----------|
| Ribblr | Interactive ePatterns with cross-device crafting, per-user progress tracking, custom-size views, and built-in video tutorials | No 3D preview advertised | Ribbuild converts PDFs into interactive ePatterns | Per-user progress tracking in ePatterns | Library with external PDF patterns | Buy/sell pattern marketplace, any user can open a shop | Apple ecosystem: iPhone/iPad/iPod touch (iOS 14.5+), Mac (macOS 11.3+ M1), Apple Vision (visionOS 1.0+) | [claim:clm_051] |
| Ribblr (no-3D evidence) | - | The listing advertises no 3D visualization or guided-assembly feature, indicating the strongest pattern+tracking incumbent does not contest that whitespace as of this version | - | - | - | - | - | [claim:clm_057] |
| My Row Counter | Row/stitch counting workflow | 2D charts only | Built-in Charts tool creates a chart from scratch or by transforming an image into a chart | Row counting is the core function | Direct Ravelry integration imports the user's existing yarn stash from Ravelry into the app | Ravelry-connected; Seller Mode for makers | Apple Watch (watchOS 5+), Android Wear OS, Fitbit Sense/Versa 3 | [claim:clm_074] |
| Pattern Keeper | Continuous-pattern view across page breaks, symbol search/highlight, diagonal stitch selection | 2D charts only, no 3D | Works with PDF charts from designers (Heaven and Earth Designs, Paine Free Crafts, Charting Creations, Artecy); photographed paper patterns import but lose search/thread-number functions | Progress tracking marks finished stitches and shows stitches left per color | Thread list per color | None advertised | Android 4.1+ (2GB RAM, avoid 8.1); iOS in early development, not yet available | [claim:clm_003] |
| knitCompanion | Magic Markers for counting/highlighting/coloring stitches over the pattern (paid) | 2D pattern tracking only | Free tier imports via Ravelry/Dropbox and adds any PDF; Intelligent Chart Recognition speeds chart setup (paid) | Free kCBasics row and along-the-row tracking, per-project counters, iCloud sync | Project-level tracking; multi-craft (knitting, crochet, cross-stitch) | Ravelry-connected directory listing | iPhone, iPad, Mac (iOS/iPadOS 16.4+, macOS 13.3+) | [claim:clm_024] |
| Stitch Fiddle | Browser-based grid charting | 2D charts only | Premium adds image upload and conversion of charts into written knit/crochet instructions | No dedicated stitch counter advertised | No yarn inventory advertised | Premium multi-user collaboration; QR-coded charts | Browser-based across Windows, Mac, Android, iOS, Linux, Chromebook with device sync | [claim:clm_014] |
| Ravelry third-party connectors | Connectors provide playback/tracking (knitCompanion) | No 3D in the connector set | Discovery connectors (kntd:discover, Pattrick, Ravelgurumi, Ravit/Ravit 2) browse Ravelry pattern/yarn databases | Row Counter, YarnBuddy, Pocket Knitting, Pocket Crochet, Loopsy sync project tracking with Ravelry | Stash connectors (Yarn Stasher Smart Scan, YarnCat, YarnBuddy); Yarn Squirrel stores PDFs alongside the Ravelry library | Directory of third-party apps; no first-party Ravelry app | iPhone/iPad (Yarn Squirrel) and connector-specific platforms | [claim:clm_067] |

The free tier can import patterns by linking to Ravelry and Dropbox and supports adding any PDF pattern (knitCompanion). [claim:clm_025]
Paid tiers add Intelligent Chart Recognition to speed up chart setup (knitCompanion). [claim:clm_028]
The app can search Ravelry to auto-import full yarn details rather than requiring manual entry (My Row Counter). [claim:clm_073]
Chart cells can be filled with stitch symbols chosen from a list or with user-created custom symbols (My Row Counter). [claim:clm_075]
An iOS version is in early development and not yet available; users can sign up for an iOS newsletter to be notified about the first test version (Pattern Keeper). [claim:clm_008]
Premium unlocks image upload, multi-user collaboration, QR-coded charts, vector/Word/Excel exports, automatic knitting-chart error checking, and conversion of charts into written knitting/crochet instructions (Stitch Fiddle). [claim:clm_013]
knitCompanion is published by Create2Thrive Inc. and is positioned as a multi-craft project tracker spanning knitting, crochet, and cross-stitch. [claim:clm_023]
Pattern discovery and management is served by several connectors including kntd:discover, Pattrick, Ravelgurumi (amigurumi-specific), and Ravit/Ravit 2, which browse the Ravelry pattern and yarn databases. [claim:clm_068]

## Pricing and monetization

| Competitor | Monetization model | Key terms | Evidence |
|------------|--------------------|-----------|----------|
| Pattern Keeper | One-time in-app purchase | $9.00 grants permanent (use-forever) access | [claim:clm_001] |
| Pattern Keeper | Free trial | One-month free trial includes access to all features | [claim:clm_002] |
| Stitch Fiddle | Non-renewing subscription | $5.50 for one month or $33.00 per year, framed as a 50% discount equal to $2.75/mo | [claim:clm_011] |
| Stitch Fiddle | Billing terms | One-off payments with no automatic renewal; expire automatically at end of period | [claim:clm_012] |
| Stitch Fiddle | Free tier caps | 15 charts, 50 unique colors/symbols per chart, max grid 300x300 (90,000 stitches) | [claim:clm_009] |
| Stitch Fiddle | Premium caps | Unlimited charts, 250 unique colors/symbols per chart, max grid 1,000x1,000 (1,000,000 stitches) | [claim:clm_010] |
| Ribblr | Free download + IAP | Free to download with free and premium patterns plus in-app purchases | [claim:clm_056] |
| Ribblr+ | Recurring subscription tiers | Plus $4.99/mo (listed $6.99), Gold $6.99/mo (listed $9.99), Platinum $9.99/mo (listed $13.99) | [claim:clm_080] |
| Ribblr+ | Annual discount | Annual billing saves 30% across all tiers | [claim:clm_081] |
| Ribblr+ | Trial / renewal | 14-day free trial precedes auto-renewal; on day 14 the membership auto-renews and the member is charged | [claim:clm_082] |
| Ribblr+ | Marketplace currency | Plus's 100 Gems is a joining gift, Gold grants 100 Gems/mo, Platinum grants 400 Gems/mo | [claim:clm_084] |
| Ribblr | Marketplace cut model | Buy/sell pattern marketplace where any user can open a shop quickly | [claim:clm_053] |
| knitCompanion | Free tier + paid IAP | Free kCBasics tier provides row/along-the-row tracking, per-project counters, iCloud sync | [claim:clm_024] |

All tiers include unlimited daily free patterns, pinning/saving patterns in boards, adding external (PDF) patterns, no ads, and Focus Mode (Ribblr+). [claim:clm_083]
Plans are cancel-anytime, and tier changes use pro-rata pricing so an upgrade only charges the difference between tiers (Ribblr+). [claim:clm_086]
Seller Mode automatically calculates time-spent cost from the configured hourly rate and the project timer, and is enabled per currency and hourly rate (My Row Counter). [claim:clm_078]
Seller Mode displays the profit from a sale on the project settings page after a project is marked for sale with costs and a price (My Row Counter). [claim:clm_079]
On price, the mobile incumbents split into two monetization archetypes - one-time unlock (Pattern Keeper $9.00 forever; Stitch Fiddle non-renewing $5.50/mo or $33/yr) versus recurring subscription + marketplace (Ribblr+ $4.99-$9.99/mo with a buy/sell marketplace; knitCompanion tiered IAP) - so a 3D/assembly wedge can credibly anchor a premium subscription above the ~$5/mo charting tier without colliding with the $9 one-time floor. **Inference:** [claim:clm_inf05]

## The 3D / generative corpus (non-mobile)

CrochetPARADE is a platform for creating, visualizing, and analyzing both 2D and 3D crochet patterns. [claim:clm_015]
CrochetPARADE uses a custom language grammar that lets users define stitches and stitch patterns, then parses and checks a submitted pattern for correctness before building a virtual model rendered in 3D. [claim:clm_037]
The custom grammar is intended to ensure accuracy and precision in pattern instructions, avoiding the ambiguities of plain-English crochet instructions. [claim:clm_038]
The platform flags overly loose or tight stitches so users can replace them before crocheting, reducing the need for blocking. [claim:clm_039]
The interactive 3D view supports rotate, zoom, and pan, animation of the pattern creation process, highlighting and hiding selected stitches, and changing yarn thickness and color. [claim:clm_040]
Export includes an auto-generated crochet chart using standard crochet symbols and an SVG image showing stitch connections that labels stitches by type, row number, and position within a row. [claim:clm_041]
CrochetPARADE is built on the JavaScript libraries SVG.js and three.js and can export projects to 3D files importable into Blender. [claim:clm_042]
Users can export to a GLTF 3D file that is compatible with Blender. [claim:clm_019]
The platform is tested on latest Chrome, Brave, and Firefox, has Safari issues, and is not designed for mobile devices. [claim:clm_017]
All calculations run locally in the browser with no data collected to a central server or transmitted over the internet. [claim:clm_018]
The platform and its computational components are free and open source under GPLv3, intended to remain free and open to all in perpetuity. [claim:clm_021]
Recent additions include a Remesher that turns a 3D model into crochet instructions and a new STL export for resizing patterns and 3D-printing a model. [claim:clm_022]
The site was last updated February 13, 2026. [claim:clm_016]
crogen is desktop crochet software where users build a crochet pattern through a GUI by adding rows and stitch types via buttons. [claim:clm_031]
As the user constructs the pattern, a 3D model updates in real time to preview what the finished crocheted piece would look like. [claim:clm_032]
On completion the tool generates a written pattern that, when followed, produces a crochet piece matching the 3D design. [claim:clm_033]
crogen is implemented in Python (100% of the codebase) using the Tkinter UI library and Blender for 3D rendering, making it a desktop application rather than mobile. [claim:clm_034]
Running crogen requires a pre-existing Blender and Tkinter installation, with remaining dependencies installed via pip, indicating a developer-oriented setup rather than a packaged consumer app. [claim:clm_035]
crogen is a low-maturity hobbyist project (about 3 stars, 0 forks, 36 commits) with no explicit license declared in the README. [claim:clm_036]
AmiGo takes a closed triangle mesh plus a single user-specified point and generates crochet instructions that, when knitted and stuffed, produce an Amigurumi toy resembling the input geometry. [claim:clm_043]
The pipeline works by constructing a 'Crochet Graph' (geometry plus connectivity) that is then translated into a human-readable crochet pattern. [claim:clm_044]
The shape is automatically segmented into crochetable components joined via the join-as-you-go method, eliminating any need for sewing. [claim:clm_045]
The full input is a closed 3D model, a seed point, and a stitch size; the generated instructions use only simple crochet stitches and are join-as-you-go, so no sewing is required. [claim:clm_046]
The authors claim the crocheted-and-stuffed output resembles the input 3D shape more closely than any previous approach to crochet instruction generation. [claim:clm_047]
Crochet cannot be easily automated and, unlike machine knitting, there exists no crochet machine to date, motivating a computational pattern-generation method. [claim:clm_048]
The crochet graph is converted to a program using standard code-synthesis tools, then loop-unrolled into a human-readable pattern, confirming a deterministic algorithmic (not ML-based) pipeline. [claim:clm_049]
The method has inherent geometric limits: surfaces with negative mean curvature and positive Gaussian curvature ('craters') cannot be realized by crocheting and stuffing alone and must be preprocessed away. [claim:clm_050]

## Whitespace map (derivation)

Across all six surveyed mobile/web incumbents (Ribblr, My Row Counter, Pattern Keeper, knitCompanion, Stitch Fiddle, and the Ravelry third-party connector ecosystem) none ships interactive 3D preview or guided physical-assembly, confirming the design-spec wedge ('see what I'm making', 'can't get lost', 'assemble/modify confidently') is unoccupied whitespace in the mobile category. **Inference:** [claim:clm_inf01]
Every tool in the corpus that offers true interactive 3D crochet preview (CrochetPARADE, crogen) or 3D-mesh-to-pattern generation (AmiGo) is non-mobile - browser-desktop, Tkinter/Blender desktop, or an academic pipeline - so the 3D capability and the mobile form factor are currently disjoint, which is precisely the gap a mobile interactive-3D product would close. **Inference:** [claim:clm_inf02]
The pattern+counter mobile segment is a 'red ocean': Ribblr, knitCompanion, Pattern Keeper, My Row Counter and Stitch Fiddle compete on overlapping features (PDF import, stitch/row counting, charting, Ravelry sync) and differentiate mainly on price and platform, leaving feature-level differentiation largely exhausted within 2D playback. **Inference:** [claim:clm_inf03]
The convergent design of CrochetPARADE's 3D view (rotate/zoom/pan, animate pattern creation, highlight/hide selected stitches) and crogen's real-time updating 3D model maps almost one-to-one onto the spec's required visualizer features (row/round highlighting, ghost-next-row, piece isolation), so the Pattern->3D visualizer (gate G3) is the lower-risk of the two spec capabilities. **Inference:** [claim:clm_inf08]

## Defensibility analysis

The 3D/guided-assembly wedge is more durable than a feature within the red-ocean charting segment because it requires a vertically integrated stack - Crochet IR + stitch-graph + approximate-3D layout + mobile renderer - that no incumbent has assembled and that the existing 3D tools deliberately scoped to non-mobile, raising the replication cost above a simple feature copy. **Inference:** [claim:clm_inf12]
The pattern+counter mobile segment is a 'red ocean': Ribblr, knitCompanion, Pattern Keeper, My Row Counter and Stitch Fiddle compete on overlapping features (PDF import, stitch/row counting, charting, Ravelry sync) and differentiate mainly on price and platform, leaving feature-level differentiation largely exhausted within 2D playback. **Inference:** [claim:clm_inf03]
Across all six surveyed mobile/web incumbents (Ribblr, My Row Counter, Pattern Keeper, knitCompanion, Stitch Fiddle, and the Ravelry third-party connector ecosystem) none ships interactive 3D preview or guided physical-assembly, confirming the design-spec wedge ('see what I'm making', 'can't get lost', 'assemble/modify confidently') is unoccupied whitespace in the mobile category. **Inference:** [claim:clm_inf01]
Incumbent roadmaps are unlikely to close the 3D/assembly whitespace within ~12-18 months - Ribblr and knitCompanion are investing in 2D adjacencies (Ribbuild PDF conversion, Magic Markers, voice/scribble, chart recognition) rather than 3D, suggesting the whitespace is durable enough to enter, though a well-funded incumbent could license an engine like CrochetPARADE (GPLv3) faster than a from-scratch build. **Speculation:** [claim:clm_spec01]

## Academic feasibility vs product readiness

AmiGo establishes academic feasibility - not product readiness - for mesh-to-amigurumi-pattern generation: it is a deterministic (non-ML) crochet-graph pipeline shown in a paper to produce join-as-you-go sewing-free patterns from a closed mesh + seed point, but with documented geometric limits (no negative-mean/positive-Gaussian 'craters') and no demonstrated mobile runtime, so it sits on the 'shown in a paper' side of the line. **Inference:** [claim:clm_inf06]
CrochetPARADE's custom stitch grammar (parse-and-check before 3D render, with loose/tight stitch flagging) is a direct prior-art anchor for the Crochet IR v0.1 op-enum approach, validating that a structured, machine-checkable representation of crochet ops is feasible and that explicit validation reduces the ambiguity of plain-English patterns. **Inference:** [claim:clm_inf07]
The convergent design of CrochetPARADE's 3D view (rotate/zoom/pan, animate pattern creation, highlight/hide selected stitches) and crogen's real-time updating 3D model maps almost one-to-one onto the spec's required visualizer features (row/round highlighting, ghost-next-row, piece isolation), so the Pattern->3D visualizer (gate G3) is the lower-risk of the two spec capabilities. **Inference:** [claim:clm_inf08]
Every tool in the corpus that offers true interactive 3D crochet preview (CrochetPARADE, crogen) or 3D-mesh-to-pattern generation (AmiGo) is non-mobile - browser-desktop, Tkinter/Blender desktop, or an academic pipeline - so the 3D capability and the mobile form factor are currently disjoint, which is precisely the gap a mobile interactive-3D product would close. **Inference:** [claim:clm_inf02]

## Crochet IR alignment

Adopt Crochet IR v0.1 unchanged as the shared baseline rather than reinventing it - CrochetPARADE's grammar and AmiGo's crochet-graph both validate the core op-set, and the spec's visual_hint.shape_role (increase/straight/decrease/closure), expected_stitch_count, and assembly[] fields are exactly the metadata needed to power row highlighting, the stitch-count validator (EXP-002), and the join-as-you-go assembly view AmiGo demonstrates. **Inference:** [claim:clm_inf13]
CrochetPARADE's custom stitch grammar (parse-and-check before 3D render, with loose/tight stitch flagging) is a direct prior-art anchor for the Crochet IR v0.1 op-enum approach, validating that a structured, machine-checkable representation of crochet ops is feasible and that explicit validation reduces the ambiguity of plain-English patterns. **Inference:** [claim:clm_inf07]

## Product and technical implications

The product implication of the whitespace finding is that the wedge is positioning ('the crochet app that shows what you're making in 3D and never lets you lose your place'), differentiating against a commoditized 2D field; the technical implication is that delivering it requires owning the Crochet IR + stitch-graph + mobile-3D stack end-to-end, which is the same integration that creates the defensibility moat. **Inference:** [claim:clm_inf15]

## Contradictions & open disagreements

My Row Counter's price is unresolved - the live App Store listing showed IAP at $29.99 while prior key points cited ~$0.99/mo or $9.99/yr; the likely resolution is a tier/region/bundle difference (one-time unlock vs subscription), and the decision impact is LOW because pricing does not affect the 3D/assembly whitespace finding, only the competitive-pricing table footnote. **Inference:** [claim:clm_inf10]
Ribblr+ Gems framing disagrees - the spec/source summary treated Plus's 100 Gems as a recurring monthly allowance while the live page labels it a one-time 'joining gift' (recurring monthly applies only to Gold 100/mo and Platinum 400/mo); the live page wins as primary source, decision impact LOW, but it sharpens that only Gold/Platinum carry recurring marketplace currency. **Inference:** [claim:clm_inf11]

## Risks

Mobile-runtime performance is the top technical risk for a Pattern->3D product - existing 3D tools rely on Blender/three.js on desktop/web (CrochetPARADE local-only browser compute, crogen Blender) with no demonstrated polycount/framerate on a phone; mitigation is to precompute approximate low-poly stitch-graph meshes server-side or at import time and ship GLTF with per-round highlight groups rather than real-time fiber simulation, de-risked by the spec's EXP-012 mobile-rendering-feasibility experiment. **Speculation:** [claim:clm_spec02]
IP/licensing risk concentrates where user-imported third-party PDF patterns (which Ribblr, knitCompanion and Pattern Keeper all ingest) are transformed into derivative 3D representations; mitigation is to gate auto-3D/auto-mesh generation to user-authored or licensed patterns and amigurumi-first scope, avoiding unlicensed marketplace ingestion per the spec governance rules. **Speculation:** [claim:clm_spec03]
Generation crochetability is a correctness risk - AmiGo's documented inability to realize 'crater' geometries and its 'similar not exact' output mean a naive mesh->pattern feature would emit un-crochetable or distorted patterns for many user meshes; mitigation is to constrain v1 to primitive watertight shapes (sphere/egg/pear) with a stitch-count validator and round-trip evaluator before showing the user a pattern, matching gate G4's pass criteria. **Speculation:** [claim:clm_spec04]
UX trust failure - if an approximate 3D preview or ghost-next-row misrepresents the real fabric, it 'confuses more than helps' (gate G3 fail condition); mitigation is to render explicitly stylized low-fidelity stitch-graph geometry with confidence indicators rather than implying photoreal accuracy, and to validate row-highlight mapping accuracy before shipping. **Speculation:** [claim:clm_spec05]

| Risk | Severity | Likelihood | Mitigation | Evidence |
|------|----------|------------|------------|----------|
| Mobile-runtime performance for Pattern->3D | high | medium | Precompute low-poly stitch-graph meshes; ship GLTF with per-round highlight groups; validate via EXP-012 | [claim:clm_spec02] |
| IP/licensing on derivative 3D of imported PDFs | high | medium | Gate auto-3D/auto-mesh to user-authored/licensed patterns; amigurumi-first scope per governance | [claim:clm_spec03] |
| Generation crochetability of arbitrary meshes | medium | high | Constrain v1 to primitive watertight shapes; stitch-count validator + round-trip evaluator per G4 | [claim:clm_spec04] |
| UX trust failure from misleading approximate preview | medium | medium | Stylized low-fidelity geometry with confidence indicators; validate row-highlight mapping | [claim:clm_spec05] |

## Prototype experiments & decision-gate relevance

The assembled evidence most de-risks gates G2 (Crochet-IR viability) and G3 (Pattern->3D viability) and least de-risks G4 (mesh->pattern primitive) and G5 (MVP); the next experiments to run in priority order are EXP-001/002/003 (IR hello-world, stitch-count validator, repeat expansion) to close G2, then EXP-004/005/006 (IR->stitch-graph, stitch-graph->approximate-3D, row-highlight export) to close G3, deferring EXP-008/009/010 (mesh->pattern + round-trip) until after a working visualizer. **Inference:** [claim:clm_inf14]
CrochetPARADE's custom stitch grammar (parse-and-check before 3D render, with loose/tight stitch flagging) is a direct prior-art anchor for the Crochet IR v0.1 op-enum approach, validating that a structured, machine-checkable representation of crochet ops is feasible and that explicit validation reduces the ambiguity of plain-English patterns. **Inference:** [claim:clm_inf07]
The convergent design of CrochetPARADE's 3D view (rotate/zoom/pan, animate pattern creation, highlight/hide selected stitches) and crogen's real-time updating 3D model maps almost one-to-one onto the spec's required visualizer features (row/round highlighting, ghost-next-row, piece isolation), so the Pattern->3D visualizer (gate G3) is the lower-risk of the two spec capabilities. **Inference:** [claim:clm_inf08]
AmiGo establishes academic feasibility - not product readiness - for mesh-to-amigurumi-pattern generation: it is a deterministic (non-ML) crochet-graph pipeline shown in a paper to produce join-as-you-go sewing-free patterns from a closed mesh + seed point, but with documented geometric limits (no negative-mean/positive-Gaussian 'craters') and no demonstrated mobile runtime, so it sits on the 'shown in a paper' side of the line. **Inference:** [claim:clm_inf06]

| Decision gate | De-risk level from current evidence | Next experiments to run | Evidence |
|---------------|-------------------------------------|------------------------------|----------|
| G2 Crochet-IR viability | most de-risked | EXP-001/002/003 (IR hello-world, stitch-count validator, repeat expansion) | [claim:clm_inf14] |
| G3 Pattern->3D viability | most de-risked | EXP-004/005/006 (IR->stitch-graph, stitch-graph->approximate-3D, row-highlight export) | [claim:clm_inf14] |
| G4 mesh->pattern primitive | least de-risked | defer EXP-008/009/010 (mesh->pattern + round-trip) until visualizer exists | [claim:clm_inf14] |

## Recommendations and decision rules

Sequence the build visualizer-first (Pattern->3D, gate G3) before the mesh->pattern generator (gate G4), because the visualizer has multiple demonstrated implementations to borrow from while the generator rests on a single academic pipeline with geometric limits - matching the spec's own directive not to start mesh->pattern until Pattern->3D has a working prototype. **Inference:** [claim:clm_inf09]
Adopt Crochet IR v0.1 unchanged as the shared baseline rather than reinventing it - CrochetPARADE's grammar and AmiGo's crochet-graph both validate the core op-set, and the spec's visual_hint.shape_role (increase/straight/decrease/closure), expected_stitch_count, and assembly[] fields are exactly the metadata needed to power row highlighting, the stitch-count validator (EXP-002), and the join-as-you-go assembly view AmiGo demonstrates. **Inference:** [claim:clm_inf13]
On price, the mobile incumbents split into two monetization archetypes - one-time unlock (Pattern Keeper $9.00 forever; Stitch Fiddle non-renewing $5.50/mo or $33/yr) versus recurring subscription + marketplace (Ribblr+ $4.99-$9.99/mo with a buy/sell marketplace; knitCompanion tiered IAP) - so a 3D/assembly wedge can credibly anchor a premium subscription above the ~$5/mo charting tier without colliding with the $9 one-time floor. **Inference:** [claim:clm_inf05]
The product implication of the whitespace finding is that the wedge is positioning ('the crochet app that shows what you're making in 3D and never lets you lose your place'), differentiating against a commoditized 2D field; the technical implication is that delivering it requires owning the Crochet IR + stitch-graph + mobile-3D stack end-to-end, which is the same integration that creates the defensibility moat. **Inference:** [claim:clm_inf15]
The assembled evidence most de-risks gates G2 (Crochet-IR viability) and G3 (Pattern->3D viability) and least de-risks G4 (mesh->pattern primitive) and G5 (MVP); the next experiments to run in priority order are EXP-001/002/003 (IR hello-world, stitch-count validator, repeat expansion) to close G2, then EXP-004/005/006 (IR->stitch-graph, stitch-graph->approximate-3D, row-highlight export) to close G3, deferring EXP-008/009/010 (mesh->pattern + round-trip) until after a working visualizer. **Inference:** [claim:clm_inf14]

## Open questions

- What is the authoritative current price of My Row Counter given the $29.99 App Store IAP versus the ~$0.99/mo or $9.99/yr prior figures?
- Does any surveyed incumbent have an unannounced 3D or guided-assembly roadmap item not visible in current listings?
- What polycount and framerate does an approximate stitch-graph mesh achieve on a representative mid-tier phone?
- Which primitive watertight shapes beyond sphere/egg/pear pass the G4 crochetability bar without manual cleanup?

## Sources

- src_20260614_kw012_00: Ravelry: Apps that connect to Ravelry (official directory)
- src_20260614_kw012_01: Ribblr - Crochet & Knitting (Apple App Store listing)
- src_20260614_kw012_02: Upgrade and become a Ribblr+ member (official subscription page)
- src_20260614_kw012_03: My Row Counter App - Features (official site)
- src_20260614_kw012_04: Stitch Fiddle Premium pricing (official)
- src_20260614_kw012_05: Pattern Keeper (official site)
- src_20260614_kw012_06: knitCompanion knitting & more (Apple App Store listing)
- src_20260614_kw012_07: CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger) - GitHub repo
- src_20260614_kw012_08: CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260614_kw012_09: CrochetPARADE README (GitHub)
- src_20260614_kw012_10: crogen: 3D Crochet Pattern Maker (GitHub)
- src_20260614_kw012_11: AmiGo: Computational Design of Amigurumi Crochet Patterns
