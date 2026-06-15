---
schema_version: '0.1'
type: research_report
report_id: report_20260615_as_of_mid_2026_what_is
title: As of mid-2026, what is the competitive feature,
intent_id: intent_research_20260614_as_of_mid_2026_what_is
evidence_bundle_id: pending
created_at: '2026-06-15T09:36:38-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

Pattern Keeper costs $9.00 as a one-time in-app purchase granting permanent (use-forever) access. [claim:clm_001]
The app offers a one-month free trial that includes access to all features. [claim:clm_002]
Core features include viewing the chart as one continuous pattern across page breaks, symbol search/highlight, and stitch selection by clicking or dragging in any direction including diagonally. [claim:clm_003]
Progress tracking marks finished stitches (coloring them with the thread color) and the thread list shows the number of stitches left per color. [claim:clm_004]
Pattern Keeper works with PDF charts from designers including Heaven and Earth Designs, Paine Free Crafts, Charting Creations, and Artecy, plus other compatible-charting-software designers. [claim:clm_005]
Photographed paper patterns can be imported but lose key functionality: you cannot search or add thread numbers. [claim:clm_006]
Android support requires version 4.1 or later with Google Play Store; at least 2GB RAM is recommended and Android 8.1 should be avoided as unstable. [claim:clm_007]
An iOS version is in early development and not yet available; users can sign up for an iOS newsletter to be notified about the first test version. [claim:clm_008]
Stitch Fiddle's free tier caps usage at 15 charts, 50 unique colors/symbols per chart, and a maximum grid of 300x300 (90,000 stitches). [claim:clm_009]
Premium raises limits to unlimited charts, 250 unique colors/symbols per chart, and a maximum grid of 1,000x1,000 (1,000,000 stitches). [claim:clm_010]
Premium costs $5.50 for one month or $33.00 per year, an annual price the vendor frames as a 50% discount equal to $2.75 per month. [claim:clm_011]
Subscriptions are one-off payments with no automatic renewal and expire automatically at the end of the chosen period. [claim:clm_012]
Premium unlocks image upload, multi-user collaboration, QR-coded charts, vector/Word/Excel exports, automatic knitting-chart error checking, and conversion of charts into written knitting/crochet instructions. [claim:clm_013]
Stitch Fiddle is browser-based across Windows, Mac, Android, iOS, Linux, and Chromebook, with charts automatically synced across a user's devices and no install required. [claim:clm_014]
CrochetPARADE is a platform for creating, visualizing, and analyzing both 2D and 3D crochet patterns. [claim:clm_015]
The site was last updated February 13, 2026. [claim:clm_016]
The platform is tested on latest Chrome, Brave, and Firefox, has Safari issues, and is not designed for mobile devices. [claim:clm_017]
All calculations run locally in the browser with no data collected to a central server or transmitted over the internet. [claim:clm_018]
Users can export to a GLTF 3D file that is compatible with Blender. [claim:clm_019]
Users can save the pattern as a Standard Crochet Chart in SVG format, and save the crochet instructions as text. [claim:clm_020]
The platform and its computational components are free and open source under GPLv3, intended to remain free and open to all in perpetuity. [claim:clm_021]
Recent additions include a Remesher that turns a 3D model into crochet instructions and a new STL export for resizing patterns and 3D-printing a model. [claim:clm_022]
knitCompanion is published by Create2Thrive Inc. and is positioned as a multi-craft project tracker spanning knitting, crochet, and cross-stitch. [claim:clm_023]
The free kCBasics tier provides row and along-the-row progress tracking, per-project counters, and iCloud sync. [claim:clm_024]
The free tier can import patterns by linking to Ravelry and Dropbox and supports adding any PDF pattern. [claim:clm_025]
knitCompanion works with any pattern, including adding PDFs, and is pitched for mystery knit-a-longs. [claim:clm_026]
Paid tiers add Magic Markers for counting, highlighting, and coloring stitches over the pattern. [claim:clm_027]
Paid tiers add Intelligent Chart Recognition to speed up chart setup. [claim:clm_028]
Paid tiers add Scribble annotation and hands-free voice command control. [claim:clm_029]
knitCompanion runs on iPhone, iPad, and Mac (iOS/iPadOS 16.4+, macOS 13.3+), rated 4+ in the Lifestyle category, with the listing reflecting version 3.0.20 (Dec 2025). [claim:clm_030]
crogen is desktop crochet software where users build a crochet pattern through a GUI by adding rows and stitch types via buttons. [claim:clm_031]
As the user constructs the pattern, a 3D model updates in real time to preview what the finished crocheted piece would look like. [claim:clm_032]
On completion the tool generates a written pattern that, when followed, produces a crochet piece matching the 3D design. [claim:clm_033]
crogen is implemented in Python (100% of the codebase) using the Tkinter UI library and Blender for 3D rendering, making it a desktop application rather than mobile. [claim:clm_034]
Running crogen requires a pre-existing Blender and Tkinter installation, with remaining dependencies installed via pip, indicating a developer-oriented setup rather than a packaged consumer app. [claim:clm_035]
crogen is a low-maturity hobbyist project (about 3 stars, 0 forks, 36 commits) with no explicit license declared in the README. [claim:clm_036]
CrochetPARADE uses a custom language grammar that lets users define stitches and stitch patterns, then parses and checks a submitted pattern for correctness before building a virtual model rendered in 3D. [claim:clm_037]
The custom grammar is intended to ensure accuracy and precision in pattern instructions, avoiding the ambiguities of plain-English crochet instructions. [claim:clm_038]
The platform flags overly loose or tight stitches so users can replace them before crocheting, reducing the need for blocking. [claim:clm_039]
The interactive 3D view supports rotate, zoom, and pan, animation of the pattern creation process, highlighting and hiding selected stitches, and changing yarn thickness and color. [claim:clm_040]
Export includes an auto-generated crochet chart using standard crochet symbols and an SVG image showing stitch connections that labels stitches by type, row number, and position within a row. [claim:clm_041]
CrochetPARADE is built on the JavaScript libraries SVG.js and three.js and can export projects to 3D files importable into Blender. [claim:clm_042]
AmiGo takes a closed triangle mesh plus a single user-specified point and generates crochet instructions that, when knitted and stuffed, produce an Amigurumi toy resembling the input geometry. [claim:clm_043]
The pipeline works by constructing a 'Crochet Graph' (geometry plus connectivity) that is then translated into a human-readable crochet pattern. [claim:clm_044]
The shape is automatically segmented into crochetable components joined via the join-as-you-go method, eliminating any need for sewing. [claim:clm_045]
The full input is a closed 3D model, a seed point, and a stitch size; the generated instructions use only simple crochet stitches and are join-as-you-go, so no sewing is required. [claim:clm_046]
The authors claim the crocheted-and-stuffed output resembles the input 3D shape more closely than any previous approach to crochet instruction generation. [claim:clm_047]
Crochet cannot be easily automated and, unlike machine knitting, there exists no crochet machine to date, motivating a computational pattern-generation method. [claim:clm_048]
The crochet graph is converted to a program using standard code-synthesis tools, then loop-unrolled into a human-readable pattern, confirming a deterministic algorithmic (not ML-based) pipeline. [claim:clm_049]
The method has inherent geometric limits: surfaces with negative mean curvature and positive Gaussian curvature ('craters') cannot be realized by crocheting and stuffing alone and must be preprocessed away. [claim:clm_050]
Ribblr's core differentiator is interactive ePatterns offering cross-device crafting, per-user progress tracking, custom-size views, and built-in video tutorials. [claim:clm_051]
Ribblr's Ribbuild tooling lets users personalize patterns and convert PDFs into interactive ePatterns. [claim:clm_052]
Ribblr operates a buy/sell pattern marketplace where any user can open a shop quickly. [claim:clm_053]
Ribblr ships across the Apple ecosystem: iPhone/iPad/iPod touch (iOS/iPadOS 14.5+), Mac (macOS 11.3+ with Apple M1+), and Apple Vision (visionOS 1.0+). [claim:clm_054]
Ribblr version 3.02 was released April 13 (2025), the app is rated 4.2 out of 5 from 468 ratings, and the download is approximately 4 MB. [claim:clm_055]
Ribblr is free to download with free and premium patterns plus in-app purchases. [claim:clm_056]
The listing advertises no 3D visualization or guided-assembly feature, indicating the strongest pattern+tracking incumbent does not contest that whitespace as of this version. [claim:clm_057]
CrochetPARADE is a platform for creating, visualizing, and analyzing both 2D and 3D crochet patterns using a custom language grammar that lets users define stitches and stitch patterns. [claim:clm_058]
The custom grammar is designed to remove the ambiguity of plain-English crochet instructions, aiming for accuracy and precision. [claim:clm_059]
The platform's debug capability flags overly loose or tight stitches so users can replace them before crocheting, reducing the need for blocking. [claim:clm_060]
The interactive 3D view supports rotate/zoom/pan, animation of the pattern-creation process, highlighting/hiding selected stitches, and changing yarn thickness and color. [claim:clm_061]
Exports include an automatically generated crochet chart in standard symbols, an SVG identifying stitches by type/row/position, and 3D files importable into Blender. [claim:clm_062]
All calculations are performed locally on the user's device, with no data collected to a central server or transmitted over the internet - relevant to mobile-runtime feasibility. [claim:clm_063]
The software is free and open source under GPLv3, while the grammar itself cannot be copyrighted and is in the public domain; the project is hosted at crochetparade.org. [claim:clm_064]
Ravelry states there is no official first-party Ravelry app and that the page is a directory of third-party apps built by Ravelers and other developers. [claim:clm_065]
knitCompanion is listed as a Ravelry-connected pattern-tracking app for knitters and fiber artists, and is one of the higher-traffic connectors on the directory. [claim:clm_066]
Multiple third-party row-counter and project-tracking connectors exist (Row Counter, YarnBuddy, Pocket Knitting, Pocket Crochet, Loopsy), each syncing project tracking with Ravelry. [claim:clm_067]
Pattern discovery and management is served by several connectors including kntd:discover, Pattrick, Ravelgurumi (amigurumi-specific), and Ravit/Ravit 2, which browse the Ravelry pattern and yarn databases. [claim:clm_068]
Yarn Squirrel is a connector that brings a user's full Ravelry library to iPhone/iPad and stores their PDF patterns alongside it. [claim:clm_069]
Stitch Fiddle is listed as a connected pattern-design tool spanning knitting, cross stitch, and crochet. [claim:clm_070]
Stash management is served by third-party connectors including Yarn Stasher (AI-powered Smart Scan), YarnCat, and YarnBuddy, all integrating with Ravelry. [claim:clm_071]
My Row Counter offers direct Ravelry integration that imports the user's existing yarn stash from Ravelry into the app. [claim:clm_072]
The app can search Ravelry to auto-import full yarn details rather than requiring manual entry. [claim:clm_073]
The built-in Charts tool lets users create a knit/crochet chart from scratch or by transforming an image into a chart. [claim:clm_074]
Chart cells can be filled with stitch symbols chosen from a list or with user-created custom symbols. [claim:clm_075]
An Apple Watch version is available and supports watchOS 5 and higher. [claim:clm_076]
The app supports Android watches running Wear OS and is compatible with Fitbit Sense or Versa 3 (Garmin via Connect IQ). [claim:clm_077]
Seller Mode automatically calculates time-spent cost from the configured hourly rate and the project timer, and is enabled per currency and hourly rate. [claim:clm_078]
Seller Mode displays the profit from a sale on the project settings page after a project is marked for sale with costs and a price. [claim:clm_079]
Ribblr+ has three monthly USD tiers - Plus at $4.99/mo (listed $6.99), Gold at $6.99/mo (listed $9.99), and Platinum at $9.99/mo (listed $13.99). [claim:clm_080]
Annual billing saves 30% across all Ribblr+ tiers. [claim:clm_081]
A 14-day free trial precedes auto-renewal; on day 14 the membership auto-renews and the member is charged. [claim:clm_082]
All tiers include unlimited daily free patterns, pinning/saving patterns in boards, adding external (PDF) patterns, no ads, and Focus Mode. [claim:clm_083]
Monthly Gems allowance differs by tier: Plus's 100 Gems is a joining gift, Gold grants 100 Gems every month, and Platinum grants 400 Gems every month. [claim:clm_084]
Membership enables adding external PDF patterns to the user's library. [claim:clm_085]
Plans are cancel-anytime, and tier changes use pro-rata pricing so an upgrade only charges the difference between tiers. [claim:clm_086]

