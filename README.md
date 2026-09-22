# oracle-report-generator

Repository Python professionale per l'estrazione dati da Oracle e la generazione automatica di report Excel con Pivot Table e formattazione avanzata.

## Funzionalità

- Connessione a database Oracle tramite `oracledb`
- Configurazione credenziali e parametri via file `.env`
- Esecuzione query SQL parametrica su dati di vendita
- Esportazione dati grezzi nel foglio Excel `DATI`
- Generazione Pivot Table nel foglio `REPORT`
- Formattazione professionale con `openpyxl`
- Logging applicativo su `logs/report.log`
- Gestione errori per configurazione, Oracle, query e file bloccati

## Requisiti

- Python 3.10+
- Accesso a un database Oracle

## Installazione

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configurazione Oracle

1. Copiare il file di esempio:

   ```bash
   cp .env.example .env
   ```

2. Configurare le variabili:

   ```env
   ORACLE_HOST=oracle.example.internal
   ORACLE_PORT=1521
   ORACLE_SERVICE_NAME=ORCLPDB1
   ORACLE_USERNAME=report_user
   ORACLE_PASSWORD=change_me
   QUERY_START_DATE=2026-01-01
   QUERY_END_DATE=2026-01-31
   QUERY_REGION=
   OUTPUT_FILE=output/report.xlsx
   ```

## Variabili ambiente

| Variabile | Obbligatoria | Descrizione |
| --- | --- | --- |
| `ORACLE_HOST` | Sì | Host del database Oracle |
| `ORACLE_PORT` | Sì | Porta del listener Oracle |
| `ORACLE_SERVICE_NAME` | Sì | Service name Oracle |
| `ORACLE_USERNAME` | Sì | Username applicativo |
| `ORACLE_PASSWORD` | Sì | Password applicativa |
| `QUERY_START_DATE` | Sì | Data inizio filtro vendite (`YYYY-MM-DD`) |
| `QUERY_END_DATE` | Sì | Data fine filtro vendite (`YYYY-MM-DD`) |
| `QUERY_REGION` | No | Filtro opzionale per regione |
| `OUTPUT_FILE` | No | Percorso file Excel finale |

## Esecuzione

```bash
python -m src.main
```

Alla fine dell'esecuzione il programma genera:

- `output/report.xlsx`
- `logs/report.log`

## Struttura progetto

```text
oracle-report-generator/
├── src/
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── oracle_connection.py
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── data_extractor.py
│   │   ├── excel_formatter.py
│   │   └── pivot_generator.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logger.py
│   └── main.py
├── logs/
│   └── .gitkeep
├── output/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── config.py
├── requirements.txt
└── README.md
```

## Query Oracle di esempio

La query utilizzata è parametrica e realistica per un contesto vendite:

```sql
SELECT
    TRUNC(DATA_VENDITA) AS DATA_VENDITA,
    REGIONE,
    CLIENTE,
    CATEGORIA,
    PRODOTTO,
    IMPORTO,
    QTA
FROM VENDITE
WHERE DATA_VENDITA >= :start_date
  AND DATA_VENDITA < :end_date + 1
  AND (:region IS NULL OR REGIONE = :region)
ORDER BY DATA_VENDITA, REGIONE, CLIENTE
```

## Output Excel

Il file Excel generato contiene:

- foglio `DATI` con i risultati completi della query
- foglio `REPORT` con pivot:
  - righe: `REGIONE`
  - colonne: `CATEGORIA`
  - valori: somma `IMPORTO`
- totali generali per righe e colonne
- ordinamento decrescente per totale importo
- titolo unito e centrato
- header blu scuro con testo bianco bold
- bordi su tutte le celle
- formato valuta euro
- filtri automatici
- freeze pane
- evidenza grafica dei totali
- color scale rosso/giallo/verde sui valori

## Troubleshooting

### Credenziali mancanti

Verificare che il file `.env` esista e contenga tutti i campi Oracle richiesti.

### Connessione Oracle non disponibile

- Verificare host, porta e service name
- Controllare eventuali firewall/VPN
- Confermare che l'utente abbia permessi sulla tabella `VENDITE`

### Query fallita

- Controllare il nome della tabella e delle colonne
- Verificare il formato delle date nei parametri
- Consultare `logs/report.log`

### File Excel bloccato

Chiudere `output/report.xlsx` se aperto in Excel e rieseguire il comando.

## Esempio di output atteso

```text
2026-09-22 10:00:00,000 | INFO | src.main | Avvio generazione report vendite
2026-09-22 10:00:01,200 | INFO | src.reporting.data_extractor | Estratte 125 righe da Oracle
2026-09-22 10:00:02,050 | INFO | src.reporting.excel_formatter | Report Excel salvato in output/report.xlsx
2026-09-22 10:00:02,051 | INFO | src.main | Processo completato con successo
```

## Estendibilità futura

- aggiunta di più report/pivot
- scheduling batch
- invio email automatico
- filtri avanzati per cliente, prodotto o categoria
