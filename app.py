import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import pandas as pd
import numpy as np
import io
import os
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patches as patches

# Globale data som oppdateres ved opplasting eller automatisk innlesing
hmi_data = pd.DataFrame()
long_data_reell = pd.DataFrame()
snitt_fvekt_beregnet = 5.0

# Globale rådataframes fra de to kildene
df_vekter_raw = pd.DataFrame()
df_basis_raw = pd.DataFrame()

# Opprett interaktive kontroller (Widgets)
style = {'description_width': 'initial'}

uploader_vekter = widgets.FileUpload(
    accept='.xls,.xlsx',
    multiple=False,
    description='1. Last opp vekter',
    button_style='info',
    icon='upload'
)

uploader_basis = widgets.FileUpload(
    accept='.xls,.xlsx',
    multiple=False,
    description='2. Last opp basisinfo (Rase/Indeks/Slakt)',
    button_style='info',
    icon='upload'
)

slider_elite_90 = widgets.FloatSlider(value=30.0, min=15.0, max=45.0, step=0.5, description='Grense Livdyr (90d):', style=style)
slider_min_indeks = widgets.IntSlider(value=100, min=80, max=150, step=1, description='Minste avlsindeks:', style=style)
slider_tiltak_56 = widgets.FloatSlider(value=15.0, min=5.0, max=25.0, step=0.5, description='Kritisk grense (56d):', style=style)
slider_tiltak_90 = widgets.FloatSlider(value=17.0, min=10.0, max=30.0, step=0.5, description='Kritisk grense (90d):', style=style)
sok_oremerke = widgets.Text(value='', placeholder='Søk på øremerke...', description='Søk lam:', style=style)

velg_rase = widgets.Dropdown(
    options=['Alle raser'],
    value='Alle raser',
    description='Filtrer på rase:',
    style=style
)

status_output = widgets.Output()
out = widgets.Output()

def clean_weight(val):
    if pd.isna(val): return np.nan
    if isinstance(val, str):
        val = val.replace(',', '.')
    try: return float(val)
    except: return np.nan

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

def flett_og_analyser():
    global hmi_data, long_data_reell, df_vekter_raw, df_basis_raw, snitt_fvekt_beregnet

    if df_vekter_raw.empty:
        with status_output:
            clear_output()
            print("⚠️ Vekt-filen (tilvekstAlleRapport.xls) er ikke lastet inn ennå. Vennligst last den opp ovenfor.")
        return

    # Klargjør vekt-dataframe
    v_cols = df_vekter_raw.columns
    col_v_id = finn_kolonne(v_cols, ['øremrk', 'øremerke', 'ind.nr', 'id', 'øremerke_nr'])
    col_v_kjoenn = finn_kolonne(v_cols, ['kjønn', 'kjoenn', 'k'])
    col_v_fvekt = finn_kolonne(v_cols, ['f.vekt', 'f-vekt', 'fødselsvekt', 'fødtvekt'])
    col_v_fodselsdato = finn_kolonne(v_cols, ['dato f.vekt', 'fødselsdato', 'fødtdato', 'født_dato'])

    if not col_v_id:
        with status_output:
            clear_output()
            print("❌ Kunne ikke identifisere ID-kolonne (f.eks. 'Øremrk') i vektfilen.")
        return

    # Beregn gjennomsnittlig fødselsvekt
    registrerte_fvekter = []
    if col_v_fvekt:
        for val in df_vekter_raw[col_v_fvekt]:
            fv_renset = clean_weight(val)
            if pd.notna(fv_renset) and fv_renset > 0:
                registrerte_fvekter.append(fv_renset)

    snitt_fvekt_beregnet = np.mean(registrerte_fvekter) if registrerte_fvekter else 5.0
    if pd.isna(snitt_fvekt_beregnet) or snitt_fvekt_beregnet <= 0:
        snitt_fvekt_beregnet = 5.0

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

    hmi_data = pd.DataFrame(resultater)
    long_data_reell = pd.DataFrame(reelle_registreringer)

    if not hmi_data.empty and 'Rase' in hmi_data.columns:
        unike_raser = sorted(list(hmi_data['Rase'].dropna().unique()))
        velg_rase.options = ['Alle raser'] + [r for r in unike_raser if r != 'nan']

    with status_output:
        clear_output()
        print(f"✅ Analyse fullført for {len(hmi_data)} lam!")

    oppdater_hmi()

def last_vekter(change):
    global df_vekter_raw
    if not uploader_vekter.value: return
    try:
        uploaded_file = list(uploader_vekter.value.values())[0]
        df_vekter_raw = pd.ExcelFile(io.BytesIO(uploaded_file['content'])).parse()
        flett_og_analyser()
    except Exception as e:
        with status_output: print(f"❌ Feil ved lesing av opplastet vektfil: {e}")

