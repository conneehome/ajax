# Connee Enterprise - Private Ajax Systems Integration

![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)
![Version](https://img.shields.io/badge/version-1.2.2-blue.svg)

**Use only for Connee** - Integrazione privata per sistemi di sicurezza Ajax Systems.

## 🔐 Autorizzazione Richiesta

Questa integrazione richiede che il tuo account sia **attivato da Connee** per funzionare. 
L'accesso viene verificato automaticamente tramite il gateway Connee.

Per richiedere l'attivazione, contatta il supporto Connee Enterprise.

## ✨ Funzionalità

- 🏠 **Alarm Control Panel** - Controllo completo arm/disarm del tuo hub Ajax
- 📟 **Sensori** - Tutti i sensori Ajax come entità Home Assistant
- 🔋 **Batteria e Segnale** - Attributi per monitorare lo stato dei dispositivi
- ⚡ **Polling Automatico** - Aggiornamenti periodici dello stato
- 🔄 **Token Refresh** - Rinnovo automatico della sessione

## 📦 Installazione HACS

### Metodo 1: HACS Custom Repository

1. Apri HACS in Home Assistant
2. Vai su **Integrazioni** → **Menu** (3 puntini) → **Repository personalizzati**
3. Aggiungi URL: `https://github.com/conneehome/ajax`
4. Categoria: **Integrazione**
5. Clicca **Aggiungi**
6. Cerca "Ajax Systems by Connee" e installa
7. Riavvia Home Assistant

### Metodo 2: Installazione Manuale

1. Scarica lo ZIP da questo repository
2. Estrai la cartella `custom_components/ajax` nella tua cartella `config/custom_components/`
3. Riavvia Home Assistant

## ⚙️ Configurazione

1. Vai su **Impostazioni** → **Dispositivi e Servizi** → **Aggiungi Integrazione**
2. Cerca "Ajax" o "Connee"
3. Inserisci:
   - **Email Ajax**
   - **Password Ajax**
4. Seleziona l'hub se ne hai più di uno

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
          entity_id: alarm_control_panel.ajax_alarm
```

## 🐛 Problemi?

Apri una issue su [GitHub](https://github.com/conneehome/ajax/issues)

## 📄 Licenza

MIT License - Connee Enterprise Team
