# Aidexa Report Mensili

Generatore di report Excel a partire da una query Oracle fissa
(`examples/caso1/query.sql`), distribuito come eseguibile Windows standalone.

## Funzionalità

- Connessione Oracle tramite `oracledb` in modalità **thin** (nessun Oracle
  Client/Instant Client richiesto). Stringa di connessione fissa (fornita
  dall'IT), non configurabile.
- Credenziali richieste al primo avvio e salvate in modo sicuro in
  **Windows Credential Manager** tramite `keyring`. Ai riavvii successivi
  vengono riusate automaticamente; in caso di fallimento vengono richieste
  di nuovo e poi aggiornate.
- Esecuzione della query in `examples/caso1/query.sql` e generazione di un
  report Excel che riproduce la struttura di
  `examples/caso1/output_atteso.xlsx` (righe per URL raggruppate per tipo
  errore 400/500, colonne per data/stato con subtotali e totale generale).
  La query riceve il mese selezionato come bind Oracle e usa sempre l'anno
  corrente del database.
- Dopo la connessione Oracle, selezione interattiva del mese. Se i dati
  estratti contengono più anni viene richiesta anche la selezione dell'anno;
  il report contiene esclusivamente il periodo scelto e tutte le sue giornate,
  incluse quelle senza record (valori a zero).
- Validazione strutturale del file generato rispetto al riferimento
  (`src/reporting/validator.py`): fogli, righe, colonne, valori, font, colori
  di sfondo, bordi, allineamenti, formati numerici, celle unite, larghezze
  colonna, altezze riga, freeze panes e filtri.
- Modalità di test offline (`--test-excel`): genera e valida il report senza
  alcuna connessione Oracle (vedi sezione dedicata sotto).
- Logging minimale su `logs/report.log` (mai password o credenziali).

## Regole di business dedotte dagli esempi

- `input.xlsx` = dump grezzo del risultato della query (stesse colonne:
  `URLL, DATAA, STATOO, TIPO_ERRORE, CONTEGGIO, CONTEGGIO_RAW`).
- `output_atteso.xlsx` = pivot costruito da quei dati:
  - righe: gruppo `TIPO_ERRORE` (`'400'` → "Errori gestiti (400)",
    `'500'` → "Errori non gestiti (500)"), poi URL in ordine alfabetico,
    poi riga subtotale ("TOTALE ERRORI GESTITI"/"TOTALE ERRORI NON GESTITI");
  - colonne: una data per blocco di 9 colonne (8 stati `A,D,F,I,K,N,P,T` +
    1 colonna totale), poi colonna "Grand Total" finale;
  - titolo report derivato dal filtro `prdt_code` della query
    (es. `DEPOSITO_VINCOLATO_AIDEXA` → "VINCOLATO");
  - colorazione: stati `A,D,F,I` giallo, `K,N,P,T` azzurro chiaro (solo sulla
    riga di intestazione stati), colonne totale grigio chiaro, riga banner di
    gruppo con testo bianco su sfondo blu, riga "Grand Total" evidenziata
    uniformemente in azzurro con bordo superiore.

## Modalità di test offline (`--test-excel`)

Permette di validare **esclusivamente** la logica di trasformazione e la
formattazione Excel, senza alcuna connessione Oracle, query, autenticazione o
accesso a credenziali:

```powershell
python -m src.main --test-excel
```

oppure, con l'eseguibile compilato:

```powershell
ReportGenerator.exe --test-excel
```

Il comando:

1. legge `examples/caso1/input.xlsx` (simula il risultato della query, stesso
   schema di colonne);
2. applica le stesse trasformazioni della modalità normale
   (`pivot_generator.build_report` + `excel_formatter.export_report`);
3. genera `output_test.xlsx` nella cartella dell'eseguibile/script;
4. confronta `output_test.xlsx` con `examples/caso1/output_atteso.xlsx`
   tramite `src/reporting/validator.py`;
5. stampa un report dettagliato delle differenze (foglio, cella, riga,
   colonna, valore atteso/generato, font, colori, bordi, allineamenti,
   formati numerici, celle unite, larghezze/altezze) e termina con exit code
   `0` se identico, `2` se sono state rilevate differenze, `1` in caso di
   errore.

### Differenze residue note (non bug)

- **Larghezze colonna**: l'originale usa larghezze frazionarie calcolate da
  Excel (auto-fit storico); il generatore usa larghezze fisse leggibili.
  Differenza puramente cosmetica.
- **Alcuni valori (righe URL del gruppo 500)**: `input.xlsx` e
  `output_atteso.xlsx` provengono da due esecuzioni storiche non
  perfettamente allineate (elenco URL leggermente diverso). Struttura,
  numero di righe/colonne e tutte le regole di formattazione coincidono
  comunque esattamente.
- **4 colonne / 2 righe** (area `FJ:FM`, righe 32-33): artefatto isolato
  presente nel solo file di riferimento storico, non riconducibile a una
  regola sistematica.

## Modalità test mensile (`--test-month`)

Verifica rapidamente il filtro senza connettersi a Oracle:

```powershell
python -m src.main --test-month
```

Il comando legge `examples/caso1/input.xlsx`, richiede un mese da `1` a `12`
e genera `output_test_month.xlsx`. Valori vuoti, non numerici o fuori
intervallo vengono richiesti nuovamente con un messaggio esplicito. Se il file
contiene un solo anno, questo viene selezionato automaticamente; con più anni
viene richiesto `Inserire anno da analizzare` e sono accettati solo gli anni
presenti nell'estrazione.

## Sviluppo locale

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.main
```

Al primo avvio verranno richiesti username e password Oracle.

## Build dell'eseguibile standalone

```powershell
pip install -r requirements.txt
pyinstaller ReportGenerator.spec --noconfirm
```

Il file `dist\ReportGenerator.exe` è autosufficiente: non richiede Python,
pip, librerie esterne o Oracle Client sulla macchina di destinazione.

`ReportGenerator.spec` include già:

- `datas`: `examples/caso1/query.sql` (bundlata nell'eseguibile);
- `hiddenimports`: tutti i backend di `keyring` (incluso quello Windows) e i
  moduli `pywin32` necessari per l'accesso a Credential Manager.

## Checklist di validazione finale

1. Disinstallare Python dalla macchina di test.
2. Copiare solo `ReportGenerator.exe` in una cartella qualsiasi.
3. Eseguire l'exe con doppio click: non deve comparire alcun
   `ModuleNotFoundError`, `ImportError`, `DLL load failed` o
   `Failed to execute script`.
4. Al primo avvio inserire username/password Oracle quando richiesto.
5. Verificare che l'exe si connetta a Oracle e informi chiaramente in caso
   di credenziali errate o rete non raggiungibile.
6. Verificare che venga eseguita la query e generato `output/report.xlsx`
   accanto all'eseguibile.
7. Confrontare struttura/formattazione con `examples/caso1/output_atteso.xlsx`.
8. Riavviare l'exe e verificare che la connessione avvenga automaticamente
   con le credenziali salvate (senza richiedere nuovamente l'input).

## Checklist per `--test-excel` (senza Oracle)

1. Eseguire `python -m src.main --test-excel` (o `ReportGenerator.exe --test-excel`).
2. Verificare nell'output/log che non compaia alcun tentativo di connessione
   Oracle, richiesta credenziali o esecuzione query.
3. Verificare che venga creato `output_test.xlsx` nella cartella corrente.
4. Leggere il "Report differenze" stampato a console:
   - `Nessuna differenza rilevata` → file identico al riferimento;
   - altrimenti, per ogni categoria (`valore`, `font`, `colore_sfondo`,
     `bordi`, `formato_numerico`, `allineamento`, `larghezza_colonna`,
     `altezza_riga`, `numero_righe`, `numero_colonne`, `celle_unite_*`,
     `freeze_panes`, `filtri`) controllare foglio/cella/riga/colonna e i
     valori atteso/generato riportati.
5. Le uniche differenze attese allo stato attuale sono quelle documentate
   nella sezione "Differenze residue note" sopra (larghezze colonna
   frazionarie, disallineamento URL tra `input.xlsx` e `output_atteso.xlsx`,
   e l'artefatto isolato in `FJ:FM` righe 32-33).

## Struttura progetto

```text
config.py                     # DSN fisso, percorsi query/log/output
requirements.txt
ReportGenerator.spec          # spec PyInstaller definitivo (onefile)
src/
├── main.py                   # orchestrazione + gestione credenziali/errori + --test-excel
├── db/oracle_connection.py   # connessione oracledb thin
├── security/credential_manager.py  # keyring / Windows Credential Manager
├── reporting/
│   ├── data_extractor.py     # lettura query.sql ed esecuzione
│   ├── pivot_generator.py    # regole di business / struttura pivot
│   ├── excel_formatter.py    # rendering Excel (stili, merge, colori)
│   └── validator.py          # confronto struttura vs file di riferimento
└── utils/logger.py
examples/                     # casi di riferimento (query, input, output atteso)
```