def last_basis(change):
    global df_basis_raw
    if not uploader_basis.value: return
    try:
        uploaded_file = list(uploader_basis.value.values())[0]
        df_basis_raw = pd.ExcelFile(io.BytesIO(uploaded_file['content'])).parse()
        flett_og_analyser()
    except Exception as e:
        with status_output: print(f"❌ Feil ved lesing av opplastet basisinfo: {e}")

def auto_last_lokale_filer():
    global df_vekter_raw, df_basis_raw
    status_msgs = []

    vekt_stier = ['/content/tilvekstAlleRapport.xls', 'tilvekstAlleRapport.xls']
    vekt_suksess = False
    for vs in vekt_stier:
        if os.path.exists(vs):
            try:
                xl = pd.ExcelFile(vs)
                sheet = 'Export' if 'Export' in xl.sheet_names else xl.sheet_names[0]
                df_vekter_raw = xl.parse(sheet)
                status_msgs.append(f"✓ Vektfil '{vs}' lastet.")
                vekt_suksess = True
                break
            except Exception as e:
                status_msgs.append(f"⚠️ Feil med '{vs}': {e}")

    basis_stier = [
        '/content/sau-besetning (22).xlsx',
        'sau-besetning (22).xlsx'
    ]
    basis_suksess = False
    for bs in basis_stier:
        if os.path.exists(bs):
            try:
                xl = pd.ExcelFile(bs)
                sheet = 'Sauekontrollen' if 'Sauekontrollen' in xl.sheet_names else xl.sheet_names[0]
                df_basis_raw = xl.parse(sheet)
                status_msgs.append(f"✓ Basisfil '{bs}' lastet.")
                basis_suksess = True
                break
            except Exception as e:
                status_msgs.append(f"⚠️ Feil med '{bs}': {e}")

    with status_output:
        clear_output()
        for msg in status_msgs: print(msg)

    if vekt_suksess:
        flett_og_analyser()

def hent_filtrerte_tabeller():
    if hmi_data.empty:
        return None, None, None, pd.DataFrame()

    temp_df = hmi_data.copy()
    rase_verdi = velg_rase.value
    sok_verdi = sok_oremerke.value.strip()

    if rase_verdi != 'Alle raser':
        temp_df = temp_df[temp_df['Rase'] == rase_verdi]
    if sok_verdi:
        temp_df = temp_df[temp_df['Oremerke'].astype(str).str.contains(sok_verdi)]

    aktive_lam_df = temp_df[temp_df['Status'].astype(str).str.lower() == 'aktiv']
    vekt_kriterium = (aktive_lam_df['Kjoenn'].astype(str).str.lower().str.startswith('s')) & (aktive_lam_df['Estimert vekt 90 dager'] >= slider_elite_90.value)
    indeks_kriterium = (aktive_lam_df['Indeks'].isna()) | (aktive_lam_df['Indeks'] >= slider_min_indeks.value)

    elite = aktive_lam_df[vekt_kriterium & indeks_kriterium].sort_values('Estimert vekt 90 dager', ascending=False)
    tiltak_56 = temp_df[temp_df['Estimert vekt 56 dager'] < slider_tiltak_56.value].sort_values('Estimert vekt 56 dager')
    tiltak_90 = temp_df[temp_df['Estimert vekt 90 dager'] < slider_tiltak_90.value].sort_values('Estimert vekt 90 dager')

    kolonner = ['Oremerke', 'Kjoenn', 'Rase', 'Indeks', 'Daglig tilvekst (g)', 'Estimert vekt 56 dager', 'Estimert vekt 90 dager', 'Status', 'Slaktevekt (kg)', 'Nettopris (kr)', 'Slakteprosent (%)']
    return elite[kolonner], tiltak_56[kolonner], tiltak_90[kolonner], temp_df

