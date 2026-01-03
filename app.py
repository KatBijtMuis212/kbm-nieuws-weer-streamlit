import os, re, time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import feedparser
import streamlit as st

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

APP_TITLE = "KbM Nieuws • Online"
BR6_BLUE = "#214c6e"
UA = "KbMStreamlitNews/1.0 (+Bas)"

# -----------------------------
# Feeds (exact zoals jij stuurde)
# -----------------------------
FEEDS = {
    "NOS • Binnenland": "https://feeds.nos.nl/nosnieuwsbinnenland",
    "NOS • Buitenland": "https://feeds.nos.nl/nosnieuwsbuitenland",
    "NOS • Politiek": "https://feeds.nos.nl/nosnieuwspolitiek",
    "NOS • Economie": "https://feeds.nos.nl/nosnieuwseconomie",
    "NOS • Opmerkelijk": "https://feeds.nos.nl/nosnieuwsopmerkelijk",
    "NOS • Koningshuis": "https://feeds.nos.nl/nosnieuwskoningshuis",
    "NOS • Cultuur & Media": "https://feeds.nos.nl/nosnieuwscultuurenmedia",
    "NOS • Tech": "https://feeds.nos.nl/nosnieuwstech",
    "NOS • Sport": "https://feeds.nos.nl/nossportalgemeen",
    "NOS • Formule 1": "https://feeds.nos.nl/nossportformule1",
    "NOS • OP3": "https://feeds.nos.nl/nosop3",
    "NU.nl • Home": "https://www.nu.nl/rss",
    "NU.nl • Algemeen": "https://www.nu.nl/rss/Algemeen",
    "NU.nl • Economie": "https://www.nu.nl/rss/Economie",
    "NU.nl • Sport": "https://www.nu.nl/rss/Sport",
    "NU.nl • Entertainment": "https://www.nu.nl/rss/entertainment",
    "NU.nl • Achterklap": "https://www.nu.nl/rss/Achterklap",
    "NU.nl • Opmerkelijk": "https://www.nu.nl/rss/Opmerkelijk",
    "NU.nl • Slimmer Leven": "https://www.nu.nl/rss/slimmer-leven",
    "NU.nl • Tech/Wetenschap": "https://www.nu.nl/rss/tech-wetenschap",
    "NU.nl • Goed Nieuws": "https://www.nu.nl/rss/goed-nieuws",
    "AD • Home": "https://www.ad.nl/home/rss.xml",
    "AD • Geld": "https://www.ad.nl/geld/rss.xml",
    "AD • Sterren": "https://www.ad.nl/sterren/rss.xml",
    "AD • Film": "https://www.ad.nl/film/rss.xml",
    "AD • Songfestival": "https://www.ad.nl/songfestival/rss.xml",
    "AD • Muziek": "https://www.ad.nl/muziek/rss.xml",
    "AD • Showbytes": "https://www.ad.nl/showbytes/rss.xml",
    "AD • Royalty": "https://www.ad.nl/royalty/rss.xml",
    "AD • Cultuur": "https://www.ad.nl/cultuur/rss.xml",
    "AD • Series": "https://www.ad.nl/series/rss.xml",
    "RTV Midden Holland": "https://rtvmiddenholland.nl/feed/",
}

# -----------------------------
# Weer (Open‑Meteo + RainViewer)
# -----------------------------
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"

DEFAULT_CITY = "Huizen"

# -----------------------------
# “Alleen voor mij” (simpel slot)
# Zet in Streamlit secrets:
#   APP_PASSWORD = "jouwWachtwoord"
# -----------------------------
def require_login():
    pw = st.secrets.get("APP_PASSWORD", "").strip()
    if not pw:
        return  # geen wachtwoord ingesteld → publiek
    if "kbm_ok" not in st.session_state:
        st.session_state.kbm_ok = False
    if st.session_state.kbm_ok:
        return
    st.markdown("### 🔒 Privé modus")
    inp = st.text_input("Wachtwoord", type="password")
    if st.button("Inloggen", use_container_width=True):
        st.session_state.kbm_ok = (inp == pw)
    if not st.session_state.kbm_ok:
        st.stop()

# -----------------------------
# Styling (NU-achtig + BR6-blauw)
# -----------------------------
st.set_page_config(page_title=APP_TITLE, page_icon="🗞️", layout="wide")

