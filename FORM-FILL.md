# BUIDL FORM — copy/paste each field

Repo: **https://github.com/symulacr/tabula-rerum**
Logo: **/home/eya/logo/logo.png** (480×480 PNG, 26 KB)

---

## BUIDL (project) name

```
Tabula Rerum
```

## Vision — Describe the problem which this project solves

```
Every crypto dashboard tells you a story about the market. Very few check whether the story is
statistically defensible — and the CoinMarketCap API makes the temptation unusually strong.

CMC20 and CMC100 exist to tell two different stories: concentrated leadership versus broad
participation. The obvious product is a "regime spread" chart. We built it, then measured
whether the spread supports the story — and it does not. The two indices correlate at
r = 0.999902. They are the same asset class. Their difference has lag-1 autocorrelation
0.947, which is a unit root: there is no stationary distribution behind the spread, so it has
no equilibrium to deviate from and no valid null distribution. A 70-day window has an effective
sample size of 6, not 70. Yet dashboards report "the spread is 2 sigma from normal" as though
that were a finding.

The problem this solves is not a missing chart. It is a missing check. A market dashboard that
prints a number without recording how it got that number cannot be audited, cannot be corrected,
and cannot be trusted when the two claims it rests on turn out to be the same claim.

Tabula Rerum adds that check. It runs entirely on keyless public API access, and every figure it
displays is measured at render time rather than copied from a document. Every fetch emits a
receipt recording the endpoint, parameters, auth mode, HTTP status, CoinMarketCap error code,
credit count, latency, and a SHA-256 digest. A number without a receipt is treated as a defect.
The app also refuses to fabricate smoothness: forward-fill is prohibited because manufacturing
zero returns would understate volatility and inflate every z-score, which would fabricate the
very finding it claims to report.

The result is a market board that reports what kind of market an index is describing, states
the confidence honestly, and shows you the receipt for each figure. It also documents where the
API itself gets in the way — including an unrouted path that returns HTTP 200 with a "system is
busy" error, which is a typo wearing a retry loop's clothes.
```

## Category

```
Data and Visualisation
```

## Links

| Field | Value |
|---|---|
| **GitHub/Gitlab/Bitbucket** * | `https://github.com/symulacr/tabula-rerum` |
| **Project website** (optional) | leave blank, or `https://github.com/symulacr/tabula-rerum#run-it` |
| **Demo video** * | see below — **required** |

### Demo video — three options, pick one

**Option A — record it yourself (fastest, 2 min)**
```bash
cd /home/eya/tabula-rerum
bash demo.sh
```
Then screen-record that window. It runs offline, needs no key, and narrates itself. Upload to
YouTube (unlisted is fine), paste the link.

**Option B — I record it for you.** `ffmpeg` and Chrome are both installed. Say the word and I
will capture the terminal session and the running app into an MP4 in a couple of minutes.

**Option C — upload is blocked.** If you cannot upload anywhere in time, put the runnable
instructions in the project description and link the repo. This is the one required field I
cannot satisfy for you.

## Social links (at least one)

| # | URL |
|---|---|
| 1 | *your X/Twitter post URL — must include `#BuildwithCMC`* |
| 2 | `https://github.com/symulacr/tabula-rerum` |
| 3 | `https://github.com/symulacr/tabula-rerum/issues` |

> The X post is required by the event rules: *"Make a X/Twitter post, with a link to your
> Dorahacks submission, demo video, and the hashtag #BuildwithCMC."* Post it, then come back and
> paste the URL here. If you would rather not post, the GitHub URL alone satisfies the form.

---

## X post — post this now, then paste the URL above

```
We built a CoinMarketCap dashboard that told us not to believe its own headline.

CMC20 and CMC100 are supposed to tell two stories: concentrated leadership vs broad
participation. So we built the regime-spread chart, then checked whether the spread
actually supports the story.

It doesn't. r = 0.999902 — they're the same asset class. The difference has lag-1
autocorrelation 0.947, a unit root. No stationary distribution, so no equilibrium to
deviate from, so no valid null. A 70-day window has an effective sample size of 6, not 70.

So we stopped drawing the chart everyone draws. We report percentage points, percentile
rank and n_eff instead. Every number is measured at render time, and every fetch ships a
receipt: endpoint, params, auth mode, error code, credit count, latency, SHA-256.

Also: your unrouted paths return HTTP 200 + error_code 500 + "The system is busy" — a
typo wearing a retry loop's clothes. We classify it as UNROUTED and never retry it.

Python 3.12, standard library only. No npm, no build step, no third-party runtime dep.
Runs with no API key at all.

[submission link] [demo link] #BuildwithCMC
```

---

## Short description (if the form has a one-line/elevator field)

```
A stdlib-only CoinMarketCap workspace that measures whether a market claim is
statistically defensible — and ships a receipt behind every number.
```

## Team

Add yourself as the sole member. The form asks for name and any social handle; there is no
co-founder to list.

## Contact

Use whichever email you want judged correspondence to reach. Nothing in the repo contains an
email address, and the commit history uses `tabula-rerum@users.noreply.github.com` so your real
address is not exposed.