def oppdater_hmi(*args):
    with out:
        clear_output(wait=True)
        if hmi_data.empty:
            print("Venter på opplasting eller automatisk innlesing av filer...")
            return

        elite, tiltak_56, tiltak_90, temp_df = hent_filtrerte_tabeller()

        def til_stylet_html(df, show_slaughter_perc=False):
            df_copy = df.copy()
            if 'Indeks' in df_copy.columns:
                df_copy['Indeks'] = df_copy['Indeks'].apply(lambda x: '' if pd.isna(x) else str(int(x)) if isinstance(x, (int, float)) and x.is_integer() else str(x))
            for numeric_col in ['Slaktevekt (kg)', 'Nettopris (kr)', 'Slakteprosent (%)', 'Est. levendevekt slakt (kg)', 'Slaktealder (dager)']:
                if numeric_col in df_copy.columns:
                    if numeric_col == 'Slakteprosent (%)':
                        df_copy[numeric_col] = df_copy[numeric_col].apply(lambda x: '' if pd.isna(x) else f"{x:.1f} %")
                    elif numeric_col == 'Slaktealder (dager)':
                        df_copy[numeric_col] = df_copy[numeric_col].apply(lambda x: '' if pd.isna(x) else f"{int(x)} dgr")
                    elif numeric_col == 'Est. levendevekt slakt (kg)':
                        df_copy[numeric_col] = df_copy[numeric_col].apply(lambda x: '' if pd.isna(x) else f"{x:.1f} kg")
                    else:
                        df_copy[numeric_col] = df_copy[numeric_col].apply(lambda x: '' if pd.isna(x) else f"{x:.1f}" if numeric_col == 'Slaktevekt (kg)' else f"{int(x)}:-")
            if not show_slaughter_perc and 'Slakteprosent (%)' in df_copy.columns:
                df_copy = df_copy.drop(columns=['Slakteprosent (%)'])

            html_rows = []
            for _, row in df_copy.iterrows():
                status_str = str(row['Status'])
                er_utmeldt = (status_str.lower() != 'aktiv') and (status_str.lower() != 'nan') and (status_str != '')
                row_vals = row.to_dict()
                if er_utmeldt:
                    row_vals['Oremerke'] = f"<span style='color: #c0392b; font-weight: bold;'>{row['Oremerke']}</span>"
                    row_vals['Status'] = f"<span style='color: #c0392b;'>{status_str}</span>"
                else:
                    row_vals['Oremerke'] = f"<b>{row['Oremerke']}</b>"
                    row_vals['Status'] = f"<span style='color: #27ae60;'>Aktiv</span>"
                html_rows.append(row_vals)

            df_html = pd.DataFrame(html_rows)
            return df_html.to_html(index=False, escape=False, classes='table table-striped')

        tab_innhold = []

        out_elite = widgets.Output()
        with out_elite:
            display(HTML(til_stylet_html(elite)))
        tab_innhold.append(out_elite)

        out_56 = widgets.Output()
        with out_56:
            display(HTML(til_stylet_html(tiltak_56)))
        tab_innhold.append(out_56)

        out_90 = widgets.Output()
        with out_90:
            display(HTML(til_stylet_html(tiltak_90)))
        tab_innhold.append(out_90)

        out_effekt = widgets.Output()
        with out_effekt:
            effekt_df = temp_df[temp_df['Slaktevekt (kg)'].notna() & (temp_df['Slaktevekt (kg)'] > 0)].copy()
            effekt_df = effekt_df.sort_values('Slakteprosent (%)', ascending=False)
            if not effekt_df.empty:
                vis_kolonner = ['Oremerke', 'Kjoenn', 'Rase', 'Slaktealder (dager)', 'Est. levendevekt slakt (kg)', 'Slaktevekt (kg)', 'Slakteprosent (%)', 'Status']
                display(HTML(til_stylet_html(effekt_df[vis_kolonner], show_slaughter_perc=True)))
        tab_innhold.append(out_effekt)

        out_plot = widgets.Output()
        with out_plot:
            if not long_data_reell.empty:
                p_df = long_data_reell.copy()
                if velg_rase.value != 'Alle raser': p_df = p_df[p_df['Rase'] == velg_rase.value]
                if sok_oremerke.value: p_df = p_df[p_df['Oremerke'].astype(str).str.contains(sok_oremerke.value)]

                if not p_df.empty:
                    plt.figure(figsize=(11, 5.5))
                    grense_tilvekst_dgl = (slider_tiltak_90.value - snitt_fvekt_beregnet) / 90.0
                    if grense_tilvekst_dgl < 0: grense_tilvekst_dgl = 0.100
                    p_df['Er_Kritisk'] = p_df['Vekt'] < (snitt_fvekt_beregnet + grense_tilvekst_dgl * p_df['Alder'])

                    normal_df = p_df[~p_df['Er_Kritisk']]
                    if not normal_df.empty:
                        sns.scatterplot(data=normal_df, x='Alder', y='Vekt', hue='Kjoenn', alpha=0.7, s=45)

                    kritisk_df = p_df[p_df['Er_Kritisk']]
                    if not kritisk_df.empty:
                        plt.scatter(kritisk_df['Alder'], kritisk_df['Vekt'], color='darkred', marker='X', s=70, label='Under kritisk tilvekst', zorder=4)

                    x_max = max(p_df['Alder']) if len(p_df) > 0 else 100
                    x_vals = np.array([0, x_max])

                    plt.plot(x_vals, snitt_fvekt_beregnet + 0.3 * x_vals, 'g--', label='300 g/dag')
                    plt.plot(x_vals, snitt_fvekt_beregnet + grense_tilvekst_dgl * x_vals, 'r--', label=f'Kritisk grense')
                    plt.fill_between(x_vals, 0, snitt_fvekt_beregnet + grense_tilvekst_dgl * x_vals, color='red', alpha=0.08, label='Tiltakssone')

                    plt.title('Reell tilvekstkurve')
                    plt.xlabel('Alder (dager)')
                    plt.ylabel('Vekt (kg)')
                    plt.xlim(-5, x_max + 5)
                    plt.ylim(0, max(p_df['Vekt']) + 5)
                    plt.grid(True, linestyle=':', alpha=0.6)
                    plt.legend(loc='upper left')
                    plt.show()
        tab_innhold.append(out_plot)

        out_est = widgets.Output()
        with out_est:
            if not temp_df.empty:
                est_recs = []
                for _, r in temp_df.iterrows():
                    est_recs.append({'Oremerke': r['Oremerke'], 'Kjoenn': r['Kjoenn'], 'Alder': 56, 'Vekt': r['Estimert vekt 56 dager']})
                    est_recs.append({'Oremerke': r['Oremerke'], 'Kjoenn': r['Kjoenn'], 'Alder': 90, 'Vekt': r['Estimert vekt 90 dager']})
                est_df = pd.DataFrame(est_recs)

                plt.figure(figsize=(11, 5.5))
                sns.scatterplot(data=est_df, x='Alder', y='Vekt', hue='Kjoenn', alpha=0.7, s=60)
                plt.axvline(x=56, color='gray', linestyle=':')
                plt.axvline(x=90, color='gray', linestyle=':')

                x_vals_est = np.array([0, 105])
                plt.plot(x_vals_est, snitt_fvekt_beregnet + 0.300 * x_vals_est, color='green', linestyle='--', alpha=0.8, label='300 g/dag')

                grense_tilvekst_dgl_90 = (slider_tiltak_90.value - snitt_fvekt_beregnet) / 90.0
                plt.plot(x_vals_est, snitt_fvekt_beregnet + grense_tilvekst_dgl_90 * x_vals_est, color='red', linestyle='--', alpha=0.8, label='Kritisk grense')

                rect_56 = patches.Rectangle((53, 0), 6, slider_tiltak_56.value, linewidth=1, edgecolor='red', facecolor='red', alpha=0.15)
                rect_90 = patches.Rectangle((87, 0), 6, slider_tiltak_90.value, linewidth=1, edgecolor='red', facecolor='red', alpha=0.15, label='Kritisk sone')
                plt.gca().add_patch(rect_56)
                plt.gca().add_patch(rect_90)

                plt.title('Standardisert tilvekstkurve (Estimerte vekter)')
                plt.xlabel('Alder (dager)')
                plt.ylabel('Vekt (kg)')
                plt.grid(True, linestyle=':', alpha=0.6)
                plt.legend()
                plt.show()
        tab_innhold.append(out_est)

        tabs = widgets.Tab(children=tab_innhold)
        tabs.set_title(0, '🌟 Potensielle Livdyr')
        tabs.set_title(1, '⚠️ Tiltak 56 dager')
        tabs.set_title(2, '🚨 Tiltak 90 dager')
        tabs.set_title(3, '📈 Effektivitetsanalyse')
        tabs.set_title(4, '📈 Tilvekstkurve (Reell)')
        tabs.set_title(5, '📊 Tilvekstkurve (Estimert)')
        display(tabs)

