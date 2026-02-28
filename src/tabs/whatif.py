"""
whatif.py — Tab: render_tab_simulatore_whatif
"""

from tier2_visibility import (
    calculate_tier2_risk,
    analyze_bom_tier2_bottlenecks,
    MATERIAL_DATABASE,
    CATEGORY_MATERIAL_MAPPINGS,
)
from typing import List, Any, Dict
from whatif_simulator import (
    simulate_disruption,
    get_predefined_scenarios,
    _is_component_affected as _check_affected,
    SCENARIO_TYPES
)
import pandas as pd
import streamlit as st


def render_tab_simulatore_whatif():
    """Tab 7: Simulatore What-If - Scenari di Disruption"""
    st.header("Simulatore What-If - Scenari di Disruption")
    st.markdown("""
    Questo modulo permette di simulare l'impatto di scenari di disruption
    sulla supply chain e vedere come cambia il rischio.

    **Scenari supportati:**
    - Blocco geografico (es. Taiwan bloccata 4-8 settimane)
    - Aumento lead time (% su tutti i fornitori)
    - Interruzione fornitore specifico

    Il simulatore calcola:
    - Impatto su buffer stock (quando si esaurisce)
    - Variazione del rischio complessivo
    - Impatto finanziario stimato
    """)

    # -------------------------------------------------------------------------
    # VERIFICA DATI
    # -------------------------------------------------------------------------
    batch = st.session_state.batch_results

    if not batch:
        st.info("""
        Esegui prima un'**Analisi Multipla** (Tab 2) per caricare i dati della BOM.
        Il simulatore ha bisogno dei componenti e dei loro rischi calcolati.
        """)
    else:
        components_data = batch['components_data']
        components_risk = batch['components_risk']

        col1, col2 = st.columns([2, 1])

        # =====================================================================
        # COLONNA 1: CONFIGURAZIONE SCENARIO
        # =====================================================================
        with col1:
            st.subheader("Configurazione Scenario")

            scenario_option = st.radio(
                "Tipo di Scenario",
                options=["Predefinito", "Personalizzato"],
                horizontal=True,
                label_visibility="collapsed",
                key="scenario_option"
            )

            scenario_config = None

            # ------------------------- SCENARI PREDEFINITI --------------------
            if scenario_option == "Predefinito":
                predefined = get_predefined_scenarios()
                scenario_names = [s['name'] for s in predefined]

                selected_name = st.selectbox(
                    "Seleziona Scenario",
                    options=scenario_names,
                    help="Scegli tra gli scenari predefiniti",
                    key="predefined_select"
                )

                selected_scenario = next(
                    s for s in predefined if s['name'] == selected_name
                )

                if selected_scenario['type'] == 'country_block':
                    param_text = selected_scenario.get('country', '')
                elif selected_scenario['type'] == 'lead_time_increase':
                    param_text = f"{selected_scenario.get('increase_percent', 0)}%"
                elif selected_scenario['type'] == 'supplier_outage':
                    param_text = selected_scenario.get('supplier', '')
                else:
                    param_text = ""

                st.info(f"""
                **Scenario**: {selected_scenario['name']}
                - Tipo: {selected_scenario.get('type', '')}
                - Parametro: {param_text}
                - Durata: {selected_scenario['weeks']} settimane
                """)

                scenario_config = {
                    'type': selected_scenario.get('type', ''),
                    'description': selected_scenario.get(
                        'description',
                        selected_scenario.get('name', '')
                    ),
                    'weeks': selected_scenario.get('weeks', 0),
                }

                if selected_scenario['type'] == 'country_block':
                    scenario_config['country'] = selected_scenario.get('country', '')
                    scenario_config['risk_multiplier'] = selected_scenario.get('risk_multiplier', 2.0)
                elif selected_scenario['type'] == 'lead_time_increase':
                    scenario_config['increase_percent'] = selected_scenario.get('increase_percent', 50)
                    scenario_config['risk_multiplier'] = selected_scenario.get('risk_multiplier', 1.5)
                elif selected_scenario['type'] == 'supplier_outage':
                    scenario_config['supplier'] = selected_scenario.get('supplier', '')

                st.session_state.predefined_scenario = scenario_config

            # ------------------------ SCENARI PERSONALIZZATI -------------------
            else:
                st.write("**Configurazione Scenario Personalizzato**")

                def _apply_custom(form_data: Dict[str, Any]):
                    st.session_state.custom_scenario = form_data

                with st.form("custom_scenario_form"):
                    scenario_type_label = st.selectbox(
                        "Tipo Disruption",
                        options=list(SCENARIO_TYPES.values()),
                        help="Seleziona il tipo di scenario",
                        key="custom_type"
                    )

                    form_data: Dict[str, Any] = {}

                    if scenario_type_label == "Blocco Paese":
                        country = st.selectbox(
                            "Paese",
                            options=list(COUNTRY_BLOCK_CONFIG.keys()),
                            help="Seleziona il paese da simulare bloccato",
                            key="custom_country"
                        )
                        default_weeks = COUNTRY_BLOCK_CONFIG[country]['default_weeks']
                        risk_multiplier = COUNTRY_BLOCK_CONFIG[country]['risk_multiplier']

                        weeks = st.slider(
                            "Durata Blocco (settimane)",
                            min_value=1, max_value=52,
                            value=default_weeks, step=1,
                            key="custom_weeks_country"
                        )
                        form_data = {
                            'type': 'country_block',
                            'country': country,
                            'weeks': weeks,
                            'description': f"{country} bloccato per {weeks} settimane",
                            'risk_multiplier': risk_multiplier,
                        }

                    elif scenario_type_label == "Interruzione Fornitore":
                        suppliers_list = sorted(list(set(
                            str(c.get('Supplier Name', '')) for c in components_data
                        )))
                        supplier = st.selectbox(
                            "Fornitore",
                            options=suppliers_list,
                            help="Seleziona il fornitore da simulare interrotto",
                            key="custom_supplier"
                        )
                        weeks = st.slider(
                            "Durata Interruzione (settimane)",
                            min_value=1, max_value=52, value=4, step=1,
                            key="custom_weeks_supplier"
                        )
                        form_data = {
                            'type': 'supplier_outage',
                            'supplier': supplier,
                            'weeks': weeks,
                            'description': f"Fornitore {supplier} interrotto per {weeks} settimane",
                        }

                    elif scenario_type_label == "Aumento Lead Time":
                        increase_percent = st.slider(
                            "Aumento Lead Time (%)",
                            min_value=10, max_value=200, value=50, step=10,
                            key="custom_increase_percent"
                        )
                        weeks = st.slider(
                            "Durata Aumento (settimane)",
                            min_value=1, max_value=52, value=4, step=1,
                            key="custom_weeks_lead"
                        )
                        form_data = {
                            'type': 'lead_time_increase',
                            'increase_percent': increase_percent,
                            'weeks': weeks,
                            'description': f"Aumento lead time del {increase_percent}% per {weeks} settimane",
                            'risk_multiplier': 1.5,
                        }

                    elif scenario_type_label == "Carenza Materiale Tier-2":
                        material_options = {v['name']: k for k, v in MATERIAL_DATABASE.items()}
                        selected_material_name = st.selectbox(
                            "Materiale",
                            options=list(material_options.keys()),
                            key="custom_material"
                        )
                        material_key = material_options[selected_material_name]

                        mat_info = MATERIAL_DATABASE[material_key]
                        countries = list(mat_info['primary_countries'].keys())
                        affected_countries = st.multiselect(
                            "Paesi Colpiti",
                            options=[c.title() for c in countries],
                            default=[c.title() for c in countries[:2]],
                            key="custom_material_countries"
                        )

                        weeks = st.slider(
                            "Durata Carenza (settimane)",
                            min_value=1, max_value=52, value=4, step=1,
                            key="custom_weeks_material"
                        )
                        form_data = {
                            'type': 'material_shortage',
                            'material_type': material_key,
                            'affected_countries': [c.lower() for c in affected_countries],
                            'weeks': weeks,
                            'description': f"Carenza {selected_material_name} per {weeks} settimane",
                            'risk_multiplier': 2.0,
                        }

                    st.form_submit_button(
                        "Applica",
                        type="primary",
                        on_click=_apply_custom,
                        args=(form_data,)
                    )

                scenario_config = st.session_state.get('custom_scenario', None)

        # =====================================================================
        # COLONNA 2: FILTRO COMPONENTI E AVVIO SIMULAZIONE
        # =====================================================================
        with col2:
            st.subheader("Componenti Specifici (Opzionale)")

            if scenario_config is not None and scenario_config.get('type'):
                scenario_type = scenario_config['type']

                if scenario_type == 'country_block':
                    country_filter = scenario_config.get('country', '')
                    st.info(f"Mostrando solo componenti con Frontend/Backend in **{country_filter}**")
                    filtered_indices = [
                        i for i, c in enumerate(components_data)
                        if _check_affected(c, scenario_config)
                    ]

                elif scenario_type == 'supplier_outage':
                    supplier_filter = scenario_config.get('supplier', '')
                    st.info(f"Mostrando solo componenti del fornitore **{supplier_filter}**")
                    filtered_indices = [
                        i for i, c in enumerate(components_data)
                        if _check_affected(c, scenario_config)
                    ]

                else:
                    filtered_indices = list(range(len(components_data)))
            else:
                filtered_indices = list(range(len(components_data)))

            if filtered_indices:
                component_names = [
                    components_data[i].get('Part Number', f'PN_{i}')
                    for i in filtered_indices
                ]
                selected_pn = st.selectbox(
                    "Componente Specifico (Analizza Tutti)",
                    options=["Analizza Tutti"] + component_names,
                    help="Seleziona un componente per vedere dettaglio",
                    key="component_select"
                )

                if selected_pn == "Analizza Tutti":
                    selected_indices = filtered_indices
                else:
                    idx_in_filtered = component_names.index(selected_pn)
                    selected_indices = [filtered_indices[idx_in_filtered]]
            else:
                st.info("Nessun componente affetto da questo scenario")
                selected_indices = []

            if st.button("Esegui Simulazione", type="primary", key="run_simulation"):
                if not scenario_config:
                    st.error("Per favore, configura uno scenario prima di eseguire la simulazione")
                elif not selected_indices:
                    st.warning("Seleziona almeno un componente da analizzare")
                else:
                    filtered_components = [components_data[i] for i in selected_indices]
                    filtered_risks = [components_risk[i] for i in selected_indices]

                    result = simulate_disruption(
                        filtered_components,
                        filtered_risks,
                        scenario_config,
                        st.session_state.run_rate
                    )
                    st.session_state.simulation_result = result

        # =====================================================================
        # RISULTATI
        # =====================================================================
        if 'simulation_result' in st.session_state:
            result = st.session_state.simulation_result
            summary = result['summary']
            scenario_info = result['scenario_info']

            st.markdown("---")
            st.subheader("Risultato Simulazione")

            col_result1, col_result2 = st.columns(2)

            with col_result1:
                st.markdown(f"""
                **Tipo**: {scenario_info['description']}
                **Durata**: {scenario_info['duration_weeks']} settimane
                **Parametro**: {scenario_info['parameter']}
                """)

                st.metric(
                    "Componenti Affetti",
                    f"{summary['affected_count']}/{summary['total_components']}"
                )
                st.metric("Componenti Critici", summary['critical_count'])

            with col_result2:
                delta = summary['score_change']
                delta_color = "normal" if delta == 0 else "inverse" if delta < 0 else "off"

                st.metric(
                    "Rischio Complessivo",
                    f"{summary['avg_adjusted_score']} ({summary['overall_level']})",
                    delta=delta,
                    delta_color=delta_color
                )

            st.markdown("### Impatto Finanziario")

            col_fin1, col_fin2, col_fin3 = st.columns(3)

            with col_fin1:
                st.metric(
                    "Valore BOM a Rischio",
                    f"${summary['total_bom_value']:,.2f}"
                )

            with col_fin2:
                weeks_lost = summary.get('total_production_lost_weeks', 0)
                st.metric(
                    "Produzione Persa",
                    f"{weeks_lost:.1f} settimane"
                )

            with col_fin3:
                revenue_loss = summary.get('total_financial_impact', 0)
                st.metric(
                    "Impatto Stimato",
                    f"${revenue_loss:,.2f}"
                )

            if result['impacted_components']:
                st.markdown("### Dettaglio Componenti Affetti")

                detail_rows = []
                for comp in result['impacted_components']:
                    detail_rows.append({
                        'Part Number': comp['part_number'],
                        'Fornitore': comp['supplier'],
                        'Score Orig.': comp['original_score'],
                        'Score Nuovo': comp['adjusted_score'],
                        'Variazione': comp['score_change'],
                        'Buffer Orig. (sett)': comp['original_buffer_weeks'],
                        'Buffer Nuovo (sett)': comp['remaining_buffer_weeks'],
                        'Sett. Perse': comp['weeks_lost'],
                        'Impatto $': comp['financial_impact'],
                    })

                df_detail = pd.DataFrame(detail_rows)
                df_detail = df_detail.sort_values('Impatto $', ascending=False)

                def color_score(val):
                    try:
                        v = float(val)
                    except Exception:
                        return ''
                    if v >= 55:
                        return 'background-color: #ff4444; color: white;'
                    elif v >= 30:
                        return 'background-color: #ffbb33; color: black;'
                    else:
                        return 'background-color: #00C851; color: white;'

                st.dataframe(
                    df_detail.style.applymap(
                        color_score,
                        subset=['Score Orig.', 'Score Nuovo']
                    ),
                    use_container_width=True,
                    hide_index=True
                )

            critical = result.get('critical_components', [])
            if critical:
                st.markdown("### Componenti Critici")
                st.warning("Questi componenti esauriscono il buffer durante la disruption:")

                for comp in critical[:10]:
                    depletion = comp['depletion_date'] or 'Immediato'
                    st.markdown(f"""
                    - **{comp['part_number']}** ({comp['supplier']})  
                      - Esaurisce: {depletion}  
                      - Sett. Rimanenti: {comp['remaining_buffer_weeks']:.1f}
                    """)

                if len(critical) > 10:
                    st.markdown(f"... e altri {len(critical) - 10} componenti")

            st.markdown("---")
            st.info("""
            **Nota**: Per vedere l'impatto su tutta la BOM, esegui una nuova **Analisi Multipla**
            con questo scenario applicato.
            """)


# =============================================================================
# TAB 8: DASHBOARD ESECUTIVA
# =============================================================================

