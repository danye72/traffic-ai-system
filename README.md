# Traffic AI System 🚦🤖

Un sistema professionale per il monitoraggio e il conteggio dei flussi di traffico in tempo reale, basato su **YOLOv8** e **FastAPI**. Il sistema permette di definire aree di interesse (ROI) interattive e applicare filtri di conteggio granulari per ogni singola zona.

## ✨ Caratteristiche principali

* **Rilevamento Multiclasse:** Monitoraggio simultaneo di Auto, Persone, Moto, Bus e Camion tramite YOLOv8.
* **Zone Interattive:** Disegna poligoni personalizzati direttamente sul flusso video tramite l'interfaccia web.
* **Filtri per Zona:** Possibilità di decidere cosa contare in ogni area (es. "conta solo Bus nella corsia gialla").
* **Conteggio Direzionale:** Configura direzioni di movimento specifiche per ogni zona (es. conta solo gli oggetti che entrano dal Segmento 1 e escono dal Segmento 3).
* **Stato Visivo Dinamico:** La zona nel video e la riga in tabella diventano verdi solo quando viene rilevato un oggetto *abilitato* e *selezionato* per quell'area.
* **Pannello AI Avanzato:** Regolazione live di Confidenza, Contrasto (CLAHE) e risoluzione del modello (320px - 640px).
* **Debug Mode:** Switch per visualizzare i Box di rilevamento e gli ID univoci di tracciamento degli oggetti (Object Tracking).
* **Localizzazione:** Interfaccia utente interamente in lingua italiana.

## 🛠️ Architettura Tecnica

* **Backend:** FastAPI (Python), OpenCV, Ultralytics (YOLOv8), Shapely.
* **Frontend:** React (Vite), Axios.
* **Containerizzazione:** Docker & Docker Compose.

---

## 🚀 Installazione e Avvio Rapido

### 1. Prerequisiti
* **Docker** e **Docker Compose** installati.
* Un video di test denominato `video.mp4` posizionato nella cartella `backend/data/`.

### 2. Clonazione e Avvio
```bash
git clone [https://github.com/danye72/traffic-ai-system.git](https://github.com/danye72/traffic-ai-system.git)
cd traffic-ai-system
docker compose up --build -d
```
### 3. Accesso al Sistema
Una volta avviati i container, il sistema è raggiungibile ai seguenti indirizzi:

* **Interfaccia Web (Frontend):** `http://localhost:5173`
* **Documentazione API (Backend):** `http://localhost:8000/docs`

---

## 📖 Guida all'uso

1.  **Ottimizzazione Immagine:** Regola lo slider **Contrasto (CLAHE)** per migliorare il rilevamento in condizioni di luce difficile o video sottoesposti.
2.  **Creazione Zone:** Clicca sul video per posizionare i punti del poligono (minimo 3). Digita il nome della zona (es. "Corsia 1") e clicca su **AGGIUNGI ZONA**.
3.  **Configurazione Filtri:** Nella tabella, usa i tasti **P, A, M, B, C** per abilitare/disabilitare il conteggio di Persone, Auto, Moto, Bus o Camion per ogni specifica area.
4.  **Conteggio Direzionale:** Per ogni zona, clicca su **"Direzioni"** per configurare i percorsi di movimento da conteggiare:
    - I segmenti sono numerati automaticamente (1, 2, 3, 4) lungo il perimetro della zona
    - Seleziona le direzioni desiderate (es. 1→3) per conteggiare solo gli oggetti che seguono quel percorso
    - Se non configuri alcuna direzione, tutti gli oggetti saranno conteggiati
5.  **Verifica Rilevamento:** Attiva **"Mostra Box Rilevamento"** per visualizzare i rettangoli di tracking e assicurarti che l'IA stia identificando correttamente i target.
6.  **Gestione Dati:** Usa il tasto **AZZERA CONTEGGI** per resettare le statistiche mantenendo le zone configurate.

### 📈 Conteggio Direzionale - Esempio Pratico

**Scenario:** Contare solo i veicoli che attraversano l'intersezione da Nord a Sud

1. Disegna una ROI attorno all'intersezione
2. Visualizzerai 4 segmenti numerati: 
   - 1 (Nord - alto), 2 (Est - destra), 3 (Sud - basso), 4 (Ovest - sinistra)
3. Clicca sul pulsante **"Direzioni"** della zona
4. Attiva solo il pulsante **"1→3"** (blu/attivo)
5. Adesso verranno conteggiati solo i veicoli che entrano dal segmento 1 (Nord) ed escono dal segmento 3 (Sud)

**Consulta:** [DIRECTION_COUNTING_GUIDE.md](DIRECTION_COUNTING_GUIDE.md) per una guida completa.

---

## 📝 Note Tecniche
* **Salvataggio Dati:** Le configurazioni delle zone e i filtri impostati vengono salvati automaticamente nel file `backend/config/rois.json`.
* **Tracking ID:** Il sistema utilizza l'ID univoco assegnato da YOLOv8 per garantire che ogni oggetto (veicolo o persona) venga contato una sola volta per ogni zona, evitando duplicati.
* **Performance:** * Se il sistema risulta rallentato, seleziona **320px** come Risoluzione AI.
  * Per la massima precisione su oggetti lontani o piccoli (es. Bus in fondo alla strada), utilizza **640px**.

---

Progetto sviluppato per il monitoraggio intelligente e l'analisi dei flussi di traffico.
