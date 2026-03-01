"""
ip_dependencies.py — Tab: render_tab_ip_dependencies (v4.1)
"""

from tier2_visibility import calculate_ip_risk
import pandas as pd
import streamlit as st


def render_tab_ip_dependencies():
    """Tab: IP/SW Dependencies Analysis"""
    st.header("IP/SW Dependencies")
    st.markdown("""
    Track and analyze software IP dependencies (peripheral libraries, firmware stacks,
    drivers, EDA IP) and their impact on supply chain risk. The risk engine automatically
    detects proprietary vendor lock-in, deprecated, and abandoned IP technologies.
    """)

    batch = st.session_state.get('batch_results')
    if not batch:
        st.info("Run a **Multiple Analysis** first to analyze IP/SW dependencies.")
        return

    db = st.session_state.db
    all_ip_deps = db.get_all_ip_dependencies()

    if not all_ip_deps:
        st.warning("No IP dependencies tracked in the database.")
        col1, col2 = st.columns(2)
        with col1:
            st.info("Go to **Database Management → IP Dependencies** to add IP dependencies.")
        with col2:
            st.markdown("""
            **Example IPs to track:**
            - USB3.0 PHY Stack (Synaptics)
            - ARM Cortex-M RTOS (Cadence)
            - WiFi Firmware (Qualcomm)
            - EDA IP cores (Cadence, Synopsys)
            """)
        return

    # =========================================================================
    # IP DEPENDENCIES ANALYSIS
    # =========================================================================

    # Aggrega IP deps per componente
    components = batch['components_data']
    ip_stats = {}
    critical_ips = []

    for comp in components:
        pn = str(comp.get('Part Number', '')).upper()
        ip_list = all_ip_deps.get(pn, [])

        if ip_list:
            ip_result = calculate_ip_risk(pn, ip_list)
            ip_stats[pn] = ip_result

            # Raccogli IP critici
            if ip_result.get('has_risk'):
                for ip_dep in ip_list:
                    status = ip_dep.get('Maintenance_Status', 'Active')
                    if status in ['Abandoned', 'Deprecated']:
                        critical_ips.append({
                            'pn': pn,
                            'ip_name': ip_dep['IP_Name'],
                            'vendor': ip_dep['IP_Vendor'],
                            'status': status,
                        })

    # =========================================================================
    # CRITICAL ALERTS
    # =========================================================================
    if critical_ips:
        st.error(f"**{len(critical_ips)} Critical IP Issues Found**")
        for issue in critical_ips:
            status_emoji = "[ABANDONED]" if issue['status'] == 'Abandoned' else "[DEPRECATED]"
            st.markdown(
                f"- {status_emoji} `{issue['ip_name']}` (by {issue['vendor']}) in PN `{issue['pn']}`"
            )

    # =========================================================================
    # IP VENDOR RISK SUMMARY
    # =========================================================================
    st.markdown("---")
    st.subheader("IP Vendor Risk Summary")

    vendor_risk = {}
    for pn, ip_list in all_ip_deps.items():
        if any(c.get('Part Number', '').upper() == pn for c in components):
            for ip_dep in ip_list:
                vendor = ip_dep['IP_Vendor']
                if vendor not in vendor_risk:
                    vendor_risk[vendor] = {'count': 0, 'proprietary': 0, 'critical': 0}
                vendor_risk[vendor]['count'] += 1
                if ip_dep.get('License_Type') == 'Proprietary':
                    vendor_risk[vendor]['proprietary'] += 1
                if ip_dep.get('Maintenance_Status') in ['Abandoned', 'Deprecated']:
                    vendor_risk[vendor]['critical'] += 1

    if vendor_risk:
        vendor_data = []
        for vendor, stats in sorted(vendor_risk.items(), key=lambda x: x[1]['critical'], reverse=True):
            vendor_data.append({
                'IP Vendor': vendor,
                'Total IPs': stats['count'],
                'Proprietary': stats['proprietary'],
                'Critical Issues': stats['critical'],
            })

        df_vendors = pd.DataFrame(vendor_data)
        st.dataframe(df_vendors, use_container_width=True, hide_index=True)
    else:
        st.info("No IP vendors in this BOM")

    # =========================================================================
    # COMPONENTS WITH IP RISK
    # =========================================================================
    st.markdown("---")
    st.subheader("Components with IP Risk")

    components_with_ip_risk = [pn for pn, result in ip_stats.items() if result.get('has_risk')]

    if components_with_ip_risk:
        for pn in sorted(components_with_ip_risk):
            ip_result = ip_stats[pn]
            ip_score = ip_result.get('ip_score', 0)

            # Colore dell'expander basato su score
            if ip_score >= 15:
                risk_color = "[CRITICAL]"
            elif ip_score >= 8:
                risk_color = "[HIGH]"
            else:
                risk_color = "[MEDIUM]"

            with st.expander(f"{risk_color} **{pn}** (IP Risk: {ip_score}/20)"):
                ip_list = all_ip_deps.get(pn, [])

                # Mostra lista IP deps
                for ip_dep in ip_list:
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown(f"**{ip_dep['IP_Name']}**")
                        st.caption(f"by {ip_dep['IP_Vendor']}")
                    with col2:
                        lic = ip_dep.get('License_Type', 'N/A')
                        status = ip_dep.get('Maintenance_Status', 'Active')
                        st.markdown(f"*{lic}*")
                        st.caption(f"Status: {status}")
                    with col3:
                        alts = int(ip_dep.get('Vendor_Alternatives', 0))
                        if alts == 0:
                            st.error(f"0 alt")
                        elif alts == 1:
                            st.warning(f"{alts} alt")
                        else:
                            st.success(f"{alts} alt")

                # Mostra fattori
                if ip_result.get('ip_factors'):
                    st.markdown("**Risk Factors:**")
                    for factor in ip_result['ip_factors']:
                        st.markdown(f"- {factor}")

                # Mostra suggerimenti
                if ip_result.get('ip_suggestions'):
                    st.markdown("**Mitigation Actions:**")
                    for sugg in ip_result['ip_suggestions']:
                        st.markdown(f"- {sugg}")
    else:
        st.success("No IP dependency risks detected in this BOM.")
