# DomoLink KeepActive

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![Version](https://img.shields.io/badge/version-1.2.5-blue.svg)](https://github.com/SocrateMobile/DomoLink-KeepActive)

**DomoLink KeepActive** est une intégration pour Home Assistant conçue pour fiabiliser et stabiliser le comportement des entités domotiques (particulièrement **Zigbee** : **Zigbee2MQTT**, **ZHA**, **deCONZ**, etc.) et **maintenir éveillés les capteurs sur batterie pendant leurs mises à jour de firmware (OTA)**.

---

## ⚡ Défibrillateur OTA Keep-Awake & Panneau Latéral

Les capteurs Zigbee sur batterie (Sleepy End Devices) retournent en veille profonde (*deep sleep*) après quelques secondes d'inactivité, ce qui interrompt ou fait régulièrement échouer les mises à jour de firmware OTA qui nécessitent entre 10 et 90 minutes.

**DomoLink KeepActive apporte la solution complète :**
* 📱 **Panneau latéral dédié dans Home Assistant** : Visualisez l'ensemble de vos appareils suivis, leur niveau de batterie, leur signal radio et l'état de leur firmware.
* 🔘 **Défibrillateur OTA Keep-Awake par appareil** : Active le maintien éveillé actif avec compte à rebours, jauge de progression en pourcentage et compteur d'impulsions.
* ⚡ **Pings radio instantanés et non-bloquants** : Déclenchez des pings manuels avec retour visuel immédiat, expédiés en arrière-plan sans bloquer Home Assistant.
* 🔥 **Mode Salve rapide (15s)** : Envoie 1 impulsion par seconde pendant 15 secondes pour réveiller le capteur pendant la phase critique de préparation (*Preparing*).
* 🎚️ **Slider Durée Totale OTA (10 min à 90 min)** : Réglage précis du temps de session avec arrêt automatique (ou prolongation paramétrable).
* 🎚️ **Slider Fréquence de Ping (1 s à 60 s)** : Sollicite le capteur avant qu'il ne s'endorme pour garantir la continuité du transfert radio.
* 🚀 **Auto-déclenchement OTA & Arrêt à 100%** : Détecte automatiquement les entités `update.*`, lance le maintien dès qu'une mise à jour démarre, et coupe automatiquement le défibrillateur dès que le déploiement atteint 100%.
* ⚙️ **Gestion complète (Ajouter / Modifier / Supprimer)** : Configurez vos appareils directement depuis le panneau latéral ou depuis **Paramètres > Appareils et services**.

---

## 💡 Trucs & Astuces : Mises à jour de firmware (OTA)

> [!TIP]
> **Problème rencontré : La mise à jour affiche « Préparation » (*Preparing*) pendant 1 à 2 minutes puis s'arrête et revient en « Mise à jour disponible » ?**
> 
> C'est le symptôme typique d'un capteur endormi dont la table de routage Zigbee s'est mise en sommeil avant d'avoir reçu le premier paquet du firmware.
> 
> **Procédure recommandée (rapide et sans perte de configuration) :**
> 1. **Réappairer le capteur sans le supprimer** : Ne supprimez **pas** l'appareil de Home Assistant. Passez simplement votre coordinateur Zigbee (ZHA ou Zigbee2MQTT) en mode recherche/appairage, puis maintenez le bouton physique du capteur quelques secondes jusqu'au clignotement de la LED. Le capteur est réassocié instantanément en conservant son identifiant, son historique et toutes ses automatisations.
> 2. **Lancer la mise à jour via DomoLink KeepActive** : Cliquez sur le bouton **« ⚡ Mettre à jour »** (ou activez le défibrillateur OTA).
> 3. **Provoquer le premier réveil radio** : Dès que l'état passe sur *« Préparation »* (*Preparing*), cliquez sur **« 🔥 Salve 15s »** (ou **« ⚡ Ping »**) et **appuyez 1 fois brièvement sur le bouton physique du capteur** (ou passez la main devant s'il s'agit d'un radar/capteur de présence). 
> 4. **Distance idéale avec la clé Zigbee** : Si l'appareil est facilement déplaçable, approchez-le idéalement entre **1 et 2 mètres** de votre coordinateur (clé Zigbee) ou d'un routeur puissant. *Astuce* : évitez d'être collé à moins de 30 cm (risque de saturation radio RF) ou à plus de 5 mètres avec des obstacles (les pertes de paquets ralentissent et risquent d'interrompre l'OTA).
> 
> Le capteur captera immédiatement le bloc d'en-tête OTA et la jauge de progression s'enclenchera jusqu'à 100% !

---

## 🛡️ Fonctionnalités Historiques Sentinelle (Toujours Actives)

Que le mode OTA soit actif ou non, KeepActive continue de fiabiliser vos entités :
1. **Maintien d'état actif prolongé** (*Hold Duration*) : Empêche un détecteur de repasser prématurément à `off`.
2. **Filtrage des micro-coupures** (*Grace Period*) : Absorbe les états `unavailable` passagers lors des sauts de maillage radio ou redémarrages.
3. **Retour d'état optimiste immédiat** : Supprime les temps de latence et le vacillement visuel sur les interrupteurs et prises.
4. **Regroupement d'appareil** : Les entités sont proprement rattachées à l'appareil de service **DomoLink KeepActive**.

---

## 🚀 Installation & Utilisation

1. Mettez à jour via **HACS** (Dépôt personnalisé) ou copiez le dossier `custom_components/domolink_keep_active` dans votre dossier `<config>/custom_components/`.
2. Redémarrez Home Assistant.
3. Ouvrez le panneau **DomoLink KeepActive** dans la barre latérale gauche.
4. Activez le bouton **« ⚡ Activer le défibrillateur OTA »** sur le capteur à mettre à jour, ou lancez la mise à jour directement depuis le bandeau de l'appareil !
