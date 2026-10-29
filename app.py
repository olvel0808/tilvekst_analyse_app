import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patches as patches

st.set_page_config(page_title="Nedre Økland gard - Tilvekst og Slakteanalysatoren", layout="wide")

# PWA Konfigurasjon
def pwa_setup():
    import streamlit.components.v1 as components
    pwa_html = """
    <script>
        const doc = window.parent.document;
        if (!doc.querySelector('link[rel="manifest"]')) {
            const manifest = doc.createElement('link');
            manifest.rel = 'manifest';
            manifest.href = 'data:application/manifest+json;charset=utf-8,' + encodeURIComponent(JSON.stringify({
                "name": "Nedre Økland gard Analysator",
                "short_name": "NØG Analyse",
                "theme_color": "#4CAF50",
                "background_color": "#ffffff",
                "display": "standalone",
                "orientation": "portrait",
                "start_url": ".",
                "icons": [
                    {
                        "src": "https://cdn-icons-png.flaticon.com/512/1970/1970044.png",
                        "sizes": "512x512",
                        "type": "image/png"
                    }
                ]
            }));
            doc.head.appendChild(manifest);
        }
    </script>
    """
    components.html(pwa_html, height=0)

pwa_setup()

st.title("🐏 Nedre Økland gard - Tilvekst og Slakteanalysatoren")
st.markdown("Last opp vekter (.xls frå Sauekontrollen ELLER .csv frå Tru-Test) og basisfila (.xlsx) i sidemenyen.")

st.sidebar.header("⚙️ Innstillingar og Data")

uploader_vekter = st.sidebar.file_uploader("1. Last opp vekter (.xls, .xlsx, .csv)", type=["xls", "xlsx", "csv", "CSV"])
uploader_basis = st.sidebar.file_uploader("2. Last opp basisinfo (sau-besetning.xlsx)", type=["xls", "xlsx"])

slider_elite_90 = st.sidebar.slider('Grense Livdyr (90d):', 15.0, 45.0, 30.0, 0.5)
slider_min_indeks = st.sidebar.slider('Minste avlsindeks:', 80, 150, 100, 1)
slider_tiltak_56 = st.sidebar.slider('Kritisk grense (56d):', 5.0, 25.0, 15.0, 0.5)
slider_tiltak_90 = st.sidebar.slider('Kritisk grense (90d):', 10.0, 30.0, 17.0, 0.5)
sok_oremerke = st.sidebar.text_input('Søk på øyremerke:', '')

def clean_weight(val):
    if pd.isna(val): return np.nan
    if isinstance(val, str): val = val.replace(',', '.')
    try: return float(val)
    except: return np.nan

def clean_id(val):
    if pd.isna(val): return None
    try: return int(float(str(val).strip()))
    except: return str(val).strip()

def extract_eid(val):
    if pd.isna(val): return None
    val_str = str(val).strip().replace(' ', '')
    if len(val_str) >= 5:
        try:
            return int(val_str[-5:])
        except:
            pass
    return clean_id(val)

def finn_kolonne(columns, mulige_navn):
    for navn in mulige_navn:
        for col in columns:
            if str(col).strip().lower() == navn.lower():
                return col
    return None

def vis_bruksanvisning():
    st.markdown('''### ℹ️ Korleis kome i gang?
For at appen skal kunne flette og analysere besetninga di, treng du to filer:

#### 1. Obligatorisk fil: Vektrapport
* **Sauekontrollen:** `tilvekstAlleRapport.xls`
* **Tru-Test:** `.csv` fil frå vektstaven (Må innehalde EID eller VID, og Weight).

#### 2. Obligatorisk tilleggsfil: Basisinfo / Besetningsliste
* **Kjelde:** Hentast frå Sauekontrollen sitt besetningsbilete (`sau-besetning.xlsx`).
* **Innhald:** Må innehalde kolonnane **Øyremerke, Rase, Indeks, Fødselsdato, og Slaktedata**.

---

### 🚀 Hovudfunksjonar
* **🌟 Potensielle Livdyr:** Viser aktive søyelam sortert etter 90-dagars estimert vekt og rase.
* **⚠️ Tiltak 56 dagar & 🚨 90 dagar:** Gir ei raud flagg-liste over lam som ligg under kritiske vekstkurver.
* **📊 Effektivitetsanalyse:** Reknar ut reell slakteprosent (levandevekt på slaktedagen vs. reell slaktevekt).
* **📈 Tilvekstkurve:** Viser reelle målingar mot standardiserte kurver og markerer faresoner automatisk.
''')

