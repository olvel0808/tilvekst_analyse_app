import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patches as patches

st.set_page_config(page_title="Interaktivt Flettingsdashbord", layout="wide")

st.title("∞ Interaktivt Flettingsdashbord (Vekter + Slaktedata)")
st.markdown("Last opp dine Excel-filer fra Sauekontrollen direkte i sidemenyen til venstre for å starte analysen.")

# Sidepanel for innstillinger og opplasting
st.sidebar.header("⚙️ Instillinger og Data")

uploader_vekter = st.sidebar.file_uploader("1. Last opp vekter (tilvekstAlleRapport.xls)", type=["xls", "xlsx"])
uploader_basis = st.sidebar.file_uploader("2. Last opp basisinfo (sau-besetning.xlsx)", type=["xls", "xlsx"])

slider_elite_90 = st.sidebar.slider('Grense Livdyr (90d):', 15.0, 45.0, 30.0, 0.5)
slider_min_indeks = st.sidebar.slider('Minste avlsindeks:', 80, 150, 100, 1)
slider_tiltak_56 = st.sidebar.slider('Kritisk grense (56d):', 5.0, 25.0, 15.0, 0.5)
slider_tiltak_90 = st.sidebar.slider('Kritisk grense (90d):', 10.0, 30.0, 17.0, 0.5)

sok_oremerke = st.sidebar.text_input('Søk på øremerke:', '')

def clean_weight(val):
    if pd.isna(val): return np.nan
    if isinstance(val, str):
        val = val.replace(',', '.')
    try: return float(val)
    except: return np.nan

def clean_id(val):
    if pd.isna(val): return None
    try: return int(float(str(val).strip()))
    except: return str(val).strip()

def finn_kolonne(columns, mulige_navn):
    for navn in mulige_navn:
        for col in columns:
            if str(col).strip().lower() == navn.lower():
                return col
    return None

if uploader_vekter is not None:
    try:
        df_vekter_raw = pd.read_excel(uploader_vekter)
    except Exception as e:
        st.error(f"Feil ved lesing av vektfil: {e}")
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

