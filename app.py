import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patches as patches

st.set_page_config(page_title="Nedre kland gard - Tilvekst og Slakteanalysatoren", layout="wide")

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
                "name": "Nedre kland gard Analysator",
                "short_name": "NG Analyse",
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

st.title("Nedre kland gard - Tilvekst og Slakteanalysatoren")
st.markdown("Last opp Tru-Test fila di (CSV) og basisfila fr Sauekontrollen (Excel) i sidemenyen.")

st.sidebar.header("Innstillingar og Data")

uploader_vekter = st.sidebar.file_uploader("1. Last opp Tru-Test vekter (.csv)", type=["csv"])
uploader_basis = st.sidebar.file_uploader("2. Last opp basisinfo (sau-besetning.xlsx)", type=["xls", "xlsx"])

slider_elite_90 = st.sidebar.slider('Grense Livdyr (90d):', 15.0, 45.0, 30.0, 0.5)
slider_min_indeks = st.sidebar.slider('Minste avlsindeks:', 80, 150, 100, 1)
slider_tiltak_56 = st.sidebar.slider('Kritisk grense (56d):', 5.0, 25.0, 15.0, 0.5)
slider_tiltak_90 = st.sidebar.slider('Kritisk grense (90d):', 10.0, 30.0, 17.0, 0.5)
sok_oremerke = st.sidebar.text_input('Sk p yremerke:', '')

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
    return None

