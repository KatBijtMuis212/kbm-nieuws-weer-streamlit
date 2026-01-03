# KbM Nieuws + Weer (Streamlit)

Dit is een **online** dashboard in NU-achtige stijl:
- Nieuws via jouw RSS-lijst (NOS / NU.nl / AD / RTV Midden Holland)
- Samenvatting uit RSS, en optioneel “beter” door artikeltekst op te halen (best effort)
- Plaatjes: via RSS `media:content`, `enclosures` of als fallback `og:image`
- Weer: Open‑Meteo (gratis, geen API key) + RainViewer radar

## Lokaal draaien
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Online (Streamlit Community Cloud)
1. Zet deze map in een GitHub repo.
2. Ga naar Streamlit Cloud en deploy `app.py`.
3. (Optioneel privé) Voeg in **Secrets** toe:
   ```toml
   APP_PASSWORD = "jouwWachtwoord"
   ```
   Dan vraagt de app om een wachtwoord en is het “alleen voor jou”.

## Opmerking over “realtime”
Feeds worden met een cache van ~2 minuten opgehaald (bewust, anders ga je onbedoeld te agressief poll-en).

## Paywalls
Sommige artikelen (met name AD/RTL) zijn (deels) paywalled. RSS werkt meestal wel, maar “artikel ophalen” kan daar beperkt zijn.