## Inferences

**Inference:** Across all six surveyed mobile/web incumbents (Ribblr, My Row Counter, Pattern Keeper, knitCompanion, Stitch Fiddle, and the Ravelry third-party connector ecosystem) none ships interactive 3D preview or guided physical-assembly, confirming the design-spec wedge ('see what I'm making', 'can't get lost', 'assemble/modify confidently') is unoccupied whitespace in the mobile category. [claim:clm_inf01]
**Inference:** Every tool in the corpus that offers true interactive 3D crochet preview (CrochetPARADE, crogen) or 3D-mesh-to-pattern generation (AmiGo) is non-mobile - browser-desktop, Tkinter/Blender desktop, or an academic pipeline - so the 3D capability and the mobile form factor are currently disjoint, which is precisely the gap a mobile interactive-3D product would close. [claim:clm_inf02]
**Inference:** The pattern+counter mobile segment is a 'red ocean': Ribblr, knitCompanion, Pattern Keeper, My Row Counter and Stitch Fiddle compete on overlapping features (PDF import, stitch/row counting, charting, Ravelry sync) and differentiate mainly on price and platform, leaving feature-level differentiation largely exhausted within 2D playback. [claim:clm_inf03]
**Inference:** The design-spec claim that Ravelry has no official native mobile app and the ecosystem is third-party connectors is CONFIRMED by current evidence: Ravelry's own directory states there is no first-party app and lists connectors (knitCompanion, Row Counter, YarnBuddy, Pocket Crochet, Ravelgurumi, Yarn Squirrel, Stitch Fiddle) built by third parties. [claim:clm_inf04]
**Inference:** On price, the mobile incumbents split into two monetization archetypes - one-time unlock (Pattern Keeper $9.00 forever; Stitch Fiddle non-renewing $5.50/mo or $33/yr) versus recurring subscription + marketplace (Ribblr+ $4.99-$9.99/mo with a buy/sell marketplace; knitCompanion tiered IAP) - so a 3D/assembly wedge can credibly anchor a premium subscription above the ~$5/mo charting tier without colliding with the $9 one-time floor. [claim:clm_inf05]
**Inference:** AmiGo establishes academic feasibility - not product readiness - for mesh-to-amigurumi-pattern generation: it is a deterministic (non-ML) crochet-graph pipeline shown in a paper to produce join-as-you-go sewing-free patterns from a closed mesh + seed point, but with documented geometric limits (no negative-mean/positive-Gaussian 'craters') and no demonstrated mobile runtime, so it sits on the 'shown in a paper' side of the line. [claim:clm_inf06]
**Inference:** CrochetPARADE's custom stitch grammar (parse-and-check before 3D render, with loose/tight stitch flagging) is a direct prior-art anchor for the Crochet IR v0.1 op-enum approach, validating that a structured, machine-checkable representation of crochet ops is feasible and that explicit validation reduces the ambiguity of plain-English patterns. [claim:clm_inf07]
**Inference:** The convergent design of CrochetPARADE's 3D view (rotate/zoom/pan, animate pattern creation, highlight/hide selected stitches) and crogen's real-time updating 3D model maps almost one-to-one onto the spec's required visualizer features (row/round highlighting, ghost-next-row, piece isolation), so the Pattern->3D visualizer (gate G3) is the lower-risk of the two spec capabilities. [claim:clm_inf08]
**Inference:** RECOMMENDATION: sequence the build visualizer-first (Pattern->3D, gate G3) before the mesh->pattern generator (gate G4), because the visualizer has multiple demonstrated implementations to borrow from while the generator rests on a single academic pipeline with geometric limits - matching the spec's own directive not to start mesh->pattern until Pattern->3D has a working prototype. [claim:clm_inf09]
**Inference:** CONTRADICTION: My Row Counter's price is unresolved - the live App Store listing showed IAP at $29.99 while prior key points cited ~$0.99/mo or $9.99/yr; the likely resolution is a tier/region/bundle difference (one-time unlock vs subscription), and the decision impact is LOW because pricing does not affect the 3D/assembly whitespace finding, only the competitive-pricing table footnote. [claim:clm_inf10]
**Inference:** CONTRADICTION: Ribblr+ Gems framing disagrees - the spec/source summary treated Plus's 100 Gems as a recurring monthly allowance while the live page labels it a one-time 'joining gift' (recurring monthly applies only to Gold 100/mo and Platinum 400/mo); the live page wins as primary source, decision impact LOW, but it sharpens that only Gold/Platinum carry recurring marketplace currency. [claim:clm_inf11]
**Inference:** DEFENSIBILITY (inference): the 3D/guided-assembly wedge is more durable than a feature within the red-ocean charting segment because it requires a vertically integrated stack - Crochet IR + stitch-graph + approximate-3D layout + mobile renderer - that no incumbent has assembled and that the existing 3D tools deliberately scoped to non-mobile, raising the replication cost above a simple feature copy. [claim:clm_inf12]
**Inference:** IR ALIGNMENT (recommendation): adopt Crochet IR v0.1 unchanged as the shared baseline rather than reinventing it - CrochetPARADE's grammar and AmiGo's crochet-graph both validate the core op-set, and the spec's visual_hint.shape_role (increase/straight/decrease/closure), expected_stitch_count, and assembly[] fields are exactly the metadata needed to power row highlighting, the stitch-count validator (EXP-002), and the join-as-you-go assembly view AmiGo demonstrates. [claim:clm_inf13]
**Inference:** DECISION-GATE (recommendation): the assembled evidence most de-risks gates G2 (Crochet-IR viability) and G3 (Pattern->3D viability) and least de-risks G4 (mesh->pattern primitive) and G5 (MVP); the next experiments to run in priority order are EXP-001/002/003 (IR hello-world, stitch-count validator, repeat expansion) to close G2, then EXP-004/005/006 (IR->stitch-graph, stitch-graph->approximate-3D, row-highlight export) to close G3, deferring EXP-008/009/010 (mesh->pattern + round-trip) until after a working visualizer. [claim:clm_inf14]
**Inference:** PRODUCT vs TECHNICAL IMPLICATION: the product implication of the whitespace finding is that the wedge is positioning ('the crochet app that shows what you're making in 3D and never lets you lose your place'), differentiating against a commoditized 2D field; the technical implication is that delivering it requires owning the Crochet IR + stitch-graph + mobile-3D stack end-to-end, which is the same integration that creates the defensibility moat. [claim:clm_inf15]

## Speculation

**Speculation:** PREDICTION (speculation): incumbent roadmaps are unlikely to close the 3D/assembly whitespace within ~12-18 months - Ribblr and knitCompanion are investing in 2D adjacencies (Ribbuild PDF conversion, Magic Markers, voice/scribble, chart recognition) rather than 3D, suggesting the whitespace is durable enough to enter, though a well-funded incumbent could license an engine like CrochetPARADE (GPLv3) faster than a from-scratch build. [claim:clm_spec01]
**Speculation:** RISK (speculation, severity high, likelihood medium): mobile-runtime performance is the top technical risk for a Pattern->3D product - existing 3D tools rely on Blender/three.js on desktop/web (CrochetPARADE local-only browser compute, crogen Blender) with no demonstrated polycount/framerate on a phone; mitigation is to precompute approximate low-poly stitch-graph meshes server-side or at import time and ship GLTF with per-round highlight groups rather than real-time fiber simulation, de-risked by the spec's EXP-012 mobile-rendering-feasibility experiment. [claim:clm_spec02]
**Speculation:** RISK (speculation, severity high, likelihood medium): IP/licensing risk concentrates where user-imported third-party PDF patterns (which Ribblr, knitCompanion and Pattern Keeper all ingest) are transformed into derivative 3D representations; mitigation is to gate auto-3D/auto-mesh generation to user-authored or licensed patterns and amigurumi-first scope, avoiding unlicensed marketplace ingestion per the spec governance rules. [claim:clm_spec03]
**Speculation:** RISK (speculation, severity medium, likelihood high): generation crochetability is a correctness risk - AmiGo's documented inability to realize 'crater' geometries and its 'similar not exact' output mean a naive mesh->pattern feature would emit un-crochetable or distorted patterns for many user meshes; mitigation is to constrain v1 to primitive watertight shapes (sphere/egg/pear) with a stitch-count validator and round-trip evaluator before showing the user a pattern, matching gate G4's pass criteria. [claim:clm_spec04]
**Speculation:** RISK (speculation, severity medium, likelihood medium): UX trust failure - if an approximate 3D preview or ghost-next-row misrepresents the real fabric, it 'confuses more than helps' (gate G3 fail condition); mitigation is to render explicitly stylized low-fidelity stitch-graph geometry with confidence indicators rather than implying photoreal accuracy, and to validate row-highlight mapping accuracy before shipping. [claim:clm_spec05]

## Open questions

- None recorded.

## Sources

- src_20260614_kw012_05: Pattern Keeper (official site)
- src_20260614_kw012_04: Stitch Fiddle Premium pricing (official)
- src_20260614_kw012_08: CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger)
- src_20260614_kw012_06: knitCompanion knitting & more (Apple App Store listing)
- src_20260614_kw012_10: crogen: 3D Crochet Pattern Maker (GitHub)
- src_20260614_kw012_09: CrochetPARADE README (GitHub)
- src_20260614_kw012_11: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw012_01: Ribblr - Crochet & Knitting (Apple App Store listing)
- src_20260614_kw012_07: CrochetPARADE (Crochet PAttern Renderer, Analyzer, and DEbugger) - GitHub repo
- src_20260614_kw012_00: Ravelry: Apps that connect to Ravelry (official directory)
- src_20260614_kw012_03: My Row Counter App - Features (official site)
- src_20260614_kw012_02: Upgrade and become a Ribblr+ member (official subscription page)