if not df_vekter_raw.empty:
    v_cols = df_vekter_raw.columns
    col_v_id = finn_kolonne(v_cols, ['øremrk', 'øremerke', 'ind.nr', 'id', 'øremerke_nr'])
    col_v_kjoenn = finn_kolonne(v_cols, ['kjønn', 'kjoenn', 'k'])
    col_v_fvekt = finn_kolonne(v_cols, ['f.vekt', 'f-vekt', 'fødselsvekt', 'fødtvekt'])
    col_v_fodselsdato = finn_kolonne(v_cols, ['dato f.vekt', 'fødselsdato', 'fødtdato', 'født_dato'])

    if col_v_id:
        registrerte_fvekter = []
        if col_v_fvekt:
            for val in df_vekter_raw[col_v_fvekt]:
                fv_renset = clean_weight(val)
                if pd.notna(fv_renset) and fv_renset > 0:
                    registrerte_fvekter.append(fv_renset)
        snitt_fvekt_beregnet = np.mean(registrerte_fvekter) if registrerte_fvekter else 5.0

        basis_dict = {}
        if not df_basis_raw.empty:
            b_cols = df_basis_raw.columns
            col_b_id = finn_kolonne(b_cols, ['øremrk', 'øremerke', 'ind.nr', 'id', 'øremerke_nr'])
            col_b_rase = finn_kolonne(b_cols, ['rase', 'rasetilhørighet', 'breed'])
            col_b_indeks = finn_kolonne(b_cols, ['indeks', 'avlsindeks', 'o.indeks', 'o-indeks'])
            col_b_kjoenn = finn_kolonne(b_cols, ['kjønn', 'kjoenn', 'k'])
            col_b_utkode = finn_kolonne(b_cols, ['utkode', 'utskrevet_årsak', 'status', 'utmeldt_årsak'])
            col_b_utdato = finn_kolonne(b_cols, ['utdato', 'utskrevet_dato', 'utmeldtdato'])
            col_b_slaktkg = finn_kolonne(b_cols, ['slaktkg', 'slaktevekt', 'slakt_vekt'])
            col_b_nettopris = finn_kolonne(b_cols, ['nettopris', 'pris', 'oppgjør'])

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
                            'Kjønn': str(row_b[col_b_kjoenn]).strip() if col_b_kjoenn and pd.notna(row_b[col_b_kjoenn]) else None,
                            'Status': status_str,
                            'UtmeldtDato': utdato_val,
                            'Slaktkg': clean_weight(row_b[col_b_slaktkg]) if col_b_slaktkg else np.nan,
                            'NettoPris': clean_weight(row_b[col_b_nettopris]) if col_b_nettopris else np.nan
                        }

        resultater = []
        reelle_registreringer = []

        for _, row in df_vekter_raw.iterrows():
            raw_id = row[col_v_id]
            lamb_id = clean_id(raw_id)
            if not lamb_id: continue

            b_info = basis_dict.get(lamb_id, {})
            rase = b_info.get('Rase', 'Ukjent')
            indeks_val = b_info.get('Indeks', np.nan)
            gender = b_info.get('Kjønn') or (row[col_v_kjoenn] if col_v_kjoenn and pd.notna(row[col_v_kjoenn]) else 'Ukjent')
            status = b_info.get('Status', 'Aktiv')
            ut_dato = b_info.get('UtmeldtDato', pd.NaT)
            slaktkg = b_info.get('Slaktkg', np.nan)
            nettopris = b_info.get('NettoPris', np.nan)

            fvekt = clean_weight(row[col_v_fvekt]) if col_v_fvekt else snitt_fvekt_beregnet
            if pd.isna(fvekt): fvekt = snitt_fvekt_beregnet

            birth_date = pd.to_datetime(row[col_v_fodselsdato], dayfirst=True, format='mixed', errors='coerce') if col_v_fodselsdato else pd.NaT
            if pd.isna(birth_date): continue

            reelle_registreringer.append({'Oremerke': lamb_id, 'Kjoenn': gender, 'Rase': rase, 'Alder': 0, 'Vekt': fvekt})
            siste_vekt = np.nan
            alder_siste_vekt = 0

            for i in range(1, 11):
                dato_n = finn_kolonne(v_cols, [f'dato {i}', f'dato{i}', f'veiedato {i}', f'veiedato{i}'])
                vekt_n = finn_kolonne(v_cols, [f'vekt {i}', f'vekt{i}', f'veid {i}', f'veid{i}'])
                if dato_n and pd.notna(row[dato_n]):
                    veiedato = pd.to_datetime(row[dato_n], dayfirst=True, format='mixed', errors='coerce')
                    vekt = clean_weight(row[vekt_n]) if vekt_n else np.nan
                    if pd.notna(veiedato) and pd.notna(vekt):
                        alder = (veiedato - birth_date).days
                        if alder > 0:
                            reelle_registreringer.append({'Oremerke': lamb_id, 'Kjoenn': gender, 'Rase': rase, 'Alder': alder, 'Vekt': vekt})
                            if pd.isna(siste_vekt) or alder > alder_siste_vekt:
                                siste_vekt = vekt
                                alder_siste_vekt = alder

            if alder_siste_vekt > 0:
                daglig_tilvekst_kg = (siste_vekt - fvekt) / alder_siste_vekt
                vekt_56 = fvekt + (daglig_tilvekst_kg * 56)
                vekt_90 = fvekt + (daglig_tilvekst_kg * 90)
                alder_slakt = (ut_dato - birth_date).days if pd.notna(ut_dato) else np.nan
                vekt_slakt_est = fvekt + (daglig_tilvekst_kg * alder_slakt) if pd.notna(alder_slakt) else np.nan
                slakteprosent = (slaktkg / vekt_slakt_est) * 100 if pd.notna(alder_slakt) and vekt_slakt_est > 0 else np.nan

                resultater.append({
                    'Oremerke': lamb_id,
                    'Kjoenn': gender,
                    'Rase': rase,
                    'Indeks': indeks_val,
                    'Daglig tilvekst (g)': round(daglig_tilvekst_kg * 1000),
                    'Estimert vekt 56 dager': round(vekt_56, 1),
                    'Estimert vekt 90 dager': round(vekt_90, 1),
                    'Status': status,
                    'Slaktevekt (kg)': slaktkg,
                    'Nettopris (kr)': nettopris,
                    'Slaktealder (dager)': alder_slakt,
                    'Est. levendevekt slakt (kg)': round(vekt_slakt_est, 1) if pd.notna(vekt_slakt_est) else np.nan,
                    'Slakteprosent (%)': round(slakteprosent, 1) if pd.notna(slakteprosent) else np.nan
                })

        hmi_data = pd.DataFrame(resultater)
        long_data_reell = pd.DataFrame(reelle_registreringer)

        unike_raser = ['Alle raser'] + sorted([r for r in hmi_data['Rase'].dropna().unique() if r != 'nan'])
        velg_rase = st.sidebar.selectbox('Filtrer på rase:', unike_raser)

        temp_df = hmi_data.copy()
        if velg_rase != 'Alle raser':
            temp_df = temp_df[temp_df['Rase'] == velg_rase]
        if sok_oremerke:
            temp_df = temp_df[temp_df['Oremerke'].astype(str).str.contains(sok_oremerke)]

        aktive_lam_df = temp_df[temp_df['Status'].astype(str).str.lower() == 'aktiv']
        vekt_kriterium = (aktive_lam_df['Kjoenn'].astype(str).str.lower().str.startswith('s')) & (aktive_lam_df['Estimert vekt 90 dager'] >= slider_elite_90)
        indeks_kriterium = (aktive_lam_df['Indeks'].isna()) | (aktive_lam_df['Indeks'] >= slider_min_indeks)

        elite = aktive_lam_df[vekt_kriterium & indeks_kriterium].sort_values('Estimert vekt 90 dager', ascending=False)
        tiltak_56 = temp_df[temp_df['Estimert vekt 56 dager'] < slider_tiltak_56].sort_values('Estimert vekt 56 dager')
        tiltak_90 = temp_df[temp_df['Estimert vekt 90 dager'] < slider_tiltak_90].sort_values('Estimert vekt 90 dager')

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "🌟 Potensielle Livdyr",
            "⚠️ Tiltak 56 dager",
            "🚨 Tiltak 90 dager",
            "📊 Effektivitetsanalyse",
            "📈 Tilvekst (Reell)",
            "📈 Tilvekst (Estimert)"
        ])

        def fargelegg_og_vis(df):
            if df.empty:
                st.info("Ingen dyr funnet med gjeldende filter.")
                return
            df_style = df.copy()
            st.dataframe(df_style.style.format({
                'Slaktevekt (kg)': '{:.1f}',
                'Nettopris (kr)': '{:.0f}',
                'Slakteprosent (%)': '{:.1f} %'
            }))

        with tab1:
            st.subheader(f"Potensielle Aktive Livdyr (Antall: {len(elite)})")
            fargelegg_og_vis(elite[['Oremerke', 'Kjoenn', 'Rase', 'Indeks', 'Daglig tilvekst (g)', 'Estimert vekt 56 dager', 'Estimert vekt 90 dager', 'Status']])

        with tab2:
            st.subheader(f"Kritiske tiltakstiltak 56 dager (Antall: {len(tiltak_56)})")
            fargelegg_og_vis(tiltak_56[['Oremerke', 'Kjoenn', 'Rase', 'Estimert vekt 56 dager', 'Status']])

        with tab3:
            st.subheader(f"Kritiske tiltakstiltak 90 dager (Antall: {len(tiltak_90)})")
            fargelegg_og_vis(tiltak_90[['Oremerke', 'Kjoenn', 'Rase', 'Estimert vekt 90 dager', 'Status']])

        with tab4:
            st.subheader("Effektivitetsanalyse (Reelle slaktedata vs Estimert)")
            effekt_df = temp_df[temp_df['Slaktevekt (kg)'].notna() & (temp_df['Slaktevekt (kg)'] > 0)].copy()
            fargelegg_og_vis(effekt_df[['Oremerke', 'Kjoenn', 'Rase', 'Slaktealder (dager)', 'Est. levendevekt slakt (kg)', 'Slaktevekt (kg)', 'Slakteprosent (%)', 'Status']])

        with tab5:
            st.subheader("Reell Tilvekstkurve")
            if not long_data_reell.empty:
                p_df = long_data_reell.copy()
                if velg_rase != 'Alle raser': p_df = p_df[p_df['Rase'] == velg_rase]
                if sok_oremerke: p_df = p_df[p_df['Oremerke'].astype(str).str.contains(sok_oremerke)]
                
                fig, ax = plt.subplots(figsize=(10, 5))
                sns.scatterplot(data=p_df, x='Alder', y='Vekt', hue='Kjoenn', alpha=0.7, ax=ax)
                
                x_max = max(p_df['Alder']) if len(p_df) > 0 else 100
                x_vals = np.array([0, x_max])
                
                # Standard vekstkurver
                ax.plot(x_vals, snitt_fvekt_beregnet + 0.3 * x_vals, 'g--', label='300 g/dag')
                grense_tilvekst_dgl = (slider_tiltak_90 - snitt_fvekt_beregnet) / 90.0
                if grense_tilvekst_dgl < 0: grense_tilvekst_dgl = 0.100
                ax.plot(x_vals, snitt_fvekt_beregnet + grense_tilvekst_dgl * x_vals, 'r--', label=f'Kritisk grense')
                
                # Rød skravering / tiltakssone
                ax.fill_between(x_vals, 0, snitt_fvekt_beregnet + grense_tilvekst_dgl * x_vals, color='red', alpha=0.08, label='Tiltakssone')
                
                ax.set_xlabel('Alder (dager)')
                ax.set_ylabel('Vekt (kg)')
                ax.grid(True, linestyle=':', alpha=0.6)
                ax.legend(loc='upper left')
                st.pyplot(fig)

        with tab6:
            st.subheader("Standardisert Tilvekstkurve (Estimerte Verdier)")
            est_recs = []
            for _, r in temp_df.iterrows():
                est_recs.append({'Oremerke': r['Oremerke'], 'Kjoenn': r['Kjoenn'], 'Alder': 56, 'Vekt': r['Estimert vekt 56 dager']})
                est_recs.append({'Oremerke': r['Oremerke'], 'Kjoenn': r['Kjoenn'], 'Alder': 90, 'Vekt': r['Estimert vekt 90 dager']})
            est_df = pd.DataFrame(est_recs)
            
            if not est_df.empty:
                fig, ax = plt.subplots(figsize=(10, 5))
                sns.scatterplot(data=est_df, x='Alder', y='Vekt', hue='Kjoenn', alpha=0.7, s=60, ax=ax)
                ax.axvline(x=56, color='gray', linestyle=':')
                ax.axvline(x=90, color='gray', linestyle=':')
                
                x_vals_est = np.array([0, 105])
                # Grønn linje
                ax.plot(x_vals_est, snitt_fvekt_beregnet + 0.300 * x_vals_est, color='green', linestyle='--', alpha=0.8, label='300 g/dag')
                # Rød linje
                grense_tilvekst_dgl_90 = (slider_tiltak_90 - snitt_fvekt_beregnet) / 90.0
                ax.plot(x_vals_est, snitt_fvekt_beregnet + grense_tilvekst_dgl_90 * x_vals_est, color='red', linestyle='--', alpha=0.8, label='Kritisk grense')
                
                # Røde tiltakssoner (skravering)
                rect_56 = patches.Rectangle((53, 0), 6, slider_tiltak_56, linewidth=1, edgecolor='red', facecolor='red', alpha=0.15)
                rect_90 = patches.Rectangle((87, 0), 6, slider_tiltak_90, linewidth=1, edgecolor='red', facecolor='red', alpha=0.15, label='Kritisk sone')
                ax.add_patch(rect_56)
                ax.add_patch(rect_90)
                
                ax.set_xlabel('Alder (dager)')
                ax.set_ylabel('Vekt (kg)')
                ax.grid(True, linestyle=':', alpha=0.6)
                ax.legend(loc='upper left')
                st.pyplot(fig)
    else:
        st.warning("Finner ikke øremerkings-id i den opplastede vektfilen.")
else:
    st.info("Vennligst last opp 'tilvekstAlleRapport.xls' og 'sau-besetning.xlsx' i sidepanelet til venstre for å starte.")
