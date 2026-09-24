# GitHub Copilot Instructions

## Mission

Genera software semplice, robusto, eseguibile e manutenibile.

Obiettivi prioritari:

1. Codice funzionante
2. Correttezza
3. Portabilità
4. Manutenibilità
5. Performance
6. Documentazione

Prediligi sempre la soluzione più semplice che soddisfa il requisito.

---

## Token Budget

Riduci al minimo il consumo di token.

Vincoli obbligatori:

- Almeno l'85% dell'output deve essere codice.
- Massimo 150 token di spiegazione.
- Massimo 10 righe fuori dai blocchi di codice.
- Nessuna introduzione.
- Nessuna conclusione.
- Nessun riassunto finale.
- Nessuna spiegazione teorica non richiesta.
- Nessuna descrizione del ragionamento interno.
- Nessuna ripetizione dei requisiti forniti dall'utente.

Se il codice è lungo:

- Riduci i commenti.
- Elimina esempi ridondanti.
- Fornisci una sola implementazione.

Target ideale:

- 0-100 token di testo.
- Tutto il resto codice.

---

## Output Format

Per richieste di sviluppo:

```python
# codice completo e funzionante
```

Poi solo:

```bash
python main.py
```

Nessun altro testo.

Se richiesto un aggiornamento:

- Modifica solo il codice necessario.
- Non riscrivere interi moduli senza motivo.
- Mantieni la compatibilità esistente.

---

## Python Standards

Versione target:

- Python 3.11+

Regole:

- Type hints obbligatori.
- UTF-8.
- PEP8.
- pathlib invece di os.path.
- dataclass quando appropriato.
- Context manager per file e risorse.
- Compatibilità Windows/Linux/macOS.
- Nessun path assoluto.
- Nessuna configurazione dipendente dalla piattaforma.

---

## Dependency Policy

Ordine di preferenza:

1. Standard Library
2. Librerie leggere e mature
3. Framework complessi solo se indispensabili

Non introdurre dipendenze senza reale necessità.

Se una dipendenza è inevitabile:

- Utilizzare la più diffusa.
- Aggiungere una sola istruzione di installazione.
- Non aggiungere spiegazioni superflue.

Preferire sempre:

- pathlib
- json
- csv
- sqlite3
- argparse
- logging
- concurrent.futures
- asyncio

prima di librerie esterne.

---

## Architecture Guidelines

Preferire:

- Un singolo file quando possibile.
- Design semplice.
- Funzioni piccole.
- Bassa complessità.
- Basso accoppiamento.
- Alta leggibilità.

Evitare:

- Over-engineering.
- Pattern enterprise inutili.
- Factory non necessarie.
- Astrazioni premature.
- Classi con una sola responsabilità banale.
- Framework quando bastano poche funzioni.

---

## Code Quality Rules

Il codice deve essere:

- Completo.
- Eseguibile.
- Testabile.
- Leggibile.
- Deterministico quando possibile.

Ogni funzione deve:

- Avere type hints.
- Avere una responsabilità chiara.
- Gestire gli errori prevedibili.

Preferire:

- Return early.
- Funzioni pure.
- Nomi espliciti.
- Strutture dati standard.

---

## Error Handling

Gestire:

- Parametri invalidi.
- File mancanti.
- Permessi insufficienti.
- Errori di rete.
- Errori di parsing.

Fornire messaggi brevi e chiari.

Evitare:

- except generici senza motivo.
- stack trace inutili verso l'utente.
- crash non gestiti.

---

## Logging

Utilizzare logging solo quando utile.

Preferenze:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
```

Evitare logging verboso.

---

## CLI Applications

Per strumenti da linea di comando:

- Usare argparse.
- Fornire help automatico.
- Restituire exit code corretti.
- Validare tutti gli input.

Preferire:

```python
def main() -> int:
    ...
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

---

## Performance

Ottimizzare solo quando necessario.

Ordine di priorità:

1. Correttezza
2. Semplicità
3. Leggibilità
4. Performance

Evitare micro-ottimizzazioni.

---

## Security

Non:

- Hardcodare credenziali.
- Hardcodare token.
- Hardcodare password.
- Disabilitare validazioni di sicurezza.

Usare:

- Variabili d'ambiente.
- Input validation.
- Parametri configurabili.

---

## Refactoring Rules

Durante i refactoring:

- Preservare il comportamento esistente.
- Minimizzare il diff.
- Mantenere API pubbliche compatibili.
- Eliminare codice morto.
- Ridurre duplicazioni.

Non introdurre nuove dipendenze senza motivo.

---

## Testing

Quando vengono richiesti test:

- Usare pytest.
- Generare test eseguibili.
- Coprire i casi principali.
- Coprire error handling.

Evitare test inutilmente complessi.

---

## Documentation

Documentazione minima.

Preferire:

```python
def load_data(path: Path) -> list[str]:
    """Load lines from a UTF-8 text file."""
```

Evitare docstring lunghe.

---

## Forbidden Output

Non generare:

- TODO
- FIXME
- Placeholder
- Pseudocodice
- Mock non richiesti
- Implementazioni incomplete
- Funzioni vuote
- Commenti ridondanti
- Catena di pensiero
- Tutorial lunghi
- Multiple soluzioni non richieste

Ogni output deve essere immediatamente utilizzabile.

---

## Decision Strategy

In caso di ambiguità scegliere nell'ordine:

1. Soluzione più semplice.
2. Meno dipendenze.
3. Più portabile.
4. Meno token.
5. Singolo file.
6. Maggiore leggibilità.

---

## Copilot Behavior

Assumere che il repository privilegi:

- Automazione.
- Script CLI.
- Tool operativi.
- Utility interne.
- Basso maintenance cost.

Consegnare direttamente la soluzione finale.

Non spiegare il processo decisionale.