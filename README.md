# DomoLink KeepActive

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](https://github.com/SocrateMobile/DomoLink-KeepActive)

**DomoLink KeepActive** est une intégration pour Home Assistant conçue pour fiabiliser et stabiliser le comportement des entités domotiques (particulièrement **Zigbee** : **Zigbee2MQTT**, **ZHA**, **deCONZ**, etc.) et **maintenir éveillés les capteurs sur batterie pendant leurs mises à jour de firmware (OTA)**.

---

## ⚡ Nouveautés v1.2.0 : Moteur OTA Keep-Awake & Panneau Latéral

Les capteurs Zigbee sur batterie retournent en veille profonde (*deep sleep*) après quelques secondes, ce qui fait régulièrement échouer les mises à jour de firmware OTA qui nécessitent entre 10 et 90 minutes.

**DomoLink KeepActive v1.2.0 apporte la solution complète :**
* 📱 **Panneau latéral dédié dans Home Assistant** : Visualisez l'ensemble de vos appareils suivis, leur niveau de batterie, leur signal LQI et l'état de leur firmware.
* 🔘 **Bouton ON / OFF OTA Keep-Awake** par appareil : active le maintien éveillé actif avec compte à rebours, jauge de progression et compteur de pings.
* 🎚️ **Slider Durée Totale OTA (10 min à 90 min)** : réglage précis du temps de session avec arrêt automatique.
* 🎚️ **Slider Fréquence de Ping (1 s à 60 s)** : sollicite le capteur avant qu'il ne s'endorme pour garantir la continuité du transfert radio.
* 🚀 **Auto-déclenchement OTA** : détecte automatiquement les entités `update.*` et lance le maintien éveillé dès qu'une mise à jour démarre.
* ⚙️ **Gestion complète (Ajouter / Modifier / Supprimer)** : modifiez vos appareils directement depuis le panneau latéral ou depuis **Paramètres > Appareils et services**.

---

## 🛡️ Fonctionnalités Historiques Sentinelle (Toujours Actives)

Que le mode OTA soit actif ou non, KeepActive continue de protéger vos entités :
1. **Maintien d'état actif prolongé** (*Hold Duration*) : empêche un détecteur de repasser prématurément à `off`.
2. **Filtrage des micro-coupures** (*Grace Period*) : absorbe les états `unavailable` passagers lors des sauts de maillage radio ou redémarrages.
3. **Retour d'état optimiste immédiat** : supprime les temps de latence et le vacillement visuel sur les interrupteurs et prises.
4. **Regroupement d'appareil** : les entités sont proprement attachées à l'appareil de service **DomoLink KeepActive**.

---

## 🚀 Installation & Utilisation

1. Mettez à jour via **HACS** ou copiez le dossier `custom_components/domolink_keep_active` dans votre dossier `<config>/custom_components/`.
2. Redémarrez Home Assistant.
3. Ouvrez le panneau **DomoLink KeepActive** dans la barre latérale gauche.
4. Activez le bouton **« Maintien éveillé (OTA) »** sur le capteur que vous souhaitez mettre à jour, ou lancez la mise à jour directement depuis le bandeau de l'appareil !
