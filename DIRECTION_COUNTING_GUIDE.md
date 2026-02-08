# Guida al Conteggio Direzionale degli Oggetti

## Panoramica

La nuova funzionalità di conteggio direzionale permette di conteggiare gli oggetti in base alla **direzione di movimento** attraverso i segmenti della zona di rilevamento.

## Come Funziona

### 1. Definire i Segmenti

Quando si disegna un'area di rilevamento (ROI), il perimetro viene automaticamente diviso in **4 segmenti numerati** (1, 2, 3, 4) visualizzati come cerchi arancioni sulla mappa video.

I segmenti sono numerati in ordine sequenziale lungo il perimetro del poligono disegnato.

### 2. Configurare le Direzioni

Nel pannello della tabella, per ogni ROI:

1. Clicca sul pulsante **"Direzioni"** della zona desiderata
2. Si aprirà una finestra di configurazione mostrando una griglia di pulsanti
3. Ogni pulsante rappresenta una direzione (es. `1→2` significa: entra dal segmento 1 ed esci dal segmento 2)
4. Clicca sui pulsanti per selezionare le direzioni da conteggiare:
   - I pulsanti **blu** (con testo nero) sono le direzioni **attive**
   - I pulsanti **grigi** (con testo grigio) sono **disattivati**

### 3. Conteggio Automatico

Una volta configurate le direzioni:
- Solo gli oggetti che **entrano** da un segmento e **escono** da un altro segmento specificato verranno conteggiati
- Se non sono specificate direzioni, tutti gli oggetti che entrano nella zona vengono conteggiati (comportamento originale)

## Esempio di Utilizzo

**Scenario**: Conteggiare solo i veicoli che attraversano l'intersezione da Nord a Sud

1. Disegna la ROI sull'intersezione
2. I segmenti verranno numerati automaticamente:
   - Segmento 1: Lato Nord
   - Segmento 2: Lato Est
   - Segmento 3: Lato Sud
   - Segmento 4: Lato Ovest

3. Apri la configurazione delle direzioni
4. Attiva solo la direzione `1→3` (da Nord a Sud)
5. Adesso verranno conteggiati solo i veicoli che entrano dal segmento 1 e escono dal segmento 3

## Struttura dei Dati (rois.json)

L'area di rilevamento conserva:

```json
{
  "id": 1770129600277,
  "label": "Intersezione A",
  "points": [
    {"x": 0.2, "y": 0.3},
    {"x": 0.8, "y": 0.3},
    {"x": 0.8, "y": 0.7},
    {"x": 0.2, "y": 0.7}
  ],
  "segments": 4,
  "directions": [
    {"from": 1, "to": 3},
    {"from": 2, "to": 4}
  ],
  "allowed_classes": [2, 5, 7]
}
```

### Campi:
- **segments**: Numero di segmenti in cui dividere il perimetro (default: 4)
- **directions**: Array di direzioni attive nel formato `{"from": numero, "to": numero}`

## Algoritmo di Tracking

Il sistema:

1. **Traccia il movimento**: Registra il primo segmento in cui è stato rilevato ogni oggetto
2. **Monitora la transizione**: Verifica quando l'oggetto si sposta verso un altro segmento
3. **Conta se valido**: Se la transizione corrisponde a una direzione configurata, l'oggetto viene conteggiato una sola volta
4. **Pulisce la history**: Quando si azzera il conteggio, la cronologia del movimento viene ripulita

## Note Importanti

- Un oggetto viene conteggiato **una sola volta** anche se attraversa più volte la zona
- Se un oggetto entra ed esce dalla zona senza completare una direzione configurata, non viene conteggiato
- Il conteggio si basa sul **centroide** della bounding box dell'oggetto
- Le direzioni configurate sono specifiche per ogni zona (ROI)

## Reset e Pulizia

Quando clicchi **"AZZERA CONTEGGI"**, verranno ripuliti:
- Tutti i conteggi degli oggetti
- La cronologia del movimento degli oggetti per tutte le zone