if uploader_vekter is not None:
    try:
        # Sjekk både små og store bokstaver for CSV
        if uploader_vekter.name.lower().endswith('.csv'):
            try:
                df_vekter_raw = pd.read_csv(uploader_vekter, sep=None, engine='python')
            except Exception:
                uploader_vekter.seek(0)
                try:
                    df_vekter_raw = pd.read_csv(uploader_vekter, sep=';', encoding='latin-1')
                except Exception:
                    uploader_vekter.seek(0)
                    df_vekter_raw = pd.read_csv(uploader_vekter, sep=',', encoding='utf-8', on_bad_lines='skip')
            kilde_type = 'trutest'
        else:
            df_vekter_raw = pd.read_excel(uploader_vekter)
            kilde_type = 'sauekontrollen'
    except Exception as e:
        st.error(f"Klarte ikkje å lese fila. Feilmelding: {e}")
        df_vekter_raw = pd.DataFrame()
else:
    df_vekter_raw = pd.DataFrame()

if uploader_basis is not None:
    try:
        df_basis_raw = pd.read_excel(uploader_basis)
    except Exception as e:
        st.error(f"Feil ved lesing av basisfil: {e}")
        df_basis_raw = pd.DataFrame()
else:
    df_basis_raw = pd.DataFrame()

har_data = not df_vekter_raw.empty and not df_basis_raw.empty