st.markdown(f"""
<style>
:root {{
  --kbm-blue: {BR6_BLUE};
  --kbm-bg: #f4f7fb;
  --kbm-card: #ffffff;
  --kbm-muted: #6b7280;
  --kbm-border: rgba(0,0,0,.08);
}}
.stApp {{
  background: radial-gradient(1200px 600px at 10% 0%, #cfe7ff 0%, var(--kbm-bg) 55%, #eef4ff 100%);
}}
.kbm-hero {{
  border: 1px solid var(--kbm-border);
  background: rgba(255,255,255,.65);
  backdrop-filter: blur(8px);
  border-radius: 18px;
  padding: 18px 18px 10px 18px;
  margin-bottom: 12px;
}}
.kbm-title {{ font-size: 28px; font-weight: 900; margin: 0; }}
.kbm-sub {{ color: var(--kbm-muted); margin-top: 4px; }}
.kbm-tag {{
  display:inline-block;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(33,76,110,.10);
  color: var(--kbm-blue);
  font-weight: 900;
  border: 1px solid rgba(33,76,110,.15);
}}
.kbm-card {{
  border: 1px solid var(--kbm-border);
  background: var(--kbm-card);
  border-radius: 18px;
  padding: 14px;
}}
.kbm-meta {{ color: var(--kbm-muted); font-size: 12px; }}
.kbm-img {{
  width: 100%;
  max-height: 220px;
  object-fit: cover;
  border-radius: 14px;
  border: 1px solid var(--kbm-border);
}}
/* input rounding */
div[data-baseweb="input"] input, div[data-baseweb="select"] > div {{
  border-radius: 12px !important;
}}
/* hide streamlit bits */
#MainMenu {{visibility:hidden;}}
footer {{visibility:hidden;}}
</style>
""", unsafe_allow_html=True)

require_login()

# -----------------------------
# Helpers
# -----------------------------
def safe_text(x: str) -> str:
    return re.sub(r"\s+", " ", (x or "")).strip()

def host(u: str) -> str:
    try:
        return urlparse(u).netloc.replace("www.", "")
    except Exception:
        return ""

