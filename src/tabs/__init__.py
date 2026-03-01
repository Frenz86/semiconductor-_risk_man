"""
src/tabs/__init__.py — Facade: re-esporta tutte le render_tab_* funzioni.
app.py e tabs_modules.py continuano a funzionare senza modifiche.
"""

from .analisi_rapida      import render_tab_analisi_rapida
from .analisi_multipla    import render_tab_analisi_multipla
from .dashboard           import render_tab_dashboard_esecutiva
from .albero_dipendenze   import render_tab_albero_dipendenze
from .mappa_geopolitica   import render_tab_mappa_geopolitica
from .tier2_visibility    import render_tab_tier2_visibility
from .ip_dependencies     import render_tab_ip_dependencies
from .costi_switching     import render_tab_costi_switching
from .gestione_database   import render_tab_gestione_database
from .whatif              import render_tab_simulatore_whatif
from .guida               import render_tab_guida
from .filiera_commerciale import render_tab_filiera_commerciale
