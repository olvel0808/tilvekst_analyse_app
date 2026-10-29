# 🐏 Interaktivt Flettingsdashbord for Sauekontrollen

Dette er en interaktiv web-applikasjon utviklet for sauebønder som ønsker å analysere tilvekst, avlsindekser og slakteresultater på en enkel, sikker og visuell måte direkte i nettleseren.

## 🌐 Slik bruker du web-appen
Applikasjonen kjører på nettet via Streamlit. Du trenger ikke å installere noe programvare på din egen maskin – alt du trenger å gjøre er å åpne nettadressen til appen og laste opp dine datafiler fra Sauekontrollen.

---

## 📂 Krav til datafiler fra Sauekontrollen

For at appen skal kunne flette og analysere besetningen din, brukes filer du laster ned direkte fra Sauekontrollen. 

### 1. Obligatorisk fil: Vektrapport (Tilvekst alle vekter)
* **Filnavn:** Typisk `tilvekstAlleRapport.xls`
* **Funksjon:** Denne filen **må** lastes opp for at programmet skal fungere. Den inneholder fødselsdatoer, fødselsvekt og alle registrerte veieomganger.

### 2. Valgfri tilleggsfil: Basisinfo / Besetningsliste
* **Kilde:** Hentes fra Sauekontrollens **besetningsbilde**.
* **Funksjon:** For å låse opp og ta i bruk **alle funksjonene** i programmet (som avansert livdyrsortering, rasefiltrering og slakteeffektivitet), må du laste opp denne filen i tillegg til vektfilen. 
* **Nødvendige kolonner:** Filen må inneholde minst følgende opplysninger for dyrene:
  * **Øremerke** (ID-matching)
  * **Rase** (for filtrering og rasespesifikk statistikk)
  * **Indeks** (avlsindeks for utvelgelse av elite-livdyr)
  * **Slaktedata** (slaktevekt og eventuelt oppgjørspris for effektivitetsanalyse)

*Merk: Appen har en smart kolonneidentifikator som kjenner igjen vanlige norske begreper fra Sauekontrollen (f.eks. 'Øremrk', 'Vekt', 'Slaktkg' osv.), så du slipper å endre eller gi nye navn til kolonnene før opplasting.*

---

## 🚀 Hovedfunksjoner i Web-appen

* **Automatisk Fletting:** Kobler sammen veiedataene med rase, avlsindekser, utmeldingsårsaker og slakteoppgjør i sanntid.
* **Livdyrkandidater (🌟):** Filtrerer automatisk ut aktive søyelam med høy estimert 90-dagersvekt kombinert med tilfredsstillende avlsindeks.
* **Kritiske Tiltaksgrenser (⚠️/🚨):** Flagger automatisk lam som ligger under de kritiske tilvekstgrensene ved 56 dager (f.eks. < 15 kg) og 90 dager (f.eks. < 17 kg).
* **Effektivitetsanalyse (📊):** Beregner den reelle slakteprosenten basert på estimert levendevekt på utmeldingsdagen mot faktisk slaktevekt i kilo.
* **Interaktive Tilvekstkurver (📈):** 
  * **Reell Kurve:** Viser alle faktiske veiepunkter opp mot en ideell tilvekst på 300 g/dag og markerer kritiske målinger med en rød farge/sone.
  * **Standardisert Kurve:** Estimerer vektene nøyaktig ved 56 og 90 dager for å kunne sammenligne alle lam på nøyaktig like vilkår.