def entry_dt(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        v = getattr(entry, key, None)
        if v:
            try:
                return datetime.fromtimestamp(time.mktime(v), tz=timezone.utc)
            except Exception:
                pass
    return None

def strip_html(html: str) -> str:
    if not html:
        return ""
    if BeautifulSoup:
        try:
            return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        except Exception:
            pass
    return re.sub(r"<[^>]+>", " ", html)

def image_from_entry(entry) -> str | None:
    if "media_content" in entry and entry.media_content:
        u = entry.media_content[0].get("url")
        if u: return u
    if "media_thumbnail" in entry and entry.media_thumbnail:
        u = entry.media_thumbnail[0].get("url")
        if u: return u
    if "enclosures" in entry and entry.enclosures:
        for e in entry.enclosures:
            if e.get("type","").startswith("image") and e.get("href"):
                return e["href"]
    # sometimes in summary HTML
    summ = entry.get("summary","") or entry.get("description","")
    if summ and BeautifulSoup:
        try:
            soup = BeautifulSoup(summ, "html.parser")
            img = soup.find("img")
            if img and img.get("src"):
                return img["src"]
        except Exception:
            pass
    return None

@st.cache_data(ttl=120, show_spinner=False)
def fetch_feed(url: str):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return feedparser.parse(r.text)

@st.cache_data(ttl=600, show_spinner=False)
def og_image(url: str) -> str | None:
    if not BeautifulSoup:
        return None
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        if not r.ok:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        m = soup.find("meta", property="og:image")
        if m and m.get("content"):
            return m["content"]
    except Exception:
        return None
    return None

@st.cache_data(ttl=1800, show_spinner=False)
def readable_text(url: str) -> str | None:
    # Snelle “goed genoeg” extractie; werkt bij veel sites, maar paywalls blijven paywalls 😄
    if not BeautifulSoup:
        return None
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        if not r.ok:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script","style","noscript"]):
            t.decompose()
        ps = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        ps = [safe_text(p) for p in ps if safe_text(p)]
        txt = "\n".join(ps[:40])
        return txt if len(txt) > 400 else None
    except Exception:
        return None

def quick_summary(entry, force_fetch: bool) -> str:
    # 1) RSS summary
    s = strip_html(entry.get("summary","") or entry.get("description",""))
    s = safe_text(s)
    if len(s) >= 140:
        return s[:420].rstrip() + ("…" if len(s) > 420 else "")
    # 2) fetch article text
    if force_fetch:
        txt = readable_text(entry.get("link",""))
        if txt:
            # take first 2-3 sentences
            parts = re.split(r"(?<=[.!?])\s+", safe_text(txt))
            parts = [p.strip() for p in parts if p.strip()]
            out = " ".join(parts[:3])
            return out[:520].rstrip() + ("…" if len(out) > 520 else "")
    return s

# -----------------------------
# Weather helpers
# -----------------------------
@st.cache_data(ttl=300, show_spinner=False)
def geocode_city(name: str):
    params = {"name": name, "count": 5, "language": "nl", "format": "json"}
    r = requests.get(OPEN_METEO_GEOCODE, params=params, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=300, show_spinner=False)
def forecast(lat: float, lon: float):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,precipitation,precipitation_probability,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "Europe/Amsterdam",
    }
    r = requests.get(OPEN_METEO_FORECAST, params=params, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return r.json()

def wx_emoji(code: int) -> str:
    c = int(code or 0)
    if c == 0: return "☀️"
    if c in (1,2): return "⛅"
    if c == 3: return "☁️"
    if c in (45,48): return "🌫️"
    if c in (51,53,55,56,57): return "🌦️"
    if c in (61,63,65,66,67): return "🌧️"
    if c in (71,73,75,77,85,86): return "❄️"
    if c in (80,81,82): return "🌧️"
    if c in (95,96,99): return "⛈️"
    return "🌤️"

# -----------------------------
# Header
# -----------------------------
st.markdown(f"""
<div class="kbm-hero">
  <div class="kbm-title">Weer & Nieuws</div>
  <div class="kbm-sub">Realtime-ish zonder API-key-drama. Nieuws via RSS, weer via Open‑Meteo + RainViewer. Klassiek nieuwsgevoel, moderne knoppen 😄</div>
</div>
""", unsafe_allow_html=True)

tab_news, tab_weather = st.tabs(["🗞️ Nieuws", "🌧️ Weer"])

# -----------------------------
# Nieuws tab
# -----------------------------
with tab_news:
    left, right = st.columns([1.45, 0.55], gap="large")

    with right:
        st.markdown('<div class="kbm-card">', unsafe_allow_html=True)
        st.markdown("#### Bronnen")
        default_sel = [k for k in FEEDS.keys() if k.startswith("NOS") or k.startswith("NU.nl") or k.startswith("AD") or k.startswith("RTV")]
        selected = st.multiselect("Kies feeds", list(FEEDS.keys()), default=default_sel)
        query = st.text_input("Zoekterm (optioneel)", placeholder="bijv. Huizen, politiek, muziek…")
        max_items = st.slider("Max items totaal", 20, 250, 80, 10)
        fetch_full = st.toggle("Betere samenvatting (artikel ophalen)", value=True, help="Haalt soms tekst op van de site voor een nettere samenvatting. Kan bij paywalls beperkt zijn.")
        st.markdown("---")
        colA, colB = st.columns(2)
        with colA:
            refresh = st.button("🔁 Ververs nu", use_container_width=True)
        with colB:
            st.caption("Cache: ~2 min. (bewust, anders ga je DDOS'en per ongeluk 🤝)")
        st.markdown('</div>', unsafe_allow_html=True)

    if refresh:
        st.cache_data.clear()

    # collect
    items = []
    per_feed_stats = []

    for label in selected:
        url = FEEDS[label]
        try:
            d = fetch_feed(url)
            entries = d.entries or []
            kept = 0
            for e in entries:
                title = safe_text(e.get("title",""))
                link = e.get("link","")
                if not title or not link:
                    continue
                if query:
                    q = query.lower()
                    hay = (title + " " + safe_text(strip_html(e.get("summary","") or e.get("description","")))).lower()
                    if q not in hay:
                        continue
                img = image_from_entry(e) or og_image(link)
                dt = entry_dt(e)
                summ = quick_summary(e, force_fetch=fetch_full)
                items.append({
                    "source": label,
                    "title": title,
                    "link": link,
                    "img": img,
                    "dt": dt,
                    "summary": summ,
                })
                kept += 1
            per_feed_stats.append((label, len(entries), kept))
        except Exception as ex:
            per_feed_stats.append((label, 0, 0))
            items.append({
                "source": label,
                "title": f"[FOUT] Feed niet bereikbaar: {label}",
                "link": url,
                "img": None,
                "dt": None,
                "summary": f"Kon feed niet ophalen ({type(ex).__name__}).",
            })

    # sort by dt if available, else keep
    items.sort(key=lambda x: x["dt"] or datetime(1970,1,1,tzinfo=timezone.utc), reverse=True)
    items = items[:max_items]

    with left:
        st.markdown('<div class="kbm-card">', unsafe_allow_html=True)
        st.markdown("#### Binnengehaald")
        if per_feed_stats:
            st.caption("Per bron: opgehaald vs. relevant na filter")
            lines = []
            for (lab, total, kept) in per_feed_stats:
                lines.append(f"• **{lab}** — {kept}/{total}")
            st.markdown("\n".join(lines))
        st.markdown('</div>', unsafe_allow_html=True)

        if not items:
            st.info("Geen resultaten. Tip: kies meer feeds of haal de zoekterm leeg.")
        else:
            for it in items:
                dt_txt = ""
                if it["dt"]:
                    # show in NL time
                    dt_txt = it["dt"].astimezone().strftime("%d-%m %H:%M")
                st.markdown('<div class="kbm-card" style="margin-top:12px">', unsafe_allow_html=True)
                st.markdown(f"<span class='kbm-tag'>{it['source']}</span>", unsafe_allow_html=True)
                st.markdown(f"### [{it['title']}]({it['link']})")
                st.markdown(f"<div class='kbm-meta'>{host(it['link'])}{' • ' + dt_txt if dt_txt else ''}</div>", unsafe_allow_html=True)
                if it["img"]:
                    st.image(it["img"], use_container_width=True)
                if it["summary"]:
                    st.write(it["summary"])
                st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Weer tab
# -----------------------------
with tab_weather:
    st.markdown('<div class="kbm-card">', unsafe_allow_html=True)
    topA, topB, topC = st.columns([1.2, 0.9, 0.9])
    with topA:
        city = st.text_input("Zoek plaats", value=st.session_state.get("kbm_city", DEFAULT_CITY), placeholder="bijv. Huizen, Gouda…")
    with topB:
        st.write("")
        st.write("")
        use_city = st.button("Zoek", use_container_width=True)
    with topC:
        st.write("")
        st.write("")
        if st.button("Gebruik Huizen (snel)", use_container_width=True):
            city = DEFAULT_CITY
            use_city = True
    st.markdown('</div>', unsafe_allow_html=True)

    if use_city or "kbm_city" not in st.session_state:
        st.session_state.kbm_city = city

    # resolve city → lat/lon
    try:
        g = geocode_city(st.session_state.kbm_city)
        results = g.get("results") or []
        if not results:
            st.warning("Plaats niet gevonden. Probeer iets algemener.")
            st.stop()
        # take first
        place = results[0]
        lat, lon = float(place["latitude"]), float(place["longitude"])
        place_name = f"{place.get('name','')} ({place.get('country_code','')})"
    except Exception as ex:
        st.error(f"Geocoding faalde: {type(ex).__name__}")
        st.stop()

    # fetch forecast
    try:
        fx = forecast(lat, lon)
    except Exception as ex:
        st.error(f"Open‑Meteo faalde: {type(ex).__name__}")
        st.stop()

    cur = fx.get("current", {})
    temp = cur.get("temperature_2m")
    app = cur.get("apparent_temperature")
    code = cur.get("weather_code")
    wind = cur.get("wind_speed_10m")
    pr = cur.get("precipitation")

    colL, colR = st.columns([1.45, 0.55], gap="large")

    # Left: Radar/Kaart/Weerbericht tabs
    with colL:
        wx_tab_radar, wx_tab_maps, wx_tab_text = st.tabs(["Radar", "Weerkaart", "Weerbericht"])

        with wx_tab_radar:
            st.markdown('<div class="kbm-card">', unsafe_allow_html=True)
            st.markdown(f"#### Buienradar (RainViewer) • {place_name}")
            st.caption("Tip: zoom in/uit in de kaart. RainViewer is openbaar en werkt meestal verrassend goed.")
            # RainViewer embed: Leaflet viewer
            rv_url = f"https://www.rainviewer.com/map.html?loc={lat:.4f},{lon:.4f},9&oFa=0&oC=0&oU=0&oCS=1&oF=0&oAP=0&c=3&o=83&lm=1&layer=radar&sm=1"
            st.components.v1.iframe(rv_url, height=520, scrolling=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with wx_tab_maps:
            st.markdown('<div class="kbm-card">', unsafe_allow_html=True)
            st.markdown("#### Weerkaart (KNMI) — snel overzicht")
            st.caption("Dit is geen officiële KNMI-API: we tonen de publieke kaarten (als ze wijzigen, pas je de URL aan in code).")
            # Public KNMI kaarten (vaak stabiel): we use known png endpoints as placeholders
            maps = {
                "Vandaag": "https://cdn.knmi.nl/knmi/map/page/weer/waarschuwingen_verwachtingen/weerkaarten/actueel-weerbeeld.png",
                "Morgen": "https://cdn.knmi.nl/knmi/map/page/weer/waarschuwingen_verwachtingen/weerkaarten/verwachting-1.png",
                "Morgen nacht": "https://cdn.knmi.nl/knmi/map/page/weer/waarschuwingen_verwachtingen/weerkaarten/verwachting-1-nacht.png",
            }
            pick = st.selectbox("Kaart", list(maps.keys()))
            st.image(maps[pick], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with wx_tab_text:
            st.markdown('<div class="kbm-card">', unsafe_allow_html=True)
            st.markdown("#### Komende 6 uur")
            hourly = fx.get("hourly", {})
            times = hourly.get("time", [])[:6]
            prmm  = hourly.get("precipitation", [])[:6]
            prob  = hourly.get("precipitation_probability", [])[:6]
            t2m   = hourly.get("temperature_2m", [])[:6]
            rows = []
            for i in range(min(6, len(times))):
                try:
                    hh = times[i][11:16]
                except Exception:
                    hh = str(i)
                rows.append({
                    "Uur": hh,
                    "Temp (°C)": t2m[i] if i < len(t2m) else None,
                    "Neerslag (mm)": prmm[i] if i < len(prmm) else None,
                    "Kans (%)": prob[i] if i < len(prob) else None,
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.markdown("---")
            st.markdown("#### WEER ALARM (simpel)")
            alarm = None
            # simpele logica
            if max([p or 0 for p in (prob[:6] or [0])]) >= 80:
                alarm = "Veel kans op regen in de komende uren."
            if max([mm or 0 for mm in (prmm[:6] or [0])]) >= 2.5:
                alarm = "Flinke buien mogelijk (mm/uur)."
            if (wind or 0) >= 15:
                alarm = "Veel wind — mogelijk onrustig weer."
            st.write(alarm or "—")
            st.markdown('</div>', unsafe_allow_html=True)

    with colR:
        st.markdown('<div class="kbm-card">', unsafe_allow_html=True)
        st.markdown("#### Nu")
        st.markdown(f"### {wx_emoji(code)} {temp if temp is not None else '—'}°C")
        st.markdown(f"<div class='kbm-meta'>Gevoel: {app if app is not None else '—'}°C • Wind: {wind if wind is not None else '—'} km/u • Neerslag: {pr if pr is not None else '—'} mm</div>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("#### Vandaag / Morgen")
        daily = fx.get("daily", {})
        dtime = daily.get("time", [])[:2]
        tmax  = daily.get("temperature_2m_max", [])[:2]
        tmin  = daily.get("temperature_2m_min", [])[:2]
        dcode = daily.get("weather_code", [])[:2]
        dpr   = daily.get("precipitation_sum", [])[:2]
        for i in range(min(2, len(dtime))):
            label = "Vandaag" if i == 0 else "Morgen"
            st.markdown(f"**{label}** — {wx_emoji(dcode[i] if i < len(dcode) else 0)} {tmin[i] if i < len(tmin) else '—'}° / {tmax[i] if i < len(tmax) else '—'}° • neerslag {dpr[i] if i < len(dpr) else '—'} mm")
        st.markdown("---")
        st.caption("Open‑Meteo data, RainViewer radar. Dit is “realtime-ish”: elke paar minuten bijgewerkt.")
        st.markdown('</div>', unsafe_allow_html=True)
