import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patches as patches
import openpyxl
from openpyxl.drawing.image import Image as OpenpyxlImage

# Sett opp nettleser-fanen
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
        return float(val.replace(',', '.'))
    try:
        return float(val)
    except:
        return np.nan

# --- STRUKTURERING AV DATA ---
def prosesser_data(df_raw):
    df_raw['F.vekt'] = df_raw['F.vekt'].apply(clean_weight)
    df_raw['Dato f.vekt'] = pd.to_datetime(df_raw['Dato f.vekt'], format='%d/%m/%y', errors='coerce')

    resultater = []
    reelle_registreringer = []

    for index, row in df_raw.iterrows():
        if pd.isna(row['Dato f.vekt']): 
            continue

        fødselsvekt = row['F.vekt']
        if pd.isna(fødselsvekt): 
            fødselsvekt = 4.5

        lamb_id = row['Øremrk']
        gender = row['Kjønn']
        rase = row['Rase'] if 'Rase' in row and pd.notna(row['Rase']) else 'Ukjent'
        birth_date = row['Dato f.vekt']

        # Fødselsvekt som reell registrering
        reelle_registreringer.append({
            'Øremerke': lamb_id, 'Kjønn': gender, 'Rase': rase, 'Alder': 0, 'Vekt': fødselsvekt
        })

        siste_vekt = np.nan
        alder_siste_vekt = 0

        for i in range(1, 8):
            date_col = f'Dato {i}'
            vekt_col = f'Vekt {i}'
            if date_col in row and pd.notna(row[date_col]):
                veiedato = pd.to_datetime(row[date_col], format='%d/%m/%y', errors='coerce')
                vekt = clean_weight(row[vekt_col])
                if pd.notna(veiedato) and pd.notna(vekt):
                    alder = (veiedato - birth_date).days
                    if alder > 0:
                        reelle_registreringer.append({
                            'Øremerke': lamb_id, 'Kjønn': gender, 'Rase': rase, 'Alder': alder, 'Vekt': vekt
                        })
                        siste_vekt = vekt
                        alder_siste_vekt = alder

        if alder_siste_vekt > 0:
            daglig_tilvekst_kg = (siste_vekt - fødselsvekt) / alder_siste_vekt
            vekt_56 = fødselsvekt + (daglig_tilvekst_kg * 56)
            vekt_90 = fødselsvekt + (daglig_tilvekst_kg * 90)

            resultater.append({
                'Øremerke': lamb_id,
                'Kjønn': gender,
                'Rase': rase,
                'Daglig tilvekst (g)': round(daglig_tilvekst_kg * 1000),
                'Estimert vekt 56 dager': round(vekt_56, 1),
                'Estimert vekt 90 dager': round(vekt_90, 1)
            })

    return pd.DataFrame(resultater), pd.DataFrame(reelle_registreringer)

