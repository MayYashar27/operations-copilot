"""Assemble REPORT.md for this live run. Agent text is copied verbatim from the JSON records;
ground truth and evaluation are the reviewer's, kept in separate, labelled sections."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = ["S29", "S30", "S16", "S03", "S05", "S07"]

REVIEW = {
"S29": {
"truth": """- Period 1 (2026-08-25 to 2026-09-01): **1,199 requests over 6 working days = 199.83/day**.
- Period 2 (2026-09-02 to 2026-09-07): **800 requests over 4 working days = 200.0/day** (5–6 Sep is a weekend).
- Every working day had 200 requests except 2026-08-27 (199). **There was no drop**; the raw −33% is entirely the 2-day difference.
- Correct answer: no drop per working day (+0.08%). Phase 0 run R8 got this wrong (reported a 33% drop).""",
"eval": """| Dimension | Assessment |
|---|---|
| Factual accuracy | **Correct.** Every number in the structured result matches the data (140 numbers checked: 133 direct, 7 one-step derivations, 0 unsupported). |
| Completeness | Complete for the question. Also reported the three incident hours, which is relevant context. |
| Reasoning | **Correct conclusion with sound reasoning** in the structured result: working days counted, per-day comparison used, the raw difference explained. This is the H2 failure from Phase 0, now answered correctly. |
| Unsupported claims | None material. |""",
"issues": """- **Tool-argument error (low):** `compare_values(current=1200, baseline=1199, current_days=6, baseline_days=6)` — 1,200 and 6 days are not Period 2's figures (800 over 4 days). The per-day result (+0.17/day, +0.08%) is right only because 1,200/6 = 200 = 800/4. The answer's numbers are correct; the call that "supports" them is not.
- **Visible self-correction in the narrative (low, presentation):** the first table says "Period 2 | 6 (2, 3, 4, 7 Sep) — wait, see note below", then a corrected table follows. A manager reading the Technical view sees the model correcting itself mid-answer.
- **Unneeded missing-evidence item (low):** asks for "intra-day hourly breakdowns for all working days in Period 2 to confirm whether the absence of anomalies is complete or a detection gap" — the anomaly tool already checked every day.""",
},
"S30": {
"truth": """- **Volume:** flat, ~200 requests per working day; 628 abandoned calls in working hours.
- **Three incident hours:** 2026-08-25 12:00 (login failures after an app update, demand-side), 2026-08-26 14:00 (cross-category **mobile-app** issue, demand-side), 2026-08-27 15:00 (**staffing shortage**: 8 agents on shift vs 12, plus demand).
- **A04:** transfers 33.87% (62 req) → 57.58% (66 req) vs peers 23.13%; concentrated on technical_support (34 of 38 later transfers).
- **A07:** transfer rate 18.33% → 37.04% while handling time fell 6.01 → 3.95 min; notes under six words went from 0/60 to 35/54. Signal `FASTER_HANDLING_WITH_MORE_TRANSFERS`.
- **A09:** later transfer rate 40.0% vs peers 24.13%, explained by case mix (85 technical-issue requests of 154; longest handling time 10.47 min).
- So: 6 planted issues (3 incidents, A04, A07, A09). Phase 0 run R8 surfaced 1 of 6.""",
"eval": """| Dimension | Assessment |
|---|---|
| Factual accuracy | **High.** 382 numbers checked, all present in the tool results. One scope mislabel (below). |
| Completeness | **5 of 6 planted issues surfaced** (all three incident hours, A04, A09 case mix; staffing on 27 Aug identified). **A07 is missing entirely.** The 26 Aug incident is found but its cause (mobile-app problem) was not investigated. |
| Reasoning | **Good.** Distinguished demand-side spikes (25 and 26 Aug, full staffing) from the combined demand + staffing incident (27 Aug); framed A09 as likely case mix rather than poor performance; kept the root cause unconfirmed. Large improvement over Phase 0 R8. |
| Unsupported claims | A few weak generalisations (below); no invented numbers or IDs. |""",
"issues": """- **Missed planted finding (medium): A07.** The agent checked signals only for A04 and A09, the two highest transfer rates over 10 days. A07's problem is a *trend* (faster handling, more transfers, degrading notes), invisible in the 10-day average (27.19%, near the team's 25.86%). The rule "report every one outside the normal range" does not reach trend-only problems; the agent did not run signal checks across all agents.
- **Scope mislabel (medium) — the H3 failure type:** observed fact: *"A04's elevated transfer rate in the later half spans all four classifications: general information 47.83% (23 requests), login issue 40.54% (37 requests), payment issue 48.72% (39 requests), technical issue 48.28% (29 requests)."* These are the **10-day** figures (23+37+39+29 = 128 = all of A04's requests). Actual later-half rates: 60.0% (6/10), 52.6% (10/19), 60.0% (15/25), 58.3% (7/12). The direction ("elevated in all four") is still true, but the period attached to the numbers is wrong. The supported pattern repeats it correctly as "in the 10-day period".
- **26 Aug cause not investigated (medium, completeness):** labelled "demand-side" correctly, but no request details were read, so the mobile-app theme (planted) was not found. Only 25 Aug got request-level analysis.
- **Mixed-period comparison (low):** A09's 10-day handling time (10.47 min) is compared with peers' *later-half* average (6.62 min), giving "~58% longer than peers".
- **Weak generalisations (low):** "Warning sign #2 — early-week elevated **transfers** & abandonment": abandonment is clearly higher on 25–27 Aug (75/73/100 vs 48–62), but transfer rates are not (25.5–30.5% early vs 20.0–30.5% later; 7 Sep equals 25 Aug at 30.5%). "Payment (60) and technical (51) issues are elevated" on 7 Sep: payment ranged 41–65 and technical 40–54 over the period, so 60 and 51 are within the normal range.
- **Approximation (low):** team technical-issue transfer rate shown as "~25%"; actual 26.69% (22.22% excluding A09).
- **Wrong count (medium) — added after the 2026-11-15 review:** an observed fact and the narrative both say "**45 login_issue requests** arrived in one hour" on 25 Aug 12:00–13:00. 45 is the hour's total; login issues were 40 (as the answer itself states two facts later). Cause: the anomaly and capacity tools reported only the hour's total, and the model attached it to the dominant category.
- **Contradictory wording (low) — added after the 2026-11-15 review:** the narrative says request-level evidence "confirms this across all 40 requests reviewed", while only 36 of the 40 match the update theme (stated in the next line).""",
},
"S16": {
"truth": """- A04 earlier half (2026-08-25..08-31, 5 working days): **62 requests, 21 transfers, 33.87%**; later half (09-01..09-07): **66 requests, 38 transfers, 57.58%**; peers later 23.13% (934 requests). Signals: RISING_TRANSFER_RATE, HIGH_TRANSFER_RATE_VS_PEERS.
- Destinations: earlier technical_support 10, billing 5, back_office 4, supervisor 2; later **technical_support 34 of 38**. 10-day: technical_support 44 of 59.
- 2026-09-07 alone: 9 requests, 8 transferred (88.89%), all to technical_support — a **low-sample single day**.
- Per-category rates before 7 Sep were 35–50%, **not near 100%** (Phase 0 run R6 claimed near-100% across the period).""",
"eval": """| Dimension | Assessment |
|---|---|
| Factual accuracy | **Correct.** 128 numbers checked, all traceable. Cited request IDs (e.g. 20162, 30022, 30127, 30133, 70077, 70147) exist, belong to A04, and have the stated classification and destination. |
| Completeness | Complete: trend, peer comparison, daily series, destination shift, documentation, sample size stated (30 of 38 reviewed). |
| Reasoning | **Good, and the Phase 0 H3 failure did not recur:** the 88.89% is attributed to "2026-09-07 (today)", not to the period; the period comparison uses equal halves and says so. Hypotheses are labelled and proportionate. |
| Unsupported claims | None material. |""",
"issues": """- **Tool misuse (low):** `compare_values(57.58, 33.87, current_days=5, baseline_days=5)` divides *rates* by days ("current_per_day 11.52"), which is meaningless. The answer only used the valid parts (+23.71 pp, +70%).
- **Answer-check warnings (informational):** two scope-wording warnings ("trended upward across the period", "consistently uses a brief one-sentence template"). On review both are supported: the daily series does rise, and the template appears in all 21 + 30 reviewed notes. The checker is doing its job; these are acceptable.
- **Interpretation to verify by a human (low):** "documentation follows a near-identical template" is true, but in this synthetic dataset 502 of 517 transfer notes across all agents end with the same template, so it is not specific to A04. The answer does not claim it is unique to A04.""",
},
"S03": {
"truth": """- 2026-08-27 15:00–16:00: **45 requests** vs 20 the hour before and 22.22 typical; **8 agents on shift vs 12** (previous hour and typical); available agents **0.33 vs 5.01**; wait **12.49 vs 4.41 min**; **46 abandoned vs 5.67** typical. Staffing returns to 12 at 16:00.
- Classifications spread: payment 16, login 10, technical 10, general 9 (no category dominates).
- **Planted cause: staffing shortage** (the generator also gives every incident hour 45 requests, so demand rose too). Phase 0 run R2 missed staffing entirely.""",
"eval": """| Dimension | Assessment |
|---|---|
| Factual accuracy | **Correct** on all capacity and demand figures. Theme counts are consistent (11 + 5 = 16 payment; 9 + 5 + 4 = 18). The five "misrouted" IDs exist and are mismatched as stated. |
| Completeness | Complete: demand, capacity, classifications, request themes, routing. |
| Reasoning | **The planted staffing cause is now identified** as one of two simultaneous factors, with the right evidence (8 vs 12 agents, 0.33 available, all agents busy). Root cause correctly left unconfirmed. Major improvement over Phase 0 R2. |
| Unsupported claims | A speculative platform-event hypothesis and some embellishment (below). |""",
"issues": """- **Speculative hypothesis (low–medium):** "login failures, browser access difficulties, and notification delivery issues across 18 requests … may suggest an underlying platform or access-layer event". These are ordinary background categories (the previous hour already had 8 technical issues) and their notes describe routine problems (incorrect passwords, password resets). It is labelled a hypothesis, but the evidence for it is thin and it competes with the staffing finding for the manager's attention.
- **Over-interpretation (low):** narrative: "**4 agents left the shift at 15:00**" and "the team was overwhelmed within minutes". The data shows 8 agents on shift during 15:00–15:55 and 12 again at 16:00 — a temporary drop of unknown cause; "left the shift" and "within minutes" are not in the data.
- **Imprecise description (low):** "technical and login issues sent to billing" — one of the five IDs (30141) is a billing inquiry sent to technical support.
- **Answer-check warnings:** "18" (a correct sum of theme counts — the model's own arithmetic) and "1.5×" (a recommended threshold, not a data claim). Both acceptable on review.""",
},
"S05": {
"truth": """- Viewing 2026-08-27. Afternoon average wait by hour: 12:00 **4.55**, 13:00 **3.90**, 14:00 **4.95**, **15:00 12.49**, 16:00 **4.22** min. The long wait is concentrated in 15:00–16:00.
- In that hour: 8 agents on shift vs 12 typical, 0.33 available vs 5.01, 45 requests vs 22.22 typical, 46 abandoned. Staffing back to 12 at 16:00.
- Planted cause: staffing shortage (with the incident hour's higher demand).""",
"eval": """| Dimension | Assessment |
|---|---|
| Factual accuracy | **Correct.** 117 numbers checked; all traceable. |
| Completeness | Good: identifies the one abnormal hour and both causes. Does not show the other afternoon hours' waits to prove the concentration, though the day average and the anomaly tool support it. |
| Reasoning | **Correct and concise:** demand surge plus staffing shortfall, root cause not confirmed, causes of the staffing drop left open. |
| Unsupported claims | One unsupported recommendation (below). |""",
"issues": """- **Unsupported generalisation (low–medium):** recommendation "Monitor 15:00–17:00 as a risk window — the data suggests this late-afternoon period may be **structurally under-staffed** relative to demand." The data shows the opposite outside the incident: 16:00 had 12 agents and a 4.22-min wait, and the typical 15:00 window (other days) has 12 agents and 4.41 min. One incident hour does not show a structural problem.
- **Redundant missing-evidence item (low):** asks for hourly volume over the 9-day window "to determine whether 15:00–16:00 is structurally higher-volume" — the capacity tool's typical value (22.22 requests) already answers this.""",
},
"S07": {
"truth": """- Viewing 2026-08-25. Busiest hour **12:00–13:00 with 45 requests** (other hours 18–21).
- **login_issue drove it: 40 of 45 (89%)**.
- **23 of the 40 login requests were transferred** (escalated): technical_support 12, billing 7, supervisor 2, back_office 2; 17 resolved. (All requests in the hour: 24 transferred.)
- Context: wait 11.47 vs 4.35 min typical; full staffing (12); planted cause = login failures after an app update (not asked).""",
"eval": """| Dimension | Assessment |
|---|---|
| Factual accuracy | **Correct** on all three parts of the question. |
| Completeness | Complete; adds useful capacity context (demand-side, full staffing). |
| Reasoning | Sound: separates demand from staffing; hypotheses labelled. |
| Unsupported claims | None material. |""",
"issues": """- **Mislabelled percentage (low):** summary: "a surge in **login issues (+89% of the spike)**" — 89% is login's *share* of the hour, not an increase. Flagged by the answer checks.
- **Weak hypothesis (low):** "transfers to billing (7) alongside technical_support (12) … may suggest the login issues had multiple distinct root causes". In this dataset transfer destinations are noisy across all categories; the routing spread is not evidence of several causes. Labelled as a hypothesis.
- **Unneeded missing evidence (low):** asks for "request-level detail" — available through `get_request_details`, but not needed for the question asked (cause was not asked), so acceptable.""",
},
}