# Registrer lyttere
uploader_vekter.observe(last_vekter, names='value')
uploader_basis.observe(last_basis, names='value')
slider_elite_90.observe(oppdater_hmi, names='value')
slider_min_indeks.observe(oppdater_hmi, names='value')
slider_tiltak_56.observe(oppdater_hmi, names='value')
slider_tiltak_90.observe(oppdater_hmi, names='value')
sok_oremerke.observe(oppdater_hmi, names='value')
velg_rase.observe(oppdater_hmi, names='value')

# Layout
kontroll_boks = widgets.VBox([
    widgets.HTML("<h3>⚙️ Last opp data (Fletting med slakt- og utmeldingsdata)</h3>"),
    widgets.HBox([uploader_vekter, uploader_basis]),
    widgets.HBox([sok_oremerke, velg_rase]),
    widgets.HBox([slider_elite_90, slider_min_indeks, slider_tiltak_56, slider_tiltak_90])
], layout=widgets.Layout(border='1px solid #ccc', padding='10px', margin='10px 0', border_radius='5px'))

clear_output(wait=True)
display(widgets.HTML("<h2>∞ Interaktivt Flettingsdashbord (Vekter + Slaktedata)</h2>"))
display(kontroll_boks)
display(status_output)
display(out)

# Sjekk lokale filer automatisk ved start
auto_last_lokale_filer()