# --- PLOTTING FOR NETTSIDE & EXCEL ---
def generer_plott(reell_df, temp_df, rase_valg, sok_valg, g_56, g_90, g_livdyr, reell=True):
    fig, ax = plt.subplots(figsize=(10, 5.5))
    
    if reell:
        if not reell_df.empty:
            plot_df = reell_df.copy()
            if rase_valg != 'Alle raser':
                plot_df = plot_df[plot_df['Rase'] == rase_valg]
            if sok_valg:
                plot_df = plot_df[plot_df['Øremerke'].astype(str).str.contains(sok_valg)]

            if not plot_df.empty:
                sns.scatterplot(data=plot_df, x='Alder', y='Vekt', hue='Kjønn', alpha=0.6, s=40,
                                palette={'Søye': 'blue', 'Vær': 'orange'}, ax=ax)
                x_vals = np.array([0, max(plot_df['Alder']) if len(plot_df) > 0 else 100])
                ax.plot(x_vals, 4.5 + 0.400 * x_vals, color='gold', linestyle='--', alpha=0.6, label='400 g/dag')
                ax.plot(x_vals, 4.5 + 0.300 * x_vals, color='green', linestyle='--', alpha=0.6, label='300 g/dag')
                ax.plot(x_vals, 4.5 + 0.200 * x_vals, color='red', linestyle='--', alpha=0.6, label='200 g/dag')
                ax.axvline(x=56, color='gray', linestyle=':', alpha=0.5)
                ax.axvline(x=90, color='gray', linestyle=':', alpha=0.5)
                ax.scatter([56], [g_56], color='red', marker='X', s=100, label=f'Gjeldende grense (56d): {g_56}kg')
                ax.scatter([90], [g_90], color='darkred', marker='X', s=100, label=f'Gjeldende grense (90d): {g_90}kg')
                ax.set_title(f'Reell tilvekstkurve - {rase_valg} (Faktiske vekter)', fontsize=12)
                ax.set_xlabel('Alder (dager)', fontsize=10)
                ax.set_ylabel('Reell Vekt (kg)', fontsize=10)
                ax.grid(True, linestyle='--', alpha=0.4)
                ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        else:
            ax.text(0.5, 0.5, 'Ingen reelle data tilgjengelig', ha='center')
    else:
        if not temp_df.empty:
            est_records = []
            for _, row_lam in temp_df.iterrows():
                est_records.append({'Øremerke': row_lam['Øremerke'], 'Kjønn': row_lam['Kjønn'], 'Alder': 56, 'Estimert Vekt': row_lam['Estimert vekt 56 dager']})
                est_records.append({'Øremerke': row_lam['Øremerke'], 'Kjønn': row_lam['Kjønn'], 'Alder': 90, 'Estimert Vekt': row_lam['Estimert vekt 90 dager']})
            est_plot_df = pd.DataFrame(est_records)

            if not est_plot_df.empty:
                sns.scatterplot(data=est_plot_df, x='Alder', y='Estimert Vekt', hue='Kjønn', alpha=0.6, s=50,
                                palette={'Søye': 'blue', 'Vær': 'orange'}, ax=ax)
                x_vals_est = np.array([0, 105])
                ax.plot(x_vals_est, 4.5 + 0.400 * x_vals_est, color='gold', linestyle='--', alpha=0.6, label='400 g/dag')
                ax.plot(x_vals_est, 4.5 + 0.300 * x_vals_est, color='green', linestyle='--', alpha=0.6, label='300 g/dag')
                ax.plot(x_vals_est, 4.5 + 0.200 * x_vals_est, color='red', linestyle='--', alpha=0.6, label='200 g/dag')
                ax.axvline(x=56, color='gray', linestyle=':', alpha=0.5)
                ax.axvline(x=90, color='gray', linestyle=':', alpha=0.5)
                ax.scatter([56], [g_56], color='red', marker='X', s=120, zorder=5, label=f'Grense 56d: {g_56} kg')
                ax.scatter([90], [g_90], color='darkred', marker='X', s=120, zorder=5, label=f'Grense 90d: {g_90} kg')
                
                rect_56 = patches.Rectangle((53, 0), 6, g_56, linewidth=1, edgecolor='red', facecolor='red', alpha=0.1)
                rect_90 = patches.Rectangle((87, 0), 6, g_90, linewidth=1, edgecolor='red', facecolor='red', alpha=0.1, label='Tiltakssone')
                ax.add_patch(rect_56)
                ax.add_patch(rect_90)
                
                ax.set_title(f'Standardisert Tilvekstkurve - {rase_valg} (Estimerte vekter)', fontsize=12)
                ax.set_xlabel('Alder (Standardisert dager)', fontsize=10)
                ax.set_ylabel('Estimert Vekt (kg)', fontsize=10)
                ax.set_xlim(0, 105)
                ax.set_ylim(0, max(est_plot_df['Estimert Vekt']) + 5 if len(est_plot_df) > 0 else 50)
                ax.grid(True, linestyle='--', alpha=0.4)
                ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        else:
            ax.text(0.5, 0.5, 'Ingen estimerte data tilgjengelig', ha='center')
            
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

# --- STRIP INTERNETTSIDETITTEL ---
st.title("🐑 Interaktivt Tilvekstdashbord")
st.markdown("Last opp din Sauekontroll-rapport for å analysere, visualisere tilvekst og eksportere fiks ferdige rapporter med grafer.")

# --- SIDEPANEL: KONTROLLER ---
st.sidebar.header("⚙️ Instillinger")
uploaded_file = st.sidebar.file_uploader("Last opp Sauekontroll-rapport (Excel)", type=["xls", "xlsx"])

grense_livdyr = st.sidebar.slider('Min. vekt Livdyr (90 dager):', 20.0, 40.0, 30.0, step=0.5)
grense_56 = st.sidebar.slider('Tiltak Vekt (56 dager):', 5.0, 25.0, 15.0, step=0.5)
grense_90 = st.sidebar.slider('Tiltak Vekt (90 dager):', 10.0, 30.0, 17.0, step=0.5)

sok_verdi = st.sidebar.text_input('Søk på øremerke:', value="").strip()