ARTEFACTS = """**About the automatic grader's FAIL verdicts.** The grader (`evals/grade_scenario.py`,
unchanged as instructed) was written before the remediation, so two of its checks produce
failures that are artefacts of the harness, not agent errors:

1. *"no invalid tool arguments: unknown tool 'get_daily_series' / 'detect_volume_anomalies' /
   'get_capacity_context'"* — the argument validator's list of known tools predates the three new
   tools. The calls themselves were valid and returned data.
2. *"tool: count_requests"* / *"tool: get_monitor_metrics"* missing — the scenarios' required-tool
   lists predate the new tools; the same evidence was obtained through `get_daily_series` or
   `get_capacity_context`.

Excluding these two artefacts, **every scenario passes all of its remaining objective checks**
(required facts stated, required concepts present, no must-not pattern, root cause left
unconfirmed). The criteria were not changed; updating them is a decision for after your review."""


def md_list(items):
    return "\n".join(f"- {i}" for i in items) if items else "_None recorded._"


def short(obj, n=260):
    text = json.dumps(obj, ensure_ascii=False)
    return text if len(text) <= n else text[:n] + " …"


def section(d):
    s, o = d["scenario"], d["outcome"]
    r = o.get("result") or {}
    plan = o.get("evidence_plan") or {}
    prefetched = len(plan.get("executed") or [])
    lines = [f"## {s} — {d['category']}", "",
             f"**Original question (exact text submitted):** {d['question']}", "",
             f"**Date context:** viewing shift {d['date_context']}. Exact prompt sent:", "",
             "```text", d["prompt_sent"], "```", "",
             f"**Run:** {o['status']} · {len(o.get('trace') or [])} tool calls ({prefetched} pre-fetched) · "
             f"{d['duration_seconds']} s · tokens in/out "
             f"{sum(u.get('input_tokens', 0) for u in d['usage'].values()):,} / "
             f"{sum(u.get('output_tokens', 0) for u in d['usage'].values()):,} · **${d['cost_usd']:.3f}**", "",
             "---", "", "### A. Agent's original answer (verbatim, unedited)", "",
             "> Everything in section A is copied unchanged from the saved record "
             f"(`{s}.json` → `outcome.result` and `outcome.narrative`).", "",
             "**Observed facts**", md_list(r.get("observed_facts")), "",
             "**Supported patterns**", md_list(r.get("supported_patterns")), "",
             "**Hypotheses**", md_list(r.get("hypotheses")), "",
             f"**Confirmed root cause:** {r.get('confirmed_root_cause')!r}", "",
             "**Missing evidence**", md_list(r.get("missing_evidence")), "",
             "**Recommendations**", md_list(r.get("recommendations")), ""]
    if o.get("pattern_themes"):
        lines += ["**Pattern-analysis themes**",
                  md_list([f"{t['theme']} — {t['evidence_count']} requests, {t['confidence']} confidence"
                           for t in o["pattern_themes"]]), ""]
    lines += ["**Narrative (the agent's final prose answer, shown in the Technical view):**", "",
              "````markdown", (o.get("narrative") or "").strip(), "````", "",
              "---", "", "### B. Tools and evidence (from the trace)", "",
              f"Pre-fetch plan (deterministic, before the AI): {' '.join(plan.get('reasons') or [])}", "",
              "| # | Tool | Arguments | Result (excerpt; full result in the JSON) |", "|---|---|---|---|"]
    for i, step in enumerate(o.get("trace") or []):
        marker = " (pre-fetched)" if i < prefetched else ""
        lines.append(f"| {i} | `{step['tool']}`{marker} | `{short(step['args'], 140)}` | "
                     f"{short(step.get('result')).replace('|', '/')} |")
    checks = o.get("answer_checks") or []
    g = d["grade"] or {}
    nums = d["numbers"] or {}
    lines += ["", "**Automatic checks (no AI):**", "",
              f"- Answer checks shown to the manager: {len(checks)} warning(s)"
              + ("".join(f"\n  - {c['kind']}: {c['message']} — “{c['excerpt'][:160]}”" for c in checks)),
              f"- Number verification against the trace: {nums.get('summary')}",
              f"- Scenario grader: {'PASS' if g.get('passed') else 'FAIL'} (score {g.get('score')}); failed checks: "
              + (", ".join(f"*{c['check']}*" for c in g.get("checks", []) if c["verdict"] == "FAIL") or "none")
              + " — see the note on grader artefacts at the top.", "",
              "---", "", "### C. Expected findings (ground truth from the synthetic data — reviewer)", "",
              REVIEW[s]["truth"], "", "### D. Evaluation (reviewer)", "", REVIEW[s]["eval"], "",
              "### E. Issues found (reviewer)", "", REVIEW[s]["issues"], "", ""]
    return "\n".join(lines)


