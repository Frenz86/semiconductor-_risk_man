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
    SCENARIO_TYPES,
    COUNTRY_BLOCK_CONFIG
)
import pandas as pd
import streamlit as st


def render_tab_simulatore_whatif():
    """Tab 7: What-If Simulator - Disruption Scenarios"""
    st.header("What-If Simulator - Disruption Scenarios")
    st.markdown("""
    This module allows you to simulate the impact of disruption scenarios
    on the supply chain and see how risk changes.

    **Supported scenarios:**
    - Geographic block (e.g. Taiwan blocked for 4-8 weeks)
    - Lead time increase (% across all suppliers)
    - Specific supplier outage

    The simulator calculates:
    - Impact on buffer stock (when it runs out)
    - Change in overall risk
    - Estimated financial impact
    """)

    # -------------------------------------------------------------------------
    # DATA CHECK
    # -------------------------------------------------------------------------
    batch = st.session_state.batch_results

    if not batch:
        st.info("""
        Run a **Multiple Analysis** (Tab 2) first to load the BOM data.
        The simulator needs the components and their calculated risks.
        """)
    else:
        components_data = batch['components_data']
        components_risk = batch['components_risk']

        col1, col2 = st.columns([2, 1])

        # =====================================================================
        # COLUMN 1: SCENARIO CONFIGURATION
        # =====================================================================
        with col1:
            st.subheader("Scenario Configuration")

            scenario_option = st.radio(
                "Scenario Type",
                options=["Predefined", "Custom"],
                horizontal=True,
                label_visibility="collapsed",
                key="scenario_option"
            )

            scenario_config = None

            # ------------------------- PREDEFINED SCENARIOS -------------------
            if scenario_option == "Predefined":
                predefined = get_predefined_scenarios()
                scenario_names = [s['name'] for s in predefined]

                selected_name = st.selectbox(
                    "Select Scenario",
                    options=scenario_names,
                    help="Choose from predefined scenarios",
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
                - Type: {selected_scenario.get('type', '')}
                - Parameter: {param_text}
                - Duration: {selected_scenario['weeks']} weeks
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

            # ------------------------ CUSTOM SCENARIOS ------------------------
            else:
                st.write("**Custom Scenario Configuration**")

                def _apply_custom(form_data: Dict[str, Any]):
                    st.session_state.custom_scenario = form_data

                with st.form("custom_scenario_form"):
                    scenario_type_label = st.selectbox(
                        "Disruption Type",
                        options=list(SCENARIO_TYPES.values()),
                        help="Select the scenario type",
                        key="custom_type"
                    )

                    form_data: Dict[str, Any] = {}

                    if scenario_type_label == "Blocco Paese":
                        country = st.selectbox(
                            "Country",
                            options=list(COUNTRY_BLOCK_CONFIG.keys()),
                            help="Select the country to simulate as blocked",
                            key="custom_country"
                        )
                        default_weeks = COUNTRY_BLOCK_CONFIG[country]['default_weeks']
                        risk_multiplier = COUNTRY_BLOCK_CONFIG[country]['risk_multiplier']

                        weeks = st.slider(
                            "Block Duration (weeks)",
                            min_value=1, max_value=52,
                            value=default_weeks, step=1,
                            key="custom_weeks_country"
                        )
                        form_data = {
                            'type': 'country_block',
                            'country': country,
                            'weeks': weeks,
                            'description': f"{country} blocked for {weeks} weeks",
                            'risk_multiplier': risk_multiplier,
                        }

                    elif scenario_type_label == "Interruzione Fornitore":
                        suppliers_list = sorted(list(set(
                            str(c.get('Supplier Name', '')) for c in components_data
                        )))
                        supplier = st.selectbox(
                            "Supplier",
                            options=suppliers_list,
                            help="Select the supplier to simulate as interrupted",
                            key="custom_supplier"
                        )
                        weeks = st.slider(
                            "Outage Duration (weeks)",
                            min_value=1, max_value=52, value=4, step=1,
                            key="custom_weeks_supplier"
                        )
                        form_data = {
                            'type': 'supplier_outage',
                            'supplier': supplier,
                            'weeks': weeks,
                            'description': f"Supplier {supplier} interrupted for {weeks} weeks",
                        }

                    elif scenario_type_label == "Aumento Lead Time":
                        increase_percent = st.slider(
                            "Lead Time Increase (%)",
                            min_value=10, max_value=200, value=50, step=10,
                            key="custom_increase_percent"
                        )
                        weeks = st.slider(
                            "Increase Duration (weeks)",
                            min_value=1, max_value=52, value=4, step=1,
                            key="custom_weeks_lead"
                        )
                        form_data = {
                            'type': 'lead_time_increase',
                            'increase_percent': increase_percent,
                            'weeks': weeks,
                            'description': f"Lead time increase of {increase_percent}% for {weeks} weeks",
                            'risk_multiplier': 1.5,
                        }

                    elif scenario_type_label == "Carenza Materiale Tier-2":
                        material_options = {v['name']: k for k, v in MATERIAL_DATABASE.items()}
                        selected_material_name = st.selectbox(
                            "Material",
                            options=list(material_options.keys()),
                            key="custom_material"
                        )
                        material_key = material_options[selected_material_name]

                        mat_info = MATERIAL_DATABASE[material_key]
                        countries = list(mat_info['primary_countries'].keys())
                        affected_countries = st.multiselect(
                            "Affected Countries",
                            options=[c.title() for c in countries],
                            default=[c.title() for c in countries[:2]],
                            key="custom_material_countries"
                        )

                        weeks = st.slider(
                            "Shortage Duration (weeks)",
                            min_value=1, max_value=52, value=4, step=1,
                            key="custom_weeks_material"
                        )
                        form_data = {
                            'type': 'material_shortage',
                            'material_type': material_key,
                            'affected_countries': [c.lower() for c in affected_countries],
                            'weeks': weeks,
                            'description': f"{selected_material_name} shortage for {weeks} weeks",
                            'risk_multiplier': 2.0,
                        }

                    st.form_submit_button(
                        "Apply",
                        type="primary",
                        on_click=_apply_custom,
                        args=(form_data,)
                    )

                scenario_config = st.session_state.get('custom_scenario', None)

        # =====================================================================
        # COLUMN 2: COMPONENT FILTER AND RUN SIMULATION
        # =====================================================================
        with col2:
            st.subheader("Specific Components (Optional)")

            if scenario_config is not None and scenario_config.get('type'):
                scenario_type = scenario_config['type']

                if scenario_type == 'country_block':
                    country_filter = scenario_config.get('country', '')
                    st.info(f"Showing only components with Frontend/Backend in **{country_filter}**")
                    filtered_indices = [
                        i for i, c in enumerate(components_data)
                        if _check_affected(c, scenario_config)
                    ]

                elif scenario_type == 'supplier_outage':
                    supplier_filter = scenario_config.get('supplier', '')
                    st.info(f"Showing only components from supplier **{supplier_filter}**")
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
                    "Specific Component (Analyze All)",
                    options=["Analyze All"] + component_names,
                    help="Select a component to see detail",
                    key="component_select"
                )

                if selected_pn == "Analyze All":
                    selected_indices = filtered_indices
                else:
                    idx_in_filtered = component_names.index(selected_pn)
                    selected_indices = [filtered_indices[idx_in_filtered]]
            else:
                st.info("No components affected by this scenario")
                selected_indices = []

            if st.button("Run Simulation", type="primary", key="run_simulation"):
                if not scenario_config:
                    st.error("Please configure a scenario before running the simulation")
                elif not selected_indices:
                    st.warning("Select at least one component to analyze")
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
        # RESULTS
        # =====================================================================
        if 'simulation_result' in st.session_state:
            result = st.session_state.simulation_result
            summary = result['summary']
            scenario_info = result['scenario_info']

            st.markdown("---")
            st.subheader("Simulation Results")

            col_result1, col_result2 = st.columns(2)

            with col_result1:
                st.markdown(f"""
                **Type**: {scenario_info['description']}
                **Duration**: {scenario_info['duration_weeks']} weeks
                **Parameter**: {scenario_info['parameter']}
                """)

                st.metric(
                    "Affected Components",
                    f"{summary['affected_count']}/{summary['total_components']}"
                )
                st.metric("Critical Components", summary['critical_count'])

            with col_result2:
                delta = summary['score_change']
                delta_color = "normal" if delta == 0 else "inverse" if delta < 0 else "off"

                st.metric(
                    "Overall Risk",
                    f"{summary['avg_adjusted_score']} ({summary['overall_level']})",
                    delta=delta,
                    delta_color=delta_color
                )

            st.markdown("### Financial Impact")

            col_fin1, col_fin2, col_fin3 = st.columns(3)

            with col_fin1:
                st.metric(
                    "BOM Value at Risk",
                    f"${summary['total_bom_value']:,.2f}"
                )

            with col_fin2:
                weeks_lost = summary.get('total_production_lost_weeks', 0)
                st.metric(
                    "Production Lost",
                    f"{weeks_lost:.1f} weeks"
                )

            with col_fin3:
                revenue_loss = summary.get('total_financial_impact', 0)
                st.metric(
                    "Estimated Impact",
                    f"${revenue_loss:,.2f}"
                )

            if result['impacted_components']:
                st.markdown("### Affected Components Detail")

                detail_rows = []
                for comp in result['impacted_components']:
                    detail_rows.append({
                        'Part Number': comp['part_number'],
                        'Supplier': comp['supplier'],
                        'Orig. Score': comp['original_score'],
                        'New Score': comp['adjusted_score'],
                        'Change': comp['score_change'],
                        'Orig. Buffer (wk)': comp['original_buffer_weeks'],
                        'New Buffer (wk)': comp['remaining_buffer_weeks'],
                        'Weeks Lost': comp['weeks_lost'],
                        'Impact $': comp['financial_impact'],
                    })

                df_detail = pd.DataFrame(detail_rows)
                df_detail = df_detail.sort_values('Impact $', ascending=False)

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
                        subset=['Orig. Score', 'New Score']
                    ),
                    width=True,
                    hide_index=True
                )

            critical = result.get('critical_components', [])
            if critical:
                st.markdown("### Critical Components")
                st.warning("These components deplete their buffer during the disruption:")

                for comp in critical[:10]:
                    depletion = comp['depletion_date'] or 'Immediate'
                    st.markdown(f"""
                    - **{comp['part_number']}** ({comp['supplier']})
                      - Depletes: {depletion}
                      - Remaining Weeks: {comp['remaining_buffer_weeks']:.1f}
                    """)

                if len(critical) > 10:
                    st.markdown(f"... and {len(critical) - 10} more components")

            st.markdown("---")
            st.info("""
            **Note**: To see the impact on the entire BOM, run a new **Multiple Analysis**
            with this scenario applied.
            """)


# =============================================================================
# TAB 8: EXECUTIVE DASHBOARD
# =============================================================================