if uploader_vekter is not None:
    try:
        df_vekter_raw = pd.read_csv(uploader_vekter, sep=None, engine='python')
    except Exception as e:
        st.error(f"Feil ved lesing av Tru-Test fil: {e}")
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
    # Klargjr Tru-Test data
    df_vekter_raw['EID_temp'] = df_vekter_raw['EID'].fillna(df_vekter_raw.get('VID', pd.Series(dtype=str)))
    df_vekter_raw['yremerke_TruTest'] = df_vekter_raw['EID_temp'].apply(extract_eid)
    df_vekter_raw['Weight'] = df_vekter_raw['Weight'].apply(clean_weight)
    df_vekter_raw['Veiedato'] = pd.to_datetime(df_vekter_raw['Date'], errors='coerce')
    
    # Klargjr Basis data fr Sauekontrollen
    df_basis_raw.columns = df_basis_raw.columns.str.strip()
    id_col = 'Øremrk' if 'remrk' in df_basis_raw.columns else 'Øremerke' if 'remerke' in df_basis_raw.columns else df_basis_raw.columns[0]
    df_basis_raw['yremerke_Clean'] = df_basis_raw[id_col].apply(clean_id)
    
    basis_dict = {}
    for _, row in df_basis_raw.iterrows():
        bid = row['yremerke_Clean']
        if bid:
            fvekt = clean_weight(row.get('Fdtvekt', np.nan)) if 'Fdtvekt' in df_basis_raw.columns else 5.0
            fdato = pd.to_datetime(row.get('FdtDato', pd.NaT), errors='coerce') if 'FdtDato' in df_basis_raw.columns else pd.NaT
            
            basis_dict[bid] = {
                'Rase': str(row.get('Rase', 'Ukjent')).strip(),
                'Indeks': clean_weight(row.get('Indeks', np.nan)),
                'Kjnn': str(row.get('Kjnn', 'Ukjent')).strip(),
                'Fdtvekt': fvekt if pd.notna(fvekt) and fvekt > 0 else 5.0,
                'FdtDato': fdato,
                'Slaktkg': clean_weight(row.get('Slaktkg', np.nan)),
                'NettoPris': clean_weight(row.get('NettoPris', np.nan)),
                'Status': "Aktiv" # Forenkla status
            }

    resultater = []
    reelle_registreringer = []

    snitt_fvekt_beregnet = 5.0

    for _, row in df_vekter_raw.dropna(subset=['yremerke_TruTest']).iterrows():
        lamb_id = row['yremerke_TruTest']
        vekt = row['Weight']
        veiedato = row['Veiedato']
        
        if pd.isna(vekt) or pd.isna(veiedato):
            continue

        b_info = basis_dict.get(lamb_id)
        if not b_info:
            continue # Hopp over om lammet ikkje finst i basisfila

        birth_date = b_info['FdtDato']
        fvekt = b_info['Fdtvekt']
        rase = b_info['Rase']
        gender = b_info['Kjnn']

        if pd.isna(birth_date):
            continue

        alder = (veiedato - birth_date).days
        if alder > 0:
            # Registrer reell veging
            reelle_registreringer.append({'Øyremerke': lamb_id, 'Kjnn': gender, 'Rase': rase, 'Alder': 0, 'Vekt': fvekt})
            reelle_registreringer.append({'Øyremerke': lamb_id, 'Kjnn': gender, 'Rase': rase, 'Alder': alder, 'Vekt': vekt})

            daglig_tilvekst_kg = (vekt - fvekt) / alder
            vekt_56 = fvekt + (daglig_tilvekst_kg * 56)
            vekt_90 = fvekt + (daglig_tilvekst_kg * 90)

            # Legg til eller oppdater i resultater
            # For enkelheits skuld, om det er fleire vegingar, overskriv vi med den siste.
            res_idx = next((i for i, r in enumerate(resultater) if r['Øyremerke'] == lamb_id), None)
            
            res_obj = {
                'Øyremerke': lamb_id,
                'Kjnn': gender,
                'Rase': rase,
                'Indeks': b_info['Indeks'],
                'Dagleg tilvekst (g)': round(daglig_tilvekst_kg * 1000),
                'Estimert vekt 56 dagar': round(vekt_56, 1),
                'Estimert vekt 90 dagar': round(vekt_90, 1),
                'Status': 'Aktiv',
                'Slaktevekt (kg)': b_info['Slaktkg'],
                'Nettopris (kr)': b_info['NettoPris'],
                'Slaktealder (dagar)': np.nan,
                'Est. levandevekt slakt (kg)': np.nan,
                'Slakteprosent (%)': np.nan
            }
            
            if res_idx is not None:
                resultater[res_idx] = res_obj
            else:
                resultater.append(res_obj)

    hmi_data = pd.DataFrame(resultater)
    long_data_reell = pd.DataFrame(reelle_registreringer)
    
    if not hmi_data.empty:
        unike_raser = ['Alle rasar'] + sorted([r for r in hmi_data['Rase'].dropna().unique() if r != 'nan'])
        velg_rase = st.sidebar.selectbox('Filtrer p rase:', unike_raser)

        temp_df = hmi_data.copy()
        if velg_rase != 'Alle rasar':
            temp_df = temp_df[temp_df['Rase'] == velg_rase]
        if sok_oremerke:
            temp_df = temp_df[temp_df['Øyremerke'].astype(str).str.contains(sok_oremerke)]

        aktive_lam_df = temp_df[temp_df['Status'].astype(str).str.lower() == 'aktiv']
        vekt_kriterium = (aktive_lam_df['Kjnn'].astype(str).str.lower().str.startswith('s')) & (aktive_lam_df['Estimert vekt 90 dagar'] >= slider_elite_90)
        indeks_kriterium = (aktive_lam_df['Indeks'].isna()) | (aktive_lam_df['Indeks'] >= slider_min_indeks)

        elite = aktive_lam_df[vekt_kriterium & indeks_kriterium].sort_values('Estimert vekt 90 dagar', ascending=False)
        tiltak_56 = temp_df[temp_df['Estimert vekt 56 dagar'] < slider_tiltak_56].sort_values('Estimert vekt 56 dagar')
        tiltak_90 = temp_df[temp_df['Estimert vekt 90 dagar'] < slider_tiltak_90].sort_values('Estimert vekt 90 dagar')

        tab1, tab2, tab3, tab4 = st.tabs([
            "🌟 Potensielle Livdyr",
            "⚠️ Tiltak 56 dagar",
            "🚨 Tiltak 90 dagar",
            "📈 Tilvekst (Reell)"
        ])

        def fargelegg_og_vis(df):
            if df.empty:
                st.info("Fann ingen dyr med gjeldande filter.")
                return
            df_style = df.copy()
            st.dataframe(df_style)

        with tab1:
            st.subheader(f"Potensielle Aktive Livdyr (Tal: {len(elite)})")
            fargelegg_og_vis(elite[['Øyremerke', 'Kjnn', 'Rase', 'Indeks', 'Dagleg tilvekst (g)', 'Estimert vekt 56 dagar', 'Estimert vekt 90 dagar']])

        with tab2:
            st.subheader(f"Kritiske tiltak 56 dagar (Tal: {len(tiltak_56)})")
            fargelegg_og_vis(tiltak_56[['Øyremerke', 'Kjnn', 'Rase', 'Estimert vekt 56 dagar']])

        with tab3:
            st.subheader(f"Kritiske tiltak 90 dagar (Tal: {len(tiltak_90)})")
            fargelegg_og_vis(tiltak_90[['Øyremerke', 'Kjnn', 'Rase', 'Estimert vekt 90 dagar']])

        with tab4:
            st.subheader("Reell Tilvekstkurve")
            if not long_data_reell.empty:
                p_df = long_data_reell.copy()
                if velg_rase != 'Alle rasar': p_df = p_df[p_df['Rase'] == velg_rase]
                if sok_oremerke: p_df = p_df[p_df['Øyremerke'].astype(str).str.contains(sok_oremerke)]

                fig, ax = plt.subplots(figsize=(10, 5))
                sns.scatterplot(data=p_df, x='Alder', y='Vekt', hue='Kjnn', alpha=0.7, ax=ax)

                x_max = max(p_df['Alder']) if len(p_df) > 0 else 100
                x_vals = np.array([0, x_max])

                ax.plot(x_vals, snitt_fvekt_beregnet + 0.3 * x_vals, 'g--', label='300 g/dag')
                grense_tilvekst_dgl = (slider_tiltak_90 - snitt_fvekt_beregnet) / 90.0
                if grense_tilvekst_dgl < 0: grense_tilvekst_dgl = 0.100
                ax.plot(x_vals, snitt_fvekt_beregnet + grense_tilvekst_dgl * x_vals, 'r--', label=f'Kritisk grense')
                ax.fill_between(x_vals, 0, snitt_fvekt_beregnet + grense_tilvekst_dgl * x_vals, color='red', alpha=0.08, label='Tiltakssone')

                ax.set_xlabel('Alder (dagar)')
                ax.set_ylabel('Vekt (kg)')
                ax.grid(True, linestyle=':', alpha=0.6)
                ax.legend(loc='upper left')
                st.pyplot(fig)
    else:
        st.warning("Fann ingen felles data mellom Tru-Test fila og basisfila. Sjekk at yremerka stemmer overeins.")
else:
    st.info("Last opp bde Tru-Test CSV og Basisinfo for  byrje.")
