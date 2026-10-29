import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patches as patches
import openpyxl
from openpyxl.drawing.image import Image as OpenpyxlImage

# Konfigurer Streamlit-siden
st.set_page_config(
    page_title="Tilvekstanalysator - Lam",
    page_icon="🐑",
    layout="wide"
)

# --- HJELPEFUNKSJONER ---
def clean_weight(val):
    if pd.isna(val):
        return np.nan
    if isinstance(val, str):
        val = val.replace(',', '.')
    try:
        return float(val)
    except:
        return np.nan

def clean_id(val):
    if pd.isna(val): return None
    try:
        return int(float(str(val).strip()))
    except:
        return str(val).strip()

def finn_kolonne(columns, mulige_navn):
    for navn in mulige_navn:
        for col in columns:
            if str(col).strip().lower() == navn.lower():
                return col
    return None

# --- STRUKTURERING OG FLETTING AV DATA ---
def prosesser_data(df_vekter, df_basis):
    if df_vekter.empty:
        return pd.DataFrame(), pd.DataFrame()

    v_cols = df_vekter.columns
    col_v_id = finn_kolonne(v_cols, ['øremrk', 'øremerke', 'ind.nr', 'id', 'øremerke_nr'])
    col_v_kjoenn = finn_kolonne(v_cols, ['kjønn', 'kjoenn', 'k'])
    col_v_fvekt = finn_kolonne(v_cols, ['f.vekt', 'f-vekt', 'fødselsvekt', 'fødtvekt'])
    col_v_fodselsdato = finn_kolonne(v_cols, ['dato f.vekt', 'fødselsdato', 'fødtdato', 'født_dato'])

    if not col_v_id:
        st.error("Kunne ikke identifisere ID-kolonne i vektfilen!")
        return pd.DataFrame(), pd.DataFrame()

    # Lag oppslagsliste fra basisinfo
    basis_dict = {}
    if not df_basis.empty:
        b_cols = df_basis.columns
        col_b_id = finn_kolonne(b_cols, ['øremrk', 'øremerke', 'ind.nr', 'id', 'øremerke_nr'])
        col_b_rase = finn_kolonne(b_cols, ['rase', 'rasetilhørighet', 'breed'])
        col_b_indeks = finn_kolonne(b_cols, ['indeks', 'avlsindeks', 'o.indeks', 'o-indeks'])
        col_b_kjoenn = finn_kolonne(b_cols, ['kjønn', 'kjoenn', 'k'])
        col_b_utkode = finn_kolonne(b_cols, ['utkode', 'utskrevet_årsak', 'status', 'utmeldt_årsak'])
        col_b_utdato = finn_kolonne(b_cols, ['utdato', 'utskrevet_dato', 'utmeldtdato'])
        col_b_slaktkg = finn_kolonne(b_cols, ['slaktkg', 'slaktevekt', 'slakt_vekt'])
        col_b_nettopris = finn_kolonne(b_cols, ['nettopris', 'pris', 'oppgjør'])

        if col_b_id:
            for _, row_b in df_basis.iterrows():
                bid = clean_id(row_b[col_b_id])
                if bid:
                    utkode_val = str(row_b[col_b_utkode]).strip() if col_b_utkode and pd.notna(row_b[col_b_utkode]) else None
                    utdato_val = pd.to_datetime(row_b[col_b_utdato], dayfirst=True, format='mixed', errors='coerce') if col_b_utdato and pd.notna(row_b[col_b_utdato]) else pd.NaT

                    status_str = "Aktiv"
                    if utkode_val and utkode_val != 'nan' and utkode_val != '':
                        if pd.notna(utdato_val):
                            status_str = f"{utkode_val} {utdato_val.strftime('%d.%m.%y')}"
                        else:
                            status_str = utkode_val

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

    for _, row in df_vekter.iterrows():
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

        fvekt = clean_weight(row[col_v_fvekt]) if col_v_fvekt else 4.5
        if pd.isna(fvekt): fvekt = 4.5

        birth_date = pd.to_datetime(row[col_v_fodselsdato], dayfirst=True, format='mixed', errors='coerce')
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

            alder_slakt = np.nan
            vekt_slakt_est = np.nan
            slakteprosent = np.nan

            if pd.notna(ut_dato) and pd.notna(slaktkg):
                alder_slakt = (ut_dato - birth_date).days
                if alder_slakt > 0:
                    vekt_slakt_est = fvekt + (daglig_tilvekst_kg * alder_slakt)
                    if vekt_slakt_est > 0:
                        slakteprosent = (slaktkg / vekt_slakt_est) * 100

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
                'Slaktealder (dager)': alder_slakt if pd.notna(alder_slakt) else np.nan,
                'Est. levendevekt slakt (kg)': round(vekt_slakt_est, 1) if pd.notna(vekt_slakt_est) else np.nan,
                'Slakteprosent (%)': round(slakteprosent, 1) if pd.notna(slakteprosent) else np.nan
            })

    return pd.DataFrame(resultater), pd.DataFrame(reelle_registreringer)

