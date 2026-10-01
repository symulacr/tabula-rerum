#!/usr/bin/env bash
# Tabula Rerum — demo script for the hackathon submission.
# Run this and screen-record the terminal. Everything below works with NO API key.
set -u
cd "$(dirname "$0")"

say() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

say "1. THE TEST SUITE (stdlib-only enforced; count is asserted against this file)"
python3 run.py --test 2>&1 | tail -4

say "2. START THE APP — offline, no key, no network"
python3 run.py --port 8099 2>/dev/null &
SRV=$!
sleep 3

say "3. HEALTH CHECK"
curl -s http://127.0.0.1:8099/healthz; echo

say "4. THE FINDING — regenerate it live from the data"
python3 - <<'PY'
import json, math
def load(p):
    d = json.load(open(p))
    pts = d["data"] if isinstance(d, dict) else d
    return {x["update_time"][:10]: x["value"] for x in pts}
a = load("evidence/fixtures/cmc20_historical.json")
b = load("evidence/fixtures/cmc100_historical.json")
days = sorted(set(a) & set(b))
ra = [a[d] for d in days]; rb = [b[d] for d in days]
n = len(days)
sp = [x - y for x, y in zip(ra, rb)]
mu = sum(sp) / n
sd = math.sqrt(sum((v - mu) ** 2 for v in sp) / n)
def pearson(x, y):
    mx, my = sum(x)/len(x), sum(y)/len(y)
    num = sum((p-mx)*(q-my) for p, q in zip(x, y))
    dx = math.sqrt(sum((p-mx)**2 for p in x)); dy = math.sqrt(sum((q-my)**2 for q in y))
    return num / (dx*dy)
def ac(x, k=1):
    m = sum(x)/len(x)
    return sum((x[i]-m)*(x[i-k]-m) for i in range(k, len(x))) / sum((v-m)**2 for v in x)
r1 = ac(sp)
rba = [v*100/ra[0] for v in ra]; rbb = [v*100/rb[0] for v in rb]
reb = [p - q for p, q in zip(rba, rbb)]
r2 = ac(reb)
neff = n / math.sqrt((1 + r2) / (1 - r2))
print(f"  window            {days[0]} .. {days[-1]}  (n={n})")
print(f"  r(CMC20,CMC100)   {pearson(ra, rb):.6f}   <- same asset class")
print(f"  raw spread        mean {mu:.3f} sd {sd:.4f} span {max(sp)-min(sp):.3f} ({(max(sp)-min(sp))/mu*100:.1f}% of mean)")
print(f"  rebased spread    rho1 {r2:.4f}   <- no stationary distribution, no valid null")
print(f"  n_eff             {neff:.1f}  (NOT {n})")
print("  => a z-score here is a POSITION, not a test statistic")
print("  NOTE: the RAW spread's rho1 is %.4f; the chart plots the REBASED one." % r1)
PY

say "5. THE PROVENANCE LAYER — receipts for every call"
curl -s http://127.0.0.1:8099/api/regimen | python3 -m json.tool 2>/dev/null | head -30

say "6. THE PAGE — SVG chart, table fallback, sentiment panels, composition panel"
echo "  open http://127.0.0.1:8099/ — scroll to show:"
echo "    - the Regime chart with its measured caption"
echo "    - the window control (try ?days=120) and its multiple-comparisons caveat"
echo "    - Bitcoin Fear & Greed and the Altcoin Season Index, each labelled with"
echo "      what it does and does not measure, each with its own table fallback"
echo "    - the Composition panel with the 'not market churn' caveat"
echo "    - the provenance table listing every receipt"
echo
echo "  verifying the page from the shell, so the claims above are checkable:"
curl -s http://127.0.0.1:8099/ | grep -oE "(Bitcoin Fear &amp; Greed|Altcoin Season Index \(90d\)|outperformed BTC|Bitcoin-only|multiple-comparisons|name=\"days\")" | sort -u | sed 's/^/    /'

say "7. A REAL KEYLESS API CALL (no key header, no credentials)"
curl -s "https://pro-api.coinmarketcap.com/public-api/v3/index/cmc20-latest" | head -c 200; echo
echo "  --- and the failure mode we classify: an unrouted path ---"
curl -s "https://pro-api.coinmarketcap.com/public-api/v9/totally/bogus" ; echo
echo "  NOTE: HTTP 200 + error_code 500 + 'system is busy'."
echo "        This is the SIGNATURE OF A TYPO, not a transient. We never retry it."

kill $SRV 2>/dev/null
say "DONE — no API key was used at any point."