if har_data:
    # --- 1. KLARGJØR BASISDATA ---
    b_cols = df_basis_raw.columns
    col_b_id = finn_kolonne(b_cols, ['øremrk', 'øremerke', 'ind.nr', 'id', 'øremerke_nr', 'oremrk', 'oremerke'])
    col_b_rase = finn_kolonne(b_cols, ['rase', 'rasetilhørighet', 'breed'])
    col_b_indeks = finn_kolonne(b_cols, ['indeks', 'avlsindeks', 'o.indeks', 'o-indeks'])
    col_b_kjoenn = finn_kolonne(b_cols, ['kjønn', 'kjoenn', 'k'])
    col_b_utkode = finn_kolonne(b_cols, ['utkode', 'utskrevet_årsak', 'status', 'utmeldt_årsak'])
    col_b_utdato = finn_kolonne(b_cols, ['utdato', 'utskrevet_dato', 'utmeldtdato'])
    col_b_slaktkg = finn_kolonne(b_cols, ['slaktkg', 'slaktevekt', 'slakt_vekt'])
    col_b_nettopris = finn_kolonne(b_cols, ['nettopris', 'pris', 'oppgjør'])
    col_b_fvekt = finn_kolonne(b_cols, ['fødtvekt', 'fødselsvekt', 'f.vekt', 'f-vekt'])
    col_b_fdato = finn_kolonne(b_cols, ['fødtdato', 'fødselsdato', 'dato f.vekt'])

    basis_dict = {}
    if col_b_id:
        for _, row_b in df_basis_raw.iterrows():
            bid = clean_id(row_b[col_b_id])
            if bid:
                utkode_val = str(row_b[col_b_utkode]).strip() if col_b_utkode and pd.notna(row_b[col_b_utkode]) else None
                utdato_val = pd.to_datetime(row_b[col_b_utdato], dayfirst=True, format='mixed', errors='coerce') if col_b_utdato and pd.notna(row_b[col_b_utdato]) else pd.NaT
                status_str = "Aktiv"
                if utkode_val and utkode_val != 'nan' and utkode_val != '':
                    status_str = f"{utkode_val} {utdato_val.strftime('%d.%m.%y')}" if pd.notna(utdato_val) else utkode_val

                basis_dict[bid] = {
                    'Rase': str(row_b[col_b_rase]).strip() if col_b_rase and pd.notna(row_b[col_b_rase]) else 'Ukjent',
                    'Indeks': clean_weight(row_b[col_b_indeks]) if col_b_indeks else np.nan,
                    'Kjønn': str(row_b[col_b_kjoenn]).strip() if col_b_kjoenn and pd.notna(row_b[col_b_kjoenn]) else 'Ukjent',
                    'Status': status_str,
                    'UtmeldtDato': utdato_val,
                    'Slaktkg': clean_weight(row_b[col_b_slaktkg]) if col_b_slaktkg else np.nan,
                    'NettoPris': clean_weight(row_b[col_b_nettopris]) if col_b_nettopris else np.nan,
                    'Fødtvekt': clean_weight(row_b[col_b_fvekt]) if col_b_fvekt else 5.0,
                    'FødtDato': pd.to_datetime(row_b[col_b_fdato], errors='coerce') if col_b_fdato else pd.NaT
                }

    resultater = []
    reelle_registreringer = []
    snitt_fvekt_beregnet = 5.0

    # --- 2. KLARGJØR VEKTDATA (Sauekontrollen eller Tru-Test) ---
    if kilde_type == 'trutest':
        if 'EID' in df_vekter_raw.columns:
            df_vekter_raw['EID_temp'] = df_vekter_raw['EID'].fillna(df_vekter_raw.get('VID', pd.Series(dtype=str)))
        elif 'VID' in df_vekter_raw.columns:
            df_vekter_raw['EID_temp'] = df_vekter_raw['VID']
        else:
            st.error("Tru-Test fila manglar EID og VID kolonner.")
            st.stop()

        df_vekter_raw['Øyremerke_Clean'] = df_vekter_raw['EID_temp'].apply(extract_eid)
        df_vekter_raw['Vekt_Clean'] = df_vekter_raw['Weight'].apply(clean_weight) if 'Weight' in df_vekter_raw.columns else np.nan
        df_vekter_raw['Dato_Clean'] = pd.to_datetime(df_vekter_raw['Date'], errors='coerce') if 'Date' in df_vekter_raw.columns else pd.NaT

        for _, row in df_vekter_raw.dropna(subset=['Øyremerke_Clean']).iterrows():
            lamb_id = row['Øyremerke_Clean']
            vekt = row['Vekt_Clean']
            veiedato = row['Dato_Clean']
            if pd.isna(vekt) or pd.isna(veiedato): continue

            b_info = basis_dict.get(lamb_id)
            if not b_info: continue

            birth_date = b_info['FødtDato']
            if pd.isna(birth_date): continue
            fvekt = b_info['Fødtvekt'] if pd.notna(b_info['Fødtvekt']) and b_info['Fødtvekt'] > 0 else 5.0

            alder = (veiedato - birth_date).days
            if alder > 0:
                reelle_registreringer.append({'Øyremerke': lamb_id, 'Kjønn': b_info['Kjønn'], 'Rase': b_info['Rase'], 'Alder': 0, 'Vekt': fvekt})
                reelle_registreringer.append({'Øyremerke': lamb_id, 'Kjønn': b_info['Kjønn'], 'Rase': b_info['Rase'], 'Alder': alder, 'Vekt': vekt})

                daglig_tilvekst_kg = (vekt - fvekt) / alder
                vekt_56 = fvekt + (daglig_tilvekst_kg * 56)
                vekt_90 = fvekt + (daglig_tilvekst_kg * 90)

                res_idx = next((i for i, r in enumerate(resultater) if r['Øyremerke'] == lamb_id), None)
                res_obj = {
                    'Øyremerke': lamb_id, 'Kjønn': b_info['Kjønn'], 'Rase': b_info['Rase'], 'Indeks': b_info['Indeks'],
                    'Dagleg tilvekst (g)': round(daglig_tilvekst_kg * 1000), 'Estimert vekt 56 dagar': round(vekt_56, 1),
                    'Estimert vekt 90 dagar': round(vekt_90, 1), 'Status': b_info['Status'], 'Slaktevekt (kg)': b_info['Slaktkg'],
                    'Nettopris (kr)': b_info['NettoPris'], 'Slaktealder (dagar)': np.nan, 'Est. levandevekt slakt (kg)': np.nan, 'Slakteprosent (%)': np.nan
                }
                if res_idx is not None:
                    resultater[res_idx] = res_obj
                else:
                    resultater.append(res_obj)

    elif kilde_type == 'sauekontrollen':
        v_cols = df_vekter_raw.columns
        col_v_id = finn_kolonne(v_cols, ['øremrk', 'øremerke', 'ind.nr', 'id', 'øremerke_nr', 'oremrk', 'oremerke'])
        col_v_fvekt = finn_kolonne(v_cols, ['f.vekt', 'f-vekt', 'fødselsvekt', 'fødtvekt'])
        col_v_fdato = finn_kolonne(v_cols, ['dato f.vekt', 'fødselsdato', 'fødtdato', 'født_dato'])

        for _, row in df_vekter_raw.iterrows():
            raw_id = row[col_v_id] if col_v_id else None
            lamb_id = clean_id(raw_id)
            if not lamb_id: continue

            b_info = basis_dict.get(lamb_id, {})
            birth_date = pd.to_datetime(row[col_v_fdato], dayfirst=True, errors='coerce') if col_v_fdato else pd.NaT
            if pd.isna(birth_date): birth_date = b_info.get('FødtDato', pd.NaT)
            if pd.isna(birth_date): continue

            fvekt = clean_weight(row[col_v_fvekt]) if col_v_fvekt else np.nan
            if pd.isna(fvekt): fvekt = b_info.get('Fødtvekt', 5.0)

            kjoenn = b_info.get('Kjønn', 'Ukjent')
            rase = b_info.get('Rase', 'Ukjent')

            reelle_registreringer.append({'Øyremerke': lamb_id, 'Kjønn': kjoenn, 'Rase': rase, 'Alder': 0, 'Vekt': fvekt})
            siste_vekt = np.nan
            alder_siste_vekt = 0

            for i in range(1, 11):
                dato_n = finn_kolonne(v_cols, [f'dato {i}', f'dato{i}', f'veiedato {i}', f'veiedato{i}'])
                vekt_n = finn_kolonne(v_cols, [f'vekt {i}', f'vekt{i}', f'veid {i}', f'veid{i}'])
                if dato_n and pd.notna(row[dato_n]):
                    veiedato = pd.to_datetime(row[dato_n], dayfirst=True, errors='coerce')
                    vekt = clean_weight(row[vekt_n]) if vekt_n else np.nan
                    if pd.notna(veiedato) and pd.notna(vekt):
                        alder = (veiedato - birth_date).days
                        if alder > 0:
                            reelle_registreringer.append({'Øyremerke': lamb_id, 'Kjønn': kjoenn, 'Rase': rase, 'Alder': alder, 'Vekt': vekt})
                            if pd.isna(siste_vekt) or alder > alder_siste_vekt:
                                siste_vekt = vekt
                                alder_siste_vekt = alder

            if alder_siste_vekt > 0:
                daglig_tilvekst_kg = (siste_vekt - fvekt) / alder_siste_vekt
                vekt_56 = fvekt + (daglig_tilvekst_kg * 56)
                vekt_90 = fvekt + (daglig_tilvekst_kg * 90)
                ut_dato = b_info.get('UtmeldtDato', pd.NaT)
                slaktkg = b_info.get('Slaktkg', np.nan)
                alder_slakt = (ut_dato - birth_date).days if pd.notna(ut_dato) else np.nan
                vekt_slakt_est = fvekt + (daglig_tilvekst_kg * alder_slakt) if pd.notna(alder_slakt) else np.nan
                slakteprosent = (slaktkg / vekt_slakt_est) * 100 if pd.notna(alder_slakt) and vekt_slakt_est > 0 else np.nan

                resultater.append({
                    'Øyremerke': lamb_id, 'Kjønn': kjoenn, 'Rase': rase, 'Indeks': b_info.get('Indeks', np.nan),
                    'Dagleg tilvekst (g)': round(daglig_tilvekst_kg * 1000), 'Estimert vekt 56 dagar': round(vekt_56, 1),
                    'Estimert vekt 90 dagar': round(vekt_90, 1), 'Status': b_info.get('Status', 'Aktiv'), 'Slaktevekt (kg)': slaktkg,
                    'Nettopris (kr)': b_info.get('NettoPris', np.nan), 'Slaktealder (dagar)': alder_slakt,
                    'Est. levandevekt slakt (kg)': round(vekt_slakt_est, 1) if pd.notna(vekt_slakt_est) else np.nan,
                    'Slakteprosent (%)': round(slakteprosent, 1) if pd.notna(slakteprosent) else np.nan
                })

    # --- 3. PRESENTASJON I DASHBOARD ---
    hmi_data = pd.DataFrame(resultater)
    long_data_reell = pd.DataFrame(reelle_registreringer)

    if not hmi_data.empty:
        unike_raser = ['Alle rasar'] + sorted([r for r in hmi_data['Rase'].dropna().unique() if str(r).lower() != 'nan'])
        velg_rase = st.sidebar.selectbox('Filtrer på rase:', unike_raser)

        temp_df = hmi_data.copy()
        if velg_rase != 'Alle rasar':
            temp_df = temp_df[temp_df['Rase'] == velg_rase]
        if sok_oremerke:
            temp_df = temp_df[temp_df['Øyremerke'].astype(str).str.contains(sok_oremerke)]

        aktive_lam_df = temp_df[temp_df['Status'].astype(str).str.lower() == 'aktiv']
        vekt_kriterium = (aktive_lam_df['Kjønn'].astype(str).str.lower().str.startswith('s')) & (aktive_lam_df['Estimert vekt 90 dagar'] >= slider_elite_90)
        indeks_kriterium = (aktive_lam_df['Indeks'].isna()) | (aktive_lam_df['Indeks'] >= slider_min_indeks)

        elite = aktive_lam_df[vekt_kriterium & indeks_kriterium].sort_values('Estimert vekt 90 dagar', ascending=False)
        tiltak_56 = temp_df[temp_df['Estimert vekt 56 dagar'] < slider_tiltak_56].sort_values('Estimert vekt 56 dagar')
        tiltak_90 = temp_df[temp_df['Estimert vekt 90 dagar'] < slider_tiltak_90].sort_values('Estimert vekt 90 dagar')

        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🌟 Potensielle Livdyr",
            "⚠️ Tiltak 56 dagar",
            "🚨 Tiltak 90 dagar",
            "📊 Effektivitet (Slakt)",
            "📈 Tilvekst (Reell)",
            "📊 Tilvekst (Estimert)",
            "ℹ️ Bruksanvisning & Info"
        ])

        def fargelegg_og_vis(df):
            if df.empty:
                st.info("Fann ingen dyr med gjeldande filter.")
                return
            
            format_dict = {
                'Slaktevekt (kg)': '{:.1f}', 
                'Nettopris (kr)': '{:.0f}', 
                'Slakteprosent (%)': '{:.1f} %',
                'Estimert vekt 56 dagar': '{:.1f}',
                'Estimert vekt 90 dagar': '{:.1f}',
                'Est. levandevekt slakt (kg)': '{:.1f}',
                'Indeks': '{:.0f}'
            }
            
            # Bruk kun dei formata der kolonnane faktisk eksisterer i tabellen
            current_format = {k: v for k, v in format_dict.items() if k in df.columns}
            
            # Vis tabell, na_rep="" gjer at 'nan' (tomme data) blir blankt i staden for stygt
            st.dataframe(df.style.format(current_format, na_rep=""))

        with tab1:
            st.subheader(f"Potensielle Aktive Livdyr (Tal: {len(elite)})")
            fargelegg_og_vis(elite[['Øyremerke', 'Kjønn', 'Rase', 'Indeks', 'Dagleg tilvekst (g)', 'Estimert vekt 56 dagar', 'Estimert vekt 90 dagar', 'Status']])

        with tab2:
            st.subheader(f"Kritiske tiltak 56 dagar (Tal: {len(tiltak_56)})")
            fargelegg_og_vis(tiltak_56[['Øyremerke', 'Kjønn', 'Rase', 'Estimert vekt 56 dagar', 'Status']])

        with tab3:
            st.subheader(f"Kritiske tiltak 90 dagar (Tal: {len(tiltak_90)})")
            fargelegg_og_vis(tiltak_90[['Øyremerke', 'Kjønn', 'Rase', 'Estimert vekt 90 dagar', 'Status']])

        with tab4:
            st.subheader("Effektivitetsanalyse (Slakt)")
            effekt_df = temp_df[temp_df['Slaktevekt (kg)'].notna() & (temp_df['Slaktevekt (kg)'] > 0)].copy()
            fargelegg_og_vis(effekt_df[['Øyremerke', 'Kjønn', 'Rase', 'Slaktealder (dagar)', 'Est. levandevekt slakt (kg)', 'Slaktevekt (kg)', 'Slakteprosent (%)', 'Status']])

        with tab5:
            st.subheader("Reell Tilvekstkurve")
            if not long_data_reell.empty:
                p_df = long_data_reell.copy()
                if velg_rase != 'Alle rasar': p_df = p_df[p_df['Rase'] == velg_rase]
                if sok_oremerke: p_df = p_df[p_df['Øyremerke'].astype(str).str.contains(sok_oremerke)]

                if not p_df.empty:
                    fig, ax = plt.subplots(figsize=(10, 5))
                    sns.scatterplot(data=p_df, x='Alder', y='Vekt', hue='Kjønn', alpha=0.7, ax=ax)

                    x_max = max(p_df['Alder']) if len(p_df) > 0 else 100
                    x_vals = np.array([0, x_max])

                    ax.plot(x_vals, snitt_fvekt_beregnet + 0.3 * x_vals, 'g--', label='300 g/dag')
                    grense_tilvekst_dgl = (slider_tiltak_90 - snitt_fvekt_beregnet) / 90.0
                    if grense_tilvekst_dgl < 0: grense_tilvekst_dgl = 0.100
                    ax.plot(x_vals, snitt_fvekt_beregnet + grense_tilvekst_dgl * x_vals, 'r--', label='Kritisk grense')
                    ax.fill_between(x_vals, 0, snitt_fvekt_beregnet + grense_tilvekst_dgl * x_vals, color='red', alpha=0.08, label='Tiltakssone')

                    ax.set_xlabel('Alder (dagar)')
                    ax.set_ylabel('Vekt (kg)')
                    ax.grid(True, linestyle=':', alpha=0.6)
                    ax.legend(loc='upper left')
                    st.pyplot(fig)
        with tab6:
            st.subheader("Standardisert Tilvekstkurve (Estimerte Verdiar)")
            est_recs = []
            for _, r in temp_df.iterrows():
                est_recs.append({'Øyremerke': r['Øyremerke'], 'Kjønn': r['Kjønn'], 'Alder': 56, 'Vekt': r['Estimert vekt 56 dagar']})
                est_recs.append({'Øyremerke': r['Øyremerke'], 'Kjønn': r['Kjønn'], 'Alder': 90, 'Vekt': r['Estimert vekt 90 dagar']})
            est_df = pd.DataFrame(est_recs)

            if not est_df.empty:
                fig, ax = plt.subplots(figsize=(10, 5))
                sns.scatterplot(data=est_df, x='Alder', y='Vekt', hue='Kjønn', alpha=0.7, s=60, ax=ax)
                ax.axvline(x=56, color='gray', linestyle=':')
                ax.axvline(x=90, color='gray', linestyle=':')

                x_vals_est = np.array([0, 105])
                ax.plot(x_vals_est, snitt_fvekt_beregnet + 0.300 * x_vals_est, color='green', linestyle='--', alpha=0.8, label='300 g/dag')
                grense_tilvekst_dgl_90 = (slider_tiltak_90 - snitt_fvekt_beregnet) / 90.0
                ax.plot(x_vals_est, snitt_fvekt_beregnet + grense_tilvekst_dgl_90 * x_vals_est, color='red', linestyle='--', alpha=0.8, label='Kritisk grense')

                rect_56 = patches.Rectangle((53, 0), 6, slider_tiltak_56, linewidth=1, edgecolor='red', facecolor='red', alpha=0.15)
                rect_90 = patches.Rectangle((87, 0), 6, slider_tiltak_90, linewidth=1, edgecolor='red', facecolor='red', alpha=0.15, label='Kritisk sone')
                ax.add_patch(rect_56)
                ax.add_patch(rect_90)

                ax.set_xlabel('Alder (dagar)')
                ax.set_ylabel('Vekt (kg)')
                ax.grid(True, linestyle=':', alpha=0.6)
                ax.legend(loc='upper left')
                st.pyplot(fig)

        with tab7:
            vis_bruksanvisning()
    else:
        st.warning("Fann ingen felles data. Sjekk at øyremerka stemmer overeins i vekter og basisinfo.")
else:
    vis_bruksanvisning()
