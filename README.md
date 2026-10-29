readme_content = """# 🐏 Interaktivt Flettingsdashbord for Sauekontrollen

Dette er en interaktiv Streamlit-applikasjon utviklet for sauebønder som ønsker å analysere tilvekst, avlsindekser og slakteresultater på en enkel og visuell måte. Ved å flette sammen vektrapporter og besetningslister, gir appen deg full oversikt over hvilke lam som utmerker seg som fremtidige livdyr, og hvem som trenger ekstra oppfølging.

## 🚀 Hovedfunksjoner
* **Automatisk Fletting:** Kobler sammen veiedata fra én rapport med rase, avlsindekser, utmeldingsårsaker og slakteoppgjør fra en annen.
* **Livdyrkandidater (🌟):** Filtrerer automatisk ut aktive søyelam med høy estimert 90-dagersvekt og tilfredsstillende avlsindeks.
* **Kritiske Tiltaksgrenser (⚠️/🚨):** Flagger automatisk lam som ligger under de kritiske tilvekstgrensene ved henholdsvis 56 dager (f.eks. < 15 kg) og 90 dager (f.eks. < 17 kg).
* **Effektivitetsanalyse (📊):** Beregner den reelle slakteprosenten basert på estimert levendevekt på utmeldingsdagen mot faktisk slaktevekt i kilo.
* **Interaktive Tilvekstkurver (📈):** 
  * **Reell Kurve:** Viser alle faktiske veiepunkter opp mot en ideell tilvekst på 300 g/dag og markerer kritiske målinger med en rød farge/sone.
  * **Standardisert Kurve:** Estimerer vektene nøyaktig ved 56 og 90 dager for å kunne sammenligne alle lam på nøyaktig like vilkår.

---

## 📂 Slik klargjør du filene fra Sauekontrollen

For at appen skal fungere feilfritt, må du laste opp to rapporter som eksporteres direkte fra Sauekontrollen:

1. **Vektfil (`tilvekstAlleRapport.xls`):**
   * Inneholder kolonner for ID/Øremerke, fødselsvekt, fødselsdato, samt datoer og vekter for de ulike veieomgangene (Dato 1, Vekt 1, Dato 2, Vekt 2, etc.).
2. **Basisinfo (`sau-besetning.xlsx`):**
   * Inneholder opplysninger som Rase, Avlsindeks, Kjønn, samt utmeldingsårsaker, utmeldingsdato, slaktevekt (`slaktkg`) og nettopris.

*Merk: Appen har en intelligent kolonneidentifikator, så du trenger ikke endre kolonnenavnene før opplasting! Den kjenner igjen vanlige norske begreper som 'Øremrk', 'Vekt', 'Slaktkg' osv.*
