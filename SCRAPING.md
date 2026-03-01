Layer 1 — dove il costo/valore è più asimmetrico:

EDGAR non è scraping — api.sec.gov è una REST API pubblica e strutturata, zero overhead. I campi che alimenta nel DB esistente (Financial_Health_Score) sono già previsti nel schema.
BIS/OFAC non è scraping — sono file CSV/XML scaricabili direttamente. Un job settimanale di matching Supplier_Name → Entity List richiede 50 righe di Python.
DigiTimes è paywalled, Reuters è accessibile ma rumoroso. Il segnale più pulito è probabilmente SEMI.org press releases + manufacturer IR pages (sempre pubbliche).
Layer 2 — sottovalutato:

Digi-Key e Mouser API gratuite ritornano esattamente i 3 campi che impattano di più il risk score: stock_qty, lead_time_weeks, unit_price. Con 500 PN nel DB e polling settimanale stai abbondantemente dentro il rate limit gratuito.

Il vero gap del mercato:

Il PCN monitor. Nessuno lo fa in real-time perché la monetizzazione non è ovvia per i grandi player (Nexar si focalizza su inventory/pricing). Ma per chi gestisce BOM automotive o industriale, sapere 6 mesi prima che un PN entra in NRND vale migliaia di ore di requalification evitate.

Priorità pratica data l'app attuale:


1. Digi-Key/Mouser API     → feed immediato su lead time, stock, price (3 fattori risk engine)
2. EDGAR API               → supplier financial health automatizzato
3. BIS/OFAC matching       → nuovo fattore rischio (compliance/sanzioni), alta differenziazione
4. PCN scraper             → moat competitivo, complessità media
5. News NLP                → complessità alta, rinviabile
I primi 3 non toccano l'architettura esistente — alimentano campi già presenti in Part_Numbers e Supplier_Profiles. 

Nexar aggrega tutto il mercato:

Stock da 20+ distributori (Digi-Key, Mouser, Arrow, Avnet, TTI, Future...)
Manufacturer lead time direttamente dalla fonte
Segnale di scarsità reale: "disponibile solo da 1 distributore su 12" → shortage alert
Trend storici di prezzo e disponibilità
BOM matching in una sola chiamata
Digi-Key/Mouser API:

Solo il loro stock interno
Un componente può sembrare "out of stock" su Digi-Key ma disponibile su Arrow → falso positivo di shortage
L'implicazione per il risk score:

Con solo Digi-Key+Mouser rischi di sovrastimare il rischio su componenti disponibili altrove. Per il fattore Allocation_Status nel motore di rischio, Nexar è genuinamente più accurato perché vede il mercato intero.

Il compromesso pratico:

Nexar free tier	DigiKey+Mouser
Copertura mercato	~95%	~20-25%
Lead time accuracy	Alta (manufacturer)	Media
Shortage detection	Affidabile	Falsi positivi
Costo	50k calls/mese gratis	Gratis illimitato
Rate limit	Restrittivo	Generoso
Conclusione onesta: per questo use case specifico Nexar è superiore come qualità del dato. Digi-Key/Mouser ha senso come fallback o per verificare prezzi puntuali, non come fonte primaria di market intelligence.

Il combo ottimale rimane Nexar per market data + Digi-Key per price check.