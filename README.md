# LLM-Driven PDDL Domain Generator

Questo progetto è una pipeline automatizzata sviluppata con la libreria **`l2p`** per generare file PDDL (a partire da descrizioni in linguaggio naturale) tramite Large Language Models, integrando un robusto ciclo di validazione semantica e self-correction.

Il repository è strutturato come un framework modulare, progettato per gestire descrizioni di domini esterne, personalizzare i prompt e salvare gli output in modo ordinato.

## 🗺️ Roadmap & Architettura Futura

Attualmente il progetto si concentra sulla generazione robusta e validata dei domini (`main.py` funge da base per il primo modulo). L'evoluzione pianificata del framework prevede la trasformazione in una suite completa multi-script, strutturata come segue:

```text
├── main_domain_generator.py     # SCRIPT 1: Genera solo il file domain.pddl (Stato Attuale)
├── main_problem_generator.py    # SCRIPT 2: Genera solo il file problem.pddl (dato un dominio di riferimento)
├── main_joint_generator.py      # SCRIPT 3: Genera congiuntamente domain.pddl e problem.pddl
└── main_pipeline_solver.py      # SCRIPT 4: Pipeline completa (Generazione PDDL + Risoluzione)
```

---

## 📂 Struttura del Progetto

Il repository è organizzato nelle seguenti cartelle principali:
* **`domain_descriptions/`**: Contiene i file di testo (`.txt`) con le descrizioni dei domini in linguaggio naturale (es. `domain_farm_v1.txt`).
* **`domains/`**: Cartella di output in cui vengono salvati automaticamente i file `domain.pddl` generati e validati.
* **`custom_template/`**: Conserva i prompt personalizzati e le regole strutturate per guidare l'LLM nella generazione di Tipi, Predicati e Azioni.
* **`main_domain_generator.py`**: Script principale interattivo per la generazione, validazione ed eventuale correzione autonoma del dominio PDDL.

---

## 🚀 Modalità di Esecuzione e Modelli LLM

Il progetto offre due script di avvio distinti, pensati per ambienti di esecuzione differenti. L'elenco esatto dei modelli supportati è in continua evoluzione.

### 1. Esecuzione Locale (`main_domain_generator.py`)
Script pensato per l'uso su PC. Presenta un menu interattivo nel terminale per la scelta del modello. Possiamo suddividere i modelli a disposizione in due tipologie:
1) LLM caricati in locale: utilizziamo Ollama per per eseguire localmente modelli (esempi: *CodeLlama*, *CodeGemma*, *Mistral*, *Cogito*, *Ornith*, ecc.).
2) LLM in cloud: usufruiamo dei servizi IA offerti da Google Gemini API, che tramite un account ti permette di generare una chiave
per eseguire un loro LLM. In questo modo al tuo pc non verranno richieste risorse per eseguire LLM. Attenzione: un account gratuito ti concede un utilizzo limitato degli LLM (es: 20 richieste massime al giorno).
Il codice mette a disposizione svariati LLM di google (esempi: *gemini-3-flash-preview*,*gemini-3.5-flash*,**,ecc.).


### 2. Esecuzione Batch per Server/Cluster (`server_domain_generator.py`)
Script progettato per l'esecuzione batch tramite **Slurm** su cluster HPC. Gestisce modelli di grandi dimensioni (da 27B a 70B di parametri) sfruttando **Ollama**.
Modelli configurati per il cluster:
* **`qwen-27b`** (`qwen3.8:27b`) - Modello agentico bilanciato per iterazioni rapide.
* **`qwen-coder-30b`** (`qwen3-coder:30b`) - Modello MoE ultra-veloce specializzato nel codice.
* **`ornith-35b`** (`ornith-1.5:35b`) - Modello di fascia media basato su Qwen.
* **`llama-70b`** (`llama3.3:70b`) - Modello ad altissima capacità di ragionamento logico.

Puoi visualizzare le opzioni disponibili eseguendo:
```bash
python server_domain_generator.py --help
```

## 🛠️ Requisiti e Configurazione

### 1. Prerequisiti
* **Python 3.12+**
* **Ollama** installato e attivo (necessario se desideri usare un LLM in locale)
* **API Key di Google AI Studio** (necessario solo se desideri usare Gemini)
* **Access Token di Hugging Face** (necessario **solo** se usi `server_domain_generator.py` con modelli "gated" come Gemma)

Se intendi usare un LLM tramite Ollama, devi prima scaricare il modello in locale usando:
```bash
ollama run NomeModello
```
Ad esempio:
```bash
ollama run qwen2.5-coder:7b
```

### 2. Installazione delle Dipendenze
Clona la repository e installa i pacchetti necessari tramite il file requirements.txt:
```bash
git clone https://github.com/tuo-utente/robotic-farm-domain-generator.git
cd robotic-farm-domain-generator

# Creazione dell'ambiente virtuale
python3 -m venv .venv

# Attivazione dell'ambiente virtuale
# in Linux
source .venv/bin/activate
# in Windows
.venv\Scripts\activate.bat

# Aggiornamento pip e installazione delle dipendenze
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurazione del File .env
Copia il file di esempio .env.example per creare il tuo file di configurazione d'ambiente .env:
```bash
cp .env.example .env
```

Apri il file .env e inserisci la tua chiave API se usi Gemini:
```env
LLM_GEMINI_KEY="la_tua_chiave_api_qui"
```

## 💻 Guida all'Uso
Per prima cosa, Assicurati che la descrizione del tuo dominio sia salvata come file .txt all'interno della cartella domain_descriptions/ (e che il nome sia correttamente puntato in main_domain_generator.py)
### Esecuzione Locale
Assicurati che l'ambiente virtuale sia attivo ed esegui:
```bash
python main_domain_generator.py
```

Per l'esecuzione in un cluster i comandi possono cambiare in base alle istruzioni definite dal proprietario del cluster.