# --- HOVEDSKJERM LOGIKK ---
if uploaded_file is not None:
    try:
        # Les inn Excel dynamisk
        xl = pd.ExcelFile(uploaded_file)
        sheet_to_read = 'Export' if 'Export' in xl.sheet_names else xl.sheet_names[0]
        raw_df = xl.parse(sheet_to_read)

        # Prosesser
        hmi_data, long_data_reell = prosesser_data(raw_df)

        # Rase-filter i sidepanelet basert på faktiske raser i dokumentet
        unike_raser = ['Alle raser']
        if not hmi_data.empty and 'Rase' in hmi_data.columns:
            unike_raser += sorted(list(hmi_data['Rase'].dropna().unique()))
        
        velg_rase = st.sidebar.selectbox('Velg rase:', unike_raser, index=0)

        # --- FILTRERING ---
        temp_df = hmi_data.copy()
        if velg_rase != 'Alle raser':
            temp_df = temp_df[temp_df['Rase'] == velg_rase]
        if sok_verdi:
            temp_df = temp_df[temp_df['Øremerke'].astype(str).str.contains(sok_verdi)]

        # Del opp tabellene
        elite_df = temp_df[(temp_df['Kjønn'] == 'Søye') & (temp_df['Estimert vekt 90 dager'] >= grense_livdyr)].sort_values('Estimert vekt 90 dager', ascending=False)
        t56_df = temp_df[temp_df['Estimert vekt 56 dager'] < grense_56].sort_values('Estimert vekt 56 dager')
        t90_df = temp_df[temp_df['Estimert vekt 90 dager'] < grense_90].sort_values('Estimert vekt 90 dager')

        # --- EXCEL EKSPORT GENERERING ---
        def lag_excel_rapport():
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Lagre dataark
                kolonne_rekkefolge = ['Øremerke', 'Kjønn', 'Rase', 'Daglig tilvekst (g)', 'Estimert vekt 56 dager', 'Estimert vekt 90 dager']
                elite_df[kolonne_rekkefolge].to_excel(writer, sheet_name='Potensielle Livdyr', index=False)
                t56_df[kolonne_rekkefolge].to_excel(writer, sheet_name='Tiltak 56 dager', index=False)
                t90_df[kolonne_rekkefolge].to_excel(writer, sheet_name='Tiltak 90 dager', index=False)

                # Opprett ark for grafer
                workbook = writer.book
                worksheet = workbook.create_sheet(title='Grafiske Vekstkurver')

                # Generer bilder
                img_reell_buf = generer_plott(long_data_reell, temp_df, velg_rase, sok_verdi, grense_56, grense_90, grense_livdyr, reell=True)
                img_est_buf = generer_plott(long_data_reell, temp_df, velg_rase, sok_verdi, grense_56, grense_90, grense_livdyr, reell=False)

                img_reell = OpenpyxlImage(img_reell_buf)
                img_est = OpenpyxlImage(img_est_buf)

                worksheet.column_dimensions['B'].width = 15
                worksheet['B2'] = "REELLE VEKSTKURVER (FAKTISKE VEKTER)"
                worksheet['B2'].font = openpyxl.styles.Font(bold=True, size=12)
                worksheet.add_image(img_reell, 'B4')

                worksheet['B32'] = "ESTIMERTE TILVEKSTKURVER (STANDARDISERT)"
                worksheet['B32'].font = openpyxl.styles.Font(bold=True, size=12)
                worksheet.add_image(img_est, 'B34')

            excel_buffer.seek(0)
            return excel_buffer.getvalue()

        # Knapp for eksport av Excel i sidepanelet
        st.sidebar.markdown("--- ")
        excel_data = lag_excel_rapport()
        st.sidebar.download_button(
            label="📥 Eksport data",
            data=excel_data,
            file_name="tilvekst_filtrert_rapport.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # --- FANER PÅ SKJERMEN ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🌟 Potensielle Livdyr", 
            "⚠️ Tiltak 56 dager", 
            "🚨 Tiltak 90 dager", 
            "📈 Tilvekstkurve (Reell)", 
            "📊 Tilvekstkurve (Estimert)"
        ])

        with tab1:
            st.subheader(f"Søyer med estimert 90-dagersvekt >= {grense_livdyr} kg (Antall: {len(elite_df)})")
            st.dataframe(elite_df, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader(f"Lam med estimert 56-dagersvekt < {grense_56} kg (Antall: {len(t56_df)})")
            st.dataframe(t56_df, use_container_width=True, hide_index=True)

        with tab3:
            st.subheader(f"Lam med estimert 90-dagersvekt < {grense_90} kg (Antall: {len(t90_df)})")
            st.dataframe(t90_df, use_container_width=True, hide_index=True)

        with tab4:
            st.subheader("Reelle vekstkurver (Faktiske registreringer over tid)")
            img_reell_display = generer_plott(long_data_reell, temp_df, velg_rase, sok_verdi, grense_56, grense_90, grense_livdyr, reell=True)
            st.image(img_reell_display)

        with tab5:
            st.subheader("Standardiserte vekstkurver (Estimert vekt ved nøyaktig 56 og 90 dager)")
            img_est_display = generer_plott(long_data_reell, temp_df, velg_rase, sok_verdi, grense_56, grense_90, grense_livdyr, reell=False)
            st.image(img_est_display)

    except Exception as e:
        st.error(f"Noe gikk galt under innlesing og prosessering: {e}")
else:
    st.info("👈 Last opp en Excel-rapport fra Sauekontrollen i venstremenyen for å begynne!")