def main():
    data = {s: json.loads((HERE / f"{s}.json").read_text(encoding="utf-8")) for s in ORDER}
    summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
    rows = {
        "S29": ("Correct: no drop per working day", "None material; one wrong tool argument, visible self-correction"),
        "S30": ("5 of 6 planted issues; mostly accurate", "**A07 missed**; A04 per-category figures given the wrong period; \"45 login_issue requests\" (actually 40); 26 Aug cause not investigated"),
        "S16": ("Correct; one-day rate properly scoped", "None material"),
        "S03": ("Correct; **staffing cause found**", "Speculative platform hypothesis; \"4 agents left\" over-interpreted"),
        "S05": ("Correct; demand + staffing", "Unsupported \"structurally under-staffed 15:00–17:00\" recommendation"),
        "S07": ("Correct on all three parts", "\"+89%\" mislabels a share"),
    }
    head = ["# Live evaluation report — 2026-11-02", "",
            "Six scenarios run once each against the current agent (`claude-sonnet-4-6`), exactly as the app runs them "
            "(question + date context). Nothing in the agent, prompts, tools or evaluation criteria was changed.", "",
            f"**Total cost: ${summary['spent_usd']:.2f}** of a $4.75 cap (account budget $5). No retries were needed.", "",
            "**How to read this report.** Each scenario has five sections. **A** is the agent's answer, copied "
            "verbatim from the saved record. **B** is the tool trace. **C, D and E** are my ground truth, evaluation "
            "and issues — clearly marked as the reviewer's. Full records (every tool result, token usage, logs) are in "
            "`S29.json` … `S07.json` and `*.log.txt` next to this file.", "",
            "## Summary", "",
            "| Scenario | Question type | Cost | Tool calls | Verdict (reviewer) | Main issues |", "|---|---|---|---|---|---|"]
    for s in ORDER:
        d = data[s]
        head.append(f"| {s} | {d['category']} | ${d['cost_usd']:.3f} | {len(d['outcome'].get('trace') or [])} | "
                    f"{rows[s][0]} | {rows[s][1]} |")
    head += ["", "### Overall assessment (reviewer)", "",
             "- **Factual accuracy is high.** Across 1,004 numbers in the six answers, none was unsupported by the "
             "tool results; no invented agent or request IDs; every root cause left unconfirmed. Number matching "
             "cannot catch a real number attached to the wrong thing: the review found one such error in S30 "
             "(an hour's total of 45 reported as 45 login requests).",
             "- **The Phase 0 reasoning failures did not recur in these runs:** unequal periods compared per working day "
             "(S29); a one-day rate attributed to its day, not the period (S16); the staffing shortage identified "
             "(S03, S05); the broad review surfaced 5 of 6 planted issues instead of 1 (S30).",
             "- **Remaining weaknesses:** a missed trend-only agent problem (A07, S30); one scope mislabel of the "
             "kind the rules target (S30); speculative or embellished interpretations (S03, S05); occasional "
             "invalid tool arguments that did not affect the answer (S29, S16).",
             "- **Caveat:** one run per scenario. Model outputs vary between runs; these results show the agent *can* "
             "answer correctly with the current design, not that it always will. Repetitions would be needed to "
             "measure consistency.", "", ARTEFACTS, "", "---", ""]
    body = [section(data[s]) for s in ORDER]
    (HERE / "REPORT.md").write_text("\n".join(head + body), encoding="utf-8")
    print("wrote", HERE / "REPORT.md")


if __name__ == "__main__":
    main()
