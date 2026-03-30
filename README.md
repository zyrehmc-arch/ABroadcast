# 🤖 Trading Channel Broadcaster Bot

Bot Telegram per inviare e programmare messaggi sul tuo canale.

---

## ⚡ Deploy su Railway (gratis, 5 minuti)

### 1. Crea account Railway
Vai su → https://railway.app e registrati con GitHub

### 2. Carica i file
- Clicca **"New Project"**
- Scegli **"Deploy from GitHub repo"** oppure **"Empty project"**
- Se usi Empty project: clicca **"+ Add service"** → **"GitHub Repo"**
- In alternativa usa il drag & drop dei file nella dashboard

### 3. Aggiungi le variabili d'ambiente
Nel tuo progetto Railway → **Variables** → aggiungi:

| Nome variabile | Valore |
|---|---|
| `BOT_TOKEN` | Il token di BotFather (es. `7812345:AAGk3f...`) |
| `CHANNEL_ID` | Il tuo canale (es. `@miocanale` o `-1001234567890`) |
| `ADMIN_ID` | Il tuo ID Telegram (vedi sotto come trovarlo) |
| `TIMEZONE` | `Europe/Rome` |

### 4. Deploy
Railway fa partire tutto automaticamente. Il bot è online!

---

## 🔍 Come trovare il tuo ADMIN_ID

1. Apri Telegram e cerca **@userinfobot**
2. Scrivi `/start`
3. Ti risponde con il tuo ID numerico (es. `123456789`)
4. Incollalo nella variabile `ADMIN_ID`

---

## 📱 Come usare il bot

1. Apri la chat con il tuo bot su Telegram
2. Scrivi `/start`
3. Apparirà il menu con 4 opzioni:

| Opzione | Cosa fa |
|---|---|
| 📤 **Invia ora** | Scrivi un messaggio → va subito sul canale |
| 🕐 **Programma** | Scrivi messaggio + data + ora + ripetizione |
| ⏰ **Coda** | Vedi tutti i messaggi programmati, puoi eliminarli |
| 📰 **News trading** | Invia news di mercato preimpostate |

---

## 💡 Suggerimenti

- Puoi usare la formattazione Markdown di Telegram nei messaggi:
  - `*testo*` → **grassetto**
  - `_testo_` → _corsivo_
  - `` `testo` `` → `codice`
- Il bot risponde solo a te (ADMIN_ID) per sicurezza
- I messaggi programmati sopravvivono ai riavvii del server su Railway
