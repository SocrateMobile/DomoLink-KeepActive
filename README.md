# DomoLink KeepActive

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/SocrateMobile/DomoLink-KeepActive)

**DomoLink KeepActive** est une intégration personnalisée pour Home Assistant conçue pour fiabiliser et stabiliser le comportement des entités domotiques (particulièrement **Zigbee** : **Zigbee2MQTT**, **ZHA**, **deCONZ / Dresden Elektronik**, etc.).

Elle crée une entité miroir (Proxy Sentinelle) qui :
1. **Maintient l'état actif** pendant une durée définie (*Hold Duration*) après que l'appareil physique a cessé d'émettre (ex: détecteur de présence/mouvement, contacteur de porte).
2. **Filtre les coupures transitoires** (*Grace Period*) : Empêche l'entité de clignoter en `unavailable` ou `unknown` pendant les mises à jour OTA Zigbee, les sauts de maillage (*mesh rediscovery*) ou les latences de réseau.
3. **Fournit un retour d'état optimiste immédiat** pour les actionneurs (switchs, prises, relais) pour une interface réactive sans effet rebond en attendant l'accusé de réception radio.

---

## 🎯 Compatibilité Universelle

Grâce à son architecture opérant directement sur le bus d'états de Home Assistant (`States Event Bus`) :
* **Zigbee2MQTT (Z2M)** : 100% compatible
* **ZHA (Zigbee Home Automation)** : 100% compatible
* **deCONZ / Phoscon (Dresden Elektronik)** : 100% compatible
* **Tout autre protocole (Z-Wave, Wi-Fi, ESPHome, BLE, MQTT)** : 100% compatible

---

## 🚀 Installation

### Méthode 1 : HACS (Recommandé)
1. Ouvrez **HACS** dans Home Assistant.
2. Cliquez sur les 3 points en haut à droite > **Dépôts personnalisés**.
3. Ajoutez l'URL de ce dépôt avec la catégorie **Intégration**.
4. Cliquez sur **Télécharger** puis redémarrez Home Assistant.

### Méthode 2 : Manuelle
1. Copiez le dossier `custom_components/domolink_keep_active` dans votre répertoire `<config>/custom_components/`.
2. Redémarrez Home Assistant.

---

## ⚙️ Configuration

1. Dans Home Assistant, allez dans **Paramètres** > **Appareils et services** > **Ajouter une intégration**.
2. Recherchez **DomoLink KeepActive**.
3. Renseignez les paramètres :
   * **Entité source** : Choisissez votre capteur ou actionneur (`binary_sensor.*`, `sensor.*`, `switch.*`).
   * **Durée de maintien actif (s)** : Nombre de secondes pendant lesquelles l'état reste `ON` après détection (ex: 30s ou 60s).
   * **Période de grâce indisponibilité (s)** : Délai d'attente avant d'accepter l'état `unavailable` (ex: 60s).
   * **Mode optimiste** : Activé par défaut pour les switchs.
4. Une nouvelle entité protégée est créée instantanément. Vous pouvez modifier ces délais à tout moment via le bouton **Configurer** de l'intégration.

---

## 📊 Exemple d'Usage

| Problème rencontré | Solution KeepActive |
| :--- | :--- |
| Un détecteur de présence repasse à `off` au bout de 5s alors qu'on est encore dans la pièce. | `hold_duration: 120` (reste `on` pendant 2 minutes après la dernière détection). |
| Une sonde de température Zigbee passe en `unavailable` pendant 15s lors des sauts de routeurs. | `grace_period: 60` (l'état reste stable et disponible). |
| Un interrupteur Zigbee met 2 secondes à confirmer son allumage, faisant vaciller le bouton dans Lovelace. | `optimistic: true` (l'UI prend l'état immédiatement sans vacillement). |
