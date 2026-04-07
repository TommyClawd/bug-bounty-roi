# Bug Bounty ROI Scoring Methodology — V2

## Philosophy
The score answers one question: **"If I spend 20 hours on this program, what's my expected return?"**

This is NOT a "best program" ranking. It's a researcher-ROI ranking. A program can be great for the company and terrible for researchers (high payout headline, 2000 participants = everyone gets duped).

## V2 Formula

```
ROI_Score = (Expected_Payout × Response_Quality × Activity_Health) / Competition_Pressure
```

### Components

**Expected Payout (EP)**
- `avg_bounty_upper` — the upper end of the average range
- If no average available, use `(min_bounty + max_bounty) / 4` as conservative estimate
- Weight: this is the numerator. Higher payout = higher ROI.

**Response Quality (RQ)** — range 0.0 to 1.2
- `response_efficiency_percentage / 100` — base quality
- Bonus: if efficiency > 95%, add 0.1 (programs that respond fast are MORE valuable because you iterate faster)
- Programs with 0% or unknown efficiency get 0.5 (neutral)

**Activity Health (AH)** — range 0.5 to 2.0
- `resolved_report_count / max(1, reports_received_last_90_days × 4)`
- This measures "what fraction of the expected annual reports have been resolved"
- A healthy program resolves most of what comes in
- A program drowning in reports (high 90d, low resolved) is backed up = bad for researchers
- Clamped to [0.5, 2.0]

**Competition Pressure (CP)** — the key differentiator
- `sqrt(max(1, participants_count))`
- Square root because competition isn't linear — going from 10 to 50 participants is much worse than going from 500 to 540
- This is the denominator. More competition = lower ROI.

### Final Score
```python
EP = avg_bounty_upper or (min_bounty + max_bounty) / 4
RQ = min(1.2, max(0.5, efficiency/100 + (0.1 if efficiency > 95 else 0)))
AH = min(2.0, max(0.5, resolved / max(1, recent_90d * 4)))
CP = sqrt(max(1, participants))

ROI = (EP * RQ * AH) / CP
```

### What this rewards
- High average payouts ✓
- Fast, responsive triage teams ✓
- Active but not overwhelmed programs ✓
- Low competition ✓✓ (this is the biggest differentiator)

### What this penalizes
- Headline max bounties with low averages ✓
- Slow/unresponsive programs ✓
- Programs drowning in submissions ✓
- Famous programs with 1000+ researchers ✓

## Validation
The V1 formula produced rankings that matched community intuition:
- Nintendo, Linktree, Whatnot ranked high (community favorites)
- Coinbase, Meta, X ranked low (community frustration targets)

V2 should maintain this while being more defensible methodologically.

## Limitations
- No duplicate rate data (not publicly available)
- No payout-per-severity breakdown
- Participant count is all-time, not active researchers
- Bugcrowd doesn't expose participant counts at all
- Self-selection bias: researchers choose programs, so popular programs may have higher duplicate rates than the score implies
