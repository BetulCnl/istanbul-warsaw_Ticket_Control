"""Her gün çalışır: tarih aralığındaki tüm uçuşların fiyatını çekip data/history.json'a ekler.

Kullanım:
  python scripts/fetch.py          # gerçek fiyatları çek
  python scripts/fetch.py --demo   # sahte örnek geçmiş üret (arayüzü denemek için)
"""
import json, random, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
HIST = ROOT / "data" / "history.json"
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")


def daterange(r):
    # geçmiş günler atlanır: tarih geçince o gün artık taranmaz
    d, end = max(date.fromisoformat(r["from"]), date.today()), date.fromisoformat(r["to"])
    while d <= end:
        yield d.isoformat()
        d += timedelta(days=1)


def queries():
    """(yön, tarih, kalkış, varış) listesi. yön: out = Varşova->İstanbul, ret = İstanbul->Varşova"""
    for d in daterange(CFG["outbound_dates"]):
        for a in CFG["origins"]:
            for b in CFG["destinations"]:
                yield ("out", d, a, b)
    for d in daterange(CFG["return_dates"]):
        for a in CFG["destinations"]:
            for b in CFG["origins"]:
                yield ("ret", d, a, b)


def parse_all(html):
    """Google sonuçları iki bölümde verir: [2] = 'Top flights', [3] = 'Other flights'.
    fast-flights yalnızca [3]'ü okuyor, bu yüzden bölümleri kendimiz birleştiriyoruz."""
    from selectolax.lexbor import LexborHTMLParser
    script = LexborHTMLParser(html).css_first(r"script.ds\:1")
    if script is None:
        raise RuntimeError("Google sonuç sayfası alınamadı (engel/onay sayfası olabilir)")
    data = script.text().split("data:", 1)[1].rsplit(",", 1)[0]
    if data.endswith("errorHasStatus: true"):
        return []
    payload = json.loads(data)
    out = []
    for section in (2, 3):
        block = payload[section] if len(payload) > section else None
        if not block or not block[0]:
            continue
        for k in block[0]:
            flight, price = k[0], k[1][0][1]
            legs = flight[2]
            t = legs[0][8] or []
            t = [*t, None, None]
            out.append({"price": price, "airlines": flight[1], "stops": len(legs) - 1,
                        "dep": "%02d:%02d" % (t[0] or 0, t[1] or 0)})
    return out


def fetch_offers(d, a, b):
    from fast_flights import FlightQuery, Passengers, create_query, fetch_flights_html
    q = create_query(
        flights=[FlightQuery(date=d, from_airport=a, to_airport=b, max_stops=CFG.get("max_stops"),
                             airlines=list(CFG["airlines"].values()) or None)],
        seat="economy", trip="one-way", passengers=Passengers(adults=1),
        currency=CFG["currency"],
    )
    last = None
    for attempt in range(3):
        try:
            res = parse_all(fetch_flights_html(q))
            break
        except Exception as e:  # ağ hatası / engel
            last = e
            time.sleep(3 * (attempt + 1))
    else:
        print(f"  ! {a}->{b} {d}: {last}", file=sys.stderr)
        return None
    allowed = set(CFG["airlines"])  # yalnızca bu havayolları (aktarmalıda tüm bacaklar)
    best = {}
    for r in res:
        if allowed and not set(r["airlines"]) <= allowed:
            continue
        airlines = " + ".join(r["airlines"])
        key = (airlines, r["stops"])
        if key not in best or r["price"] < best[key][4]:
            best[key] = [None, None, None, None, r["price"], airlines, r["stops"], r["dep"]]
    return sorted(best.values(), key=lambda o: o[4])[: CFG["keep_offers_per_query"]]


def load():
    return json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else {"currency": CFG["currency"], "snapshots": []}


def save(h):
    HIST.parent.mkdir(exist_ok=True)
    HIST.write_text(json.dumps(h, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def totals(offers):
    """En ucuz gidiş-dönüş çifti (dönüş gidişten sonraki bir günde). (gidiş, dönüş) fiyatı döner."""
    def per_day(d):
        m = {}
        for o in offers:
            if o[0] == d and (o[1] not in m or o[4] < m[o[1]]):
                m[o[1]] = o[4]
        return m
    outs, rets = per_day("out"), per_day("ret")
    lo, hi = CFG.get("min_stay_days", 1), CFG.get("max_stay_days", 999)
    gap = lambda a, b: (date.fromisoformat(b) - date.fromisoformat(a)).days
    pairs = [(po, pr) for do, po in outs.items() for dr, pr in rets.items() if lo <= gap(do, dr) <= hi]
    return min(pairs, key=sum) if pairs else (None, None)


def run_real():
    today = date.today().isoformat()
    offers, failed, total = [], 0, 0
    for (direction, d, a, b) in queries():
        total += 1
        res = fetch_offers(d, a, b)
        if res is None:
            failed += 1
        else:
            for o in res:
                o[0], o[1], o[2], o[3] = direction, d, a, b
                offers.append(o)
        time.sleep(CFG["pause_seconds"])
    if not offers:
        sys.exit("Hiç fiyat alınamadı (Google engellemiş olabilir). Geçmişe dokunulmadı.")
    if failed > total * 0.5:
        print(f"Uyarı: {failed}/{total} sorgu başarısız.", file=sys.stderr)
    h = load()
    h["currency"] = CFG["currency"]
    h["snapshots"] = [s for s in h["snapshots"] if s["d"] != today]
    h["snapshots"].append({"d": today, "o": offers})
    save(h)
    o, r = totals(offers)
    if o is not None and r is not None:
        print(f"Bugünün en ucuz gidiş-dönüşü: {o} + {r} = {o + r} {CFG['currency']}")
    print(f"Tamam: {len(offers)} teklif kaydedildi, {failed} sorgu başarısız.")


def run_demo():
    random.seed(7)
    airlines = [("Turkish Airlines", 0, 1.0), ("LOT", 0, 1.05), ("Pegasus", 0, 0.75),
                ("Pegasus", 1, 0.7), ("LOT + Turkish Airlines", 1, 0.85)]
    h = {"currency": CFG["currency"], "snapshots": []}
    days = 30
    for i in range(days):
        day = (date.today() - timedelta(days=days - 1 - i)).isoformat()
        offers = []
        for (direction, d, a, b) in queries():
            weekend = date.fromisoformat(d).weekday() in (4, 6)
            base = 95 + (35 if weekend else 0) + (days - i) * 0.8 + random.uniform(-15, 15)
            for name, stops, k in random.sample(airlines, 3):
                offers.append([direction, d, a, b, round(base * k + random.uniform(-8, 8)),
                               name, stops, "%02d:%02d" % (random.choice([6, 9, 13, 17, 21]), random.choice([0, 15, 30, 45]))])
        h["snapshots"].append({"d": day, "o": offers})
    save(h)
    print(f"Demo verisi yazıldı: {days} günlük geçmiş.")


if __name__ == "__main__":
    run_demo() if "--demo" in sys.argv else run_real()
