# CNAIR eRovinieta — Integrare Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.11%2B-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/cnecrea/erovinieta)](https://github.com/cnecrea/erovinieta/releases)
[![GitHub Stars](https://img.shields.io/github/stars/cnecrea/erovinieta?style=flat&logo=github)](https://github.com/cnecrea/erovinieta/stargazers)
[![Instalări](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/cnecrea/erovinieta/main/statistici/shields/descarcari.json)](https://github.com/cnecrea/erovinieta)
[![Ultima versiune](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/cnecrea/erovinieta/main/statistici/shields/ultima_release.json)](https://github.com/cnecrea/erovinieta/releases/latest)

Această integrare pentru Home Assistant oferă **monitorizare completă** pentru utilizatorii eRovinieta, permițându-le să verifice starea rovinietei, să monitorizeze trecerile de pod, tranzacțiile realizate și alte informații importante, direct din aplicația Home Assistant. 🚀

---

## 🌟 Caracteristici

### Senzor `Date utilizator`
  - **🔍 Informații detaliate despre utilizator**:
      - Afișează detalii complete ale utilizatorului din contul CNAIR eRovinieta.
  - **📊 Atribute disponibile**:
      - **Nume complet**: Numele și prenumele utilizatorului.
      - **CNP**: CNP-ul utilizatorului.
      - **Telefon de contact**: Telefonul de contact.
      - **Persoană fizică**: Da/Nu.
      - **Email utilizator**: Emailul asociat contului.
      - **Acceptă corespondența**: Dacă utilizatorul acceptă corespondența din partea CNAIR.
      - **Adresă**: Adresa completă a utilizatorului.
      - **Localitate și Județ**: Locația detaliată a utilizatorului.
      - **Țară**: Țara utilizatorului.


### Senzor `Rovinietă activă ({nr_înmatriculare})`
  - **🔍 Verificare stare rovinietă**:
      - Verifică dacă vehiculul deține o rovinietă valabilă și afișează detalii despre aceasta.
  - **🔑 Stare principală**:
      - **Da**: Vehiculul are rovinietă activă (data de expirare este în viitor).
      - **Nu**: Vehiculul nu are rovinietă sau aceasta a expirat.
  - **📊 Atribute disponibile**:
      - **Număr de înmatriculare**: Numărul de înmatriculare al vehiculului.
      - **VIN**: Numărul de serie (VIN) al vehiculului.
      - **Seria certificatului**: Seria certificatului vehiculului.
      - **Țara**: Țara vehiculului.
      - **Categorie vignietă**: Categoria vignietei asociate vehiculului.
      - **Data început vignietă**: Data începerii valabilității vignietei.
      - **Data sfârșit vignietă**: Data expirării vignietei.
      - **Expiră peste (zile)**: Numărul de zile rămase până la expirare.


### Senzor `Raport tranzacții`
  - **📊 Monitorizare tranzacții**:
      - Afișează un raport detaliat al tranzacțiilor realizate în perioada configurată.
  - **🔑 Stare principală**: Numărul total al tranzacțiilor.
  - **📊 Atribute disponibile**:
      - **Perioadă analizată**: Perioada de timp configurată (ex: „Ultimii 2 ani").
      - **Număr facturi**: Numărul total al facturilor.
      - **Suma totală plătită**: Suma totală plătită pentru tranzacțiile efectuate (RON).


### Senzor `Restanțe treceri pod ({nr_înmatriculare})`
  - **📊 Monitorizare restanțe per vehicul**:
      - Indică dacă există treceri de pod neplătite din ultimele 24 de ore **pentru vehiculul respectiv**.
      - Fiecare vehicul este monitorizat independent — o trecere neplătită a unui vehicul nu afectează statusul celorlalte vehicule din cont.
  - **🔑 Stare principală**:
      - **Da**: Există cel puțin o trecere de pod neplătită pentru acest vehicul.
      - **Nu**: Nu există treceri de pod neplătite.
  - **📊 Atribute disponibile**:
      - **Număr treceri neplătite**: Numărul total al trecerilor neplătite.
      - **Număr de înmatriculare**, **VIN**, **Seria certificatului**.
      - **Detalii per trecere**: Categorie, timp detectare, direcție, bandă.


### Senzor `Treceri pod ({nr_înmatriculare})`
  - **📊 Istoric treceri de pod per vehicul**:
      - Afișează istoricul complet al trecerilor de pod pentru vehiculul respectiv.
  - **🔑 Stare principală**: Numărul total al trecerilor de pod.
  - **📊 Atribute disponibile**:
      - **Număr total treceri**: Totalul trecerilor înregistrate.
      - **Număr de înmatriculare**, **VIN**, **Seria certificatului**.
      - **Detalii per trecere**: Categorie, timp detectare, direcție, bandă, valoare (RON), partener, metodă plată, valabilitate.


### Senzor `Sold peaje neexpirate ({nr_înmatriculare})`
  - **📊 Monitorizare sold peaje**:
      - Afișează valoarea totală a soldului pentru peajele neexpirate ale vehiculului.
  - **🔑 Stare principală**: Valoarea soldului peajelor neexpirate.
  - **📊 Atribute disponibile**:
      - **Sold peaje neexpirate**: Valoarea totală a soldului.


### Senzor `Licență`
  - **🔐 Sistem de licență** — fără licență validă se afișează doar senzorul „Licență necesară"
      - Integrarea utilizează un sistem de licențiere server-side care validează accesul la toți senzorii.
      - Cu licență validă: toți senzorii funcționează normal.
      - Fără licență: numai senzorul „Licență necesară" este disponibil.

---

## ⚙️ Configurare

### 🛠️ Interfața UI:
1. Adaugă integrarea din meniul **Setări > Dispozitive și Servicii > Adaugă Integrare**.
2. Caută **CNAIR eRovinieta** și introdu datele contului:
   - **Nume utilizator**: username-ul contului tău eRovinieta.
   - **Parolă**: parola asociată contului tău.
   - **Interval de actualizare**: Intervalul de actualizare în secunde (implicit: 3600 secunde, minim: 300, maxim: 86400).
   - **Istoric tranzacții**: Selectează câți ani de tranzacții dorești să aduci (1–10, implicit: 2 ani).
3. Apasă **Salvează** pentru a finaliza configurarea.
4. **Licență**: Integrarea necesită o licență validă. Poți achiziționa una de la [hubinteligent.org/licenta/erovinieta](https://hubinteligent.org/licenta/erovinieta). Licența se introduce din **OptionsFlow** (Setări > Dispozitive și Servicii > CNAIR eRovinieta > Configurare).

### 🔧 Modificare opțiuni:
După instalare, poți modifica intervalul de actualizare și istoricul de tranzacții din **Setări > Dispozitive și Servicii > CNAIR eRovinieta > Configurare**.

### Observații:
- Asigură-te că ai introdus corect datele de autentificare.
- Setarea „Istoric tranzacții" afectează doar senzorul **Raport tranzacții**. Trecerile de pod sunt gestionate separat de API-ul CNAIR.

---

## ✅ Cerințe

- **Cont CNAIR eRovinieta** — cu nume de utilizator și parolă
- **Home Assistant** — versiunea 2025.11 sau mai nouă
- **Licență** validă — [hubinteligent.org/licenta/erovinieta](https://hubinteligent.org/licenta/erovinieta)

---

## 🚀 Instalare

### 💡 Instalare prin HACS:
1. Adaugă [depozitul personalizat](https://github.com/cnecrea/erovinieta) în HACS. 🛠️
2. Caută integrarea **CNAIR eRovinieta** și instaleaz-o. ✅
3. Repornește Home Assistant și configurează integrarea. 🔄

### ✋ Instalare manuală:
1. Clonează sau descarcă [depozitul GitHub](https://github.com/cnecrea/erovinieta). 📂
2. Copiază folderul `custom_components/erovinieta` în directorul `custom_components` al Home Assistant. 🗂️
3. Repornește Home Assistant și configurează integrarea. 🔧

---

## ✨ Exemple de utilizare

### 🔔 Automatizare pentru expirarea rovinietei:
Creează o automatizare pentru a primi notificări când rovinieta expiră în 10 zile.

```yaml
alias: Notificare expirare rovinietă
description: Notificare atunci când rovinieta expiră în 10 zile
mode: single
triggers:
  - entity_id: sensor.erovinieta_vehicul_[nr_inmatriculare]
    attribute: Expiră peste (zile)
    below: 10
    trigger: numeric_state
conditions: []
actions:
  - data:
      title: Rovinieta expiră curând!
      message: >-
        Rovinieta vehiculului {{ state_attr('sensor.erovinieta_vehicul_[nr_inmatriculare]',
        'Număr de înmatriculare') }} va expira în {{
        state_attr('sensor.erovinieta_vehicul_[nr_inmatriculare]',
        'Expiră peste (zile)') }} zile!
    action: notify.notify
```

### 🔔 Automatizare pentru rovinietă expirată:
Creează o automatizare care te avertizează imediat ce rovinieta unui vehicul devine inactivă.

```yaml
alias: Notificare rovinietă expirată
description: Notificare atunci când rovinieta unui vehicul devine inactivă
mode: single
triggers:
  - entity_id: sensor.erovinieta_vehicul_[nr_inmatriculare]
    to: "Nu"
    trigger: state
conditions: []
actions:
  - data:
      title: Rovinietă expirată!
      message: >-
        Vehiculul {{ state_attr('sensor.erovinieta_vehicul_[nr_inmatriculare]',
        'Număr de înmatriculare') }} nu mai are rovinietă activă!
    action: notify.notify
```

### 🔔 Automatizare pentru restanțe la trecerile de pod:
Creează o automatizare pentru a primi notificări atunci când există treceri de pod neplătite.

```yaml
alias: Notificare restanțe treceri pod
description: Notificare atunci când există treceri de pod neplătite
mode: single
triggers:
  - entity_id: sensor.erovinieta_plata_treceri_pod_[nr_inmatriculare]
    to: "Da"
    trigger: state
conditions: []
actions:
  - data:
      title: Restanțe la treceri pod!
      message: >-
        Vehiculul {{ state_attr('sensor.erovinieta_plata_treceri_pod_[nr_inmatriculare]',
        'Număr de înmatriculare') }} are {{
        state_attr('sensor.erovinieta_plata_treceri_pod_[nr_inmatriculare]',
        'Număr treceri neplătite') }} treceri de pod neplătite!
    action: notify.notify
```

### 🔍 Card pentru Dashboard:
Afișează datele despre utilizator, vehicul și tranzacții pe interfața Home Assistant.

```yaml
type: entities
title: Monitorizare eRovinieta
entities:
  - entity: sensor.erovinieta_date_utilizator_[username]
    name: Date Utilizator
  - entity: sensor.erovinieta_vehicul_[nr_inmatriculare]
    name: Rovinietă activă
  - entity: sensor.erovinieta_plata_treceri_pod_[nr_inmatriculare]
    name: Restanțe treceri pod
  - entity: sensor.erovinieta_treceri_pod_[nr_inmatriculare]
    name: Treceri pod
  - entity: sensor.erovinieta_sold_peaje_neexpirate_[nr_inmatriculare]
    name: Sold peaje neexpirate
  - entity: sensor.erovinieta_raport_tranzactii_[username]
    name: Raport tranzacții
  - entity: sensor.erovinieta_[username]_licenta
    name: Licență
```

---

## 📁 Structura fișierelor

```
custom_components/erovinieta/
├── __init__.py          # Setup/unload integrare (runtime_data, licență)
├── api.py               # eRovinietzApiClient — autentificare, GET/POST
├── config_flow.py       # ConfigFlow + OptionsFlow (autentificare, licență)
├── const.py             # Constante și URL-uri API
├── coordinator.py       # DataUpdateCoordinator — fetch date
├── diagnostics.py       # Diagnostics pentru troubleshooting
├── helpers.py           # Funcții utilitare
├── license.py           # Manager licență (server-side v3.3, Ed25519, HMAC-SHA256)
├── manifest.json        # Metadata integrare
├── sensor.py            # Clase senzori (utilizator, rovinietă, tranzacții, etc.)
├── strings.json         # Traduceri implicite
└── translations/
    ├── en.json          # Traduceri engleză
    └── ro.json          # Traduceri române
```

---

## ☕ Susține dezvoltatorul

Dacă ți-a plăcut această integrare și vrei să sprijini munca depusă, **invită-mă la o cafea**! 🫶
Nu costă nimic, iar contribuția ta ajută la dezvoltarea viitoare a proiectului. 🙌

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Susține%20dezvoltatorul-orange?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/cnecrea)

Mulțumesc pentru sprijin și apreciez fiecare gest de susținere! 🤗

---

## 🧑‍💻 Contribuții

Contribuțiile sunt binevenite! Simte-te liber să trimiți un pull request sau să raportezi probleme [aici](https://github.com/cnecrea/erovinieta/issues).
