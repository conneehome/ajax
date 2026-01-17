# Connee Alarm - Integrazione Home Assistant

![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)
![Version](https://img.shields.io/badge/version-1.3.10-blue.svg)

**Integrazione ufficiale Connee** - Sistema di sicurezza per Home Assistant.

## 🔐 Autorizzazione Richiesta

Questa integrazione richiede che il tuo account sia **attivato da Connee** per funzionare. 
L'accesso viene verificato automaticamente tramite il gateway Connee.

Per richiedere l'attivazione, contatta il supporto Connee.

## ✨ Funzionalità

- 🏠 **Alarm Control Panel** - Controllo completo arm/disarm del tuo hub
- 📟 **Sensori** - Tutti i sensori come entità Home Assistant
- 🔋 **Batteria e Segnale** - Attributi per monitorare lo stato dei dispositivi
- ⚡ **Polling Automatico** - Aggiornamenti ogni 10 secondi
- 🔄 **Token Refresh** - Rinnovo automatico della sessione
- 📊 **Dashboard Integrata** - Pannello Lovelace preconfigurato nella sidebar

## 📦 Installazione HACS

### Metodo 1: HACS Custom Repository

1. Apri HACS in Home Assistant
2. Vai su **Integrazioni** → **Menu** (3 puntini) → **Repository personalizzati**
3. Aggiungi URL: `https://github.com/conneehome/ajax`
4. Categoria: **Integrazione**
5. Clicca **Aggiungi**
6. Cerca "Connee Alarm" e installa
7. Riavvia Home Assistant

### Metodo 2: Installazione Manuale

1. Scarica lo ZIP da questo repository
2. Estrai la cartella `custom_components/connee_alarm` nella tua cartella `config/custom_components/`
3. Copia la cartella `www/connee_alarm` nella tua cartella `config/www/` (per il logo)
4. Riavvia Home Assistant

## ⚙️ Configurazione

1. Vai su **Impostazioni** → **Dispositivi e Servizi** → **Aggiungi Integrazione**
2. Cerca "Connee Alarm"
3. Inserisci:
   - **Email** - La tua email registrata
   - **Password** - La tua password
4. Seleziona l'hub se ne hai più di uno

**Nota:** Il tuo account deve essere attivato da Connee. Se ricevi errore "Accesso negato", contatta il supporto Connee.

## 📊 Dashboard

Dopo l'installazione, troverai automaticamente un pannello **"Connee Alarm"** nella sidebar di Home Assistant con:

- 🖼️ **Logo Connee** - Branding personalizzato
- 🛡️ **Controllo allarme** - Arm Away, Arm Home, Arm Night, Disarm
- 📟 **Griglia sensori** - Stati in tempo reale
- 🔋 **Monitor batterie** - Avvisi batterie scariche
- 📜 **Log eventi** - Ultimi 24h

## 🛡️ Dispositivi Supportati

| Dispositivo | Tipo Entità | Device Class |
|-------------|-------------|--------------|
| DoorProtect | binary_sensor | door |
| MotionProtect | binary_sensor | motion |
| GlassProtect | binary_sensor | vibration |
| LeaksProtect | binary_sensor | moisture |
| FireProtect | binary_sensor | smoke |
| Hub / Hub 2 | alarm_control_panel | - |
| KeyPad | sensor | - |
| SpaceControl | sensor | - |

## 📝 Esempio Automazione

```yaml
automation:
  - alias: "Arma allarme quando tutti escono"
    trigger:
      - platform: state
        entity_id: group.family
        to: "not_home"
    action:
      - service: alarm_control_panel.alarm_arm_away
        target:
          entity_id: alarm_control_panel.connee_alarm
```

## 🔔 Notifiche Push con Logo

```yaml
automation:
  - alias: "Notifica allarme con logo Connee"
    trigger:
      - platform: state
        entity_id: alarm_control_panel.connee_alarm
        to: "triggered"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🚨 ALLARME CONNEE"
          message: "Intrusione rilevata!"
          data:
            image: "https://raw.githubusercontent.com/conneehome/ajax/main/logo.png"
            thumbnail: "https://raw.githubusercontent.com/conneehome/ajax/main/logo.png"
            push:
              sound:
                name: default
                critical: 1
                volume: 1.0
```

## 🐛 Problemi?

Apri una issue su [GitHub](https://github.com/conneehome/ajax/issues)

## 📄 Licenza

MIT License - Connee Team