# --- HOVEDTITTEL ---
st.title("🐑 Interaktivt Tilvekstdashbord")
st.markdown("Last opp dine Sauekontroll-rapporter for å analysere tilvekst, avlsindeks og reelle slakteresultater.")

# --- SIDEPANEL: KONTROLLER ---
st.sidebar.header("⚙️ Instillinger")

up_vekter = st.sidebar.file_uploader("1. Last opp vekter (tilvekstAlleRapport.xls)", type=["xls", "xlsx"])
up_basis = st.sidebar.file_uploader("2. Last opp basisinfo (sau-besetning.xlsx)", type=["xls", "xlsx"])

grense_livdyr = st.sidebar.slider("Min. vekt Livdyr (90 dager):", 15.0, 45.0, 30.0, step=0.5)
min_indeks = st.sidebar.slider("Minste tillatte avlsindeks:", 80, 150, 100, step=1)
grense_56 = st.sidebar.slider("Tiltak Vekt (56 dager):", 5.0, 25.0, 15.0, step=0.5)
grense_90 = st.sidebar.slider("Tiltak Vekt (90 dager):", 10.0, 30.0, 17.0, step=0.5)
sok_verdi = st.sidebar.text_input("Søk på øremerke:", value="").strip()

if up_vekter is not None:
    try:
        df_vekter_raw = pd.ExcelFile(up_vekter).parse()
        df_basis_raw = pd.DataFrame()
        if up_basis is not None:
            df_basis_raw = pd.ExcelFile(up_basis).parse()

        hmi_data, long_data_reell = prosesser_data(df_vekter_raw, df_basis_raw)

        if not hmi_data.empty:
            unike_raser = ['Alle raser']
            if 'Rase' in hmi_data.columns:
                unike_raser += sorted(list(hmi_data['Rase'].dropna().unique()))

            velg_rase = st.sidebar.selectbox('Velg rase:', unike_raser, index=0)

            # --- FILTRERING ---
            temp_df = hmi_data.copy()
            if velg_rase != 'Alle raser':
                temp_df = temp_df[temp_df['Rase'] == velg_rase]
            if sok_verdi:
                temp_df = temp_df[temp_df['Oremerke'].astype(str).str.contains(sok_verdi)]

            # VIKTIG: Kun aktive dyr vurderes som potensielle livdyr
            aktive_df = temp_df[temp_df['Status'].astype(str).str.lower() == 'aktiv']

            vekt_kriterium = (aktive_df['Kjoenn'].astype(str).str.lower().str.startswith('s')) & (aktive_df['Estimert vekt 90 dager'] >= grense_livdyr)
            indeks_kriterium = (aktive_df['Indeks'].isna()) | (aktive_df['Indeks'] >= min_indeks)

            elite_df = aktive_df[vekt_kriterium & indeks_kriterium].sort_values('Estimert vekt 90 dager', ascending=False)
            t56_df = temp_df[temp_df['Estimert vekt 56 dager'] < grense_56].sort_values('Estimert vekt 56 dager')
            t90_df = temp_df[temp_df['Estimert vekt 90 dager'] < grense_90].sort_values('Estimert vekt 90 dager')

            # --- FANER ---
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "🌟 Potensielle Livdyr",
                "⚠️ Tiltak 56 dager",
                "🚨 Tiltak 90 dager",
                "📈 Effektivitetsanalyse",
                "📊 Tilvekstkurve (Reell)",
                "📈 Tilvekstkurve (Estimert)"
            ])

            cols_to_show = ['Oremerke', 'Kjoenn', 'Rase', 'Indeks', 'Daglig tilvekst (g)', 'Estimert vekt 56 dager', 'Estimert vekt 90 dager', 'Status']

            with tab1:
                st.subheader(f"Potensielle Aktive Livdyr (90d >= {grense_livdyr} kg, indeks >= {min_indeks})")
                st.dataframe(elite_df[cols_to_show], use_container_width=True, hide_index=True)

            with tab2:
                st.subheader(f"Lam med estimert 56-dagersvekt < {grense_56} kg (Antall: {len(t56_df)})")
                st.dataframe(t56_df[cols_to_show], use_container_width=True, hide_index=True)

            with tab3:
                st.subheader(f"Lam med estimert 90-dagersvekt < {grense_90} kg (Antall: {len(t90_df)})")
                st.dataframe(t90_df[cols_to_show], use_container_width=True, hide_index=True)

            with tab4:
                st.subheader("Slakteresultater og nøyaktig utbytteprosent basert på estimert slaktevekt på leveringsdagen")
                effekt_df = temp_df[temp_df['Slaktevekt (kg)'].notna() & (temp_df['Slaktevekt (kg)'] > 0)].copy()
                if not effekt_df.empty:
                    vis_effekt = ['Oremerke', 'Kjoenn', 'Rase', 'Slaktealder (dager)', 'Est. levendevekt slakt (kg)', 'Slaktevekt (kg)', 'Slakteprosent (%)', 'Status']
                    st.dataframe(effekt_df[vis_effekt].sort_values('Slakteprosent (%)', ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.info("Ingen registrerte slakteoppgjør funnet i basisinfo-filen.")

            with tab5:
                st.subheader("Reelle målinger over tid")
                if not long_data_reell.empty:
                    fig, ax = plt.subplots(figsize=(10, 5))
                    p_df = long_data_reell.copy()
                    if velg_rase != 'Alle raser':
                        p_df = p_df[p_df['Rase'] == velg_rase]
                    if sok_verdi:
                        p_df = p_df[p_df['Oremerke'].astype(str).str.contains(sok_verdi)]

                    if not p_df.empty:
                        sns.scatterplot(data=p_df, x='Alder', y='Vekt', hue='Kjoenn', alpha=0.7, ax=ax)
                        
                        # Lag kurver og skyggeområde
                        x_vals = np.array([0, max(p_df['Alder']) if len(p_df) > 0 else 100])
                        ax.plot(x_vals, 4.5 + 0.300 * x_vals, color='green', linestyle='--', alpha=0.8, label='300 g/dag')
                        
                        grense_tilvekst_dgl_90 = (grense_90 - 4.5) / 90.0
                        ax.plot(x_vals, 4.5 + grense_tilvekst_dgl_90 * x_vals, color='red', linestyle='--', alpha=0.8, label=f'Kritisk grense ({round(grense_tilvekst_dgl_90*1000)} g/dag)')
                        ax.fill_between(x_vals, 0, 4.5 + grense_tilvekst_dgl_90 * x_vals, color='red', alpha=0.08, label='Tiltakssone')
                        
                        ax.set_xlim(-5, max(p_df['Alder']) + 5)
                        ax.set_ylim(0, max(p_df['Vekt']) + 5)
                        ax.grid(True, linestyle=':', alpha=0.6)
                        ax.legend(loc='upper left')
                        st.pyplot(fig)

            with tab6:
                st.subheader("Standardisert kurve ved 56 og 90 dager")
                fig, ax = plt.subplots(figsize=(10, 5))
                est_recs = []
                for _, r in temp_df.iterrows():
                    est_recs.append({'Oremerke': r['Oremerke'], 'Kjoenn': r['Kjoenn'], 'Alder': 56, 'Vekt': r['Estimert vekt 56 dager']})
                    est_recs.append({'Oremerke': r['Oremerke'], 'Kjoenn': r['Kjoenn'], 'Alder': 90, 'Vekt': r['Estimert vekt 90 dager']})

                if est_recs:
                    est_df = pd.DataFrame(est_recs)
                    sns.scatterplot(data=est_df, x='Alder', y='Vekt', hue='Kjoenn', s=60, ax=ax)
                    
                    # Tegn referanselinjer for standardiserte punkter
                    x_vals_est = np.array([0, 105])
                    ax.plot(x_vals_est, 4.5 + 0.300 * x_vals_est, color='green', linestyle='--', alpha=0.8, label='300 g/dag')
                    
                    grense_tilvekst_dgl_90 = (grense_90 - 4.5) / 90.0
                    ax.plot(x_vals_est, 4.5 + grense_tilvekst_dgl_90 * x_vals_est, color='red', linestyle='--', alpha=0.8, label='Kritisk grense')
                    
                    ax.axvline(x=56, color='gray', linestyle=':')
                    ax.axvline(x=90, color='gray', linestyle=':')
                    
                    rect_56 = patches.Rectangle((53, 0), 6, grense_56, linewidth=1, edgecolor='red', facecolor='red', alpha=0.15)
                    rect_90 = patches.Rectangle((87, 0), 6, grense_90, linewidth=1, edgecolor='red', facecolor='red', alpha=0.15, label='Tiltakssone')
                    ax.add_patch(rect_56)
                    ax.add_patch(rect_90)
                    
                    ax.set_xlim(0, 105)
                    ax.set_ylim(0, max(est_df['Vekt']) + 5 if not est_df.empty else 50)
                    ax.grid(True, linestyle=':', alpha=0.6)
                    ax.legend(loc='upper left')
                    st.pyplot(fig)

    except Exception as e:
        st.error(f"Feil under prosessering av data: {e}")
else:
    st.info("👈 Last opp vektfilen (tilvekstAlleRapport.xls) i venstremenyen for å starte.")
