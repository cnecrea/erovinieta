
<!-- Adaugă o ancoră la începutul paginii -->
<a name="top"></a>
# Întrebări frecvente
- [Cum să adaug integrarea în Home Assistant?](#cum-să-adaug-integrarea-în-home-assistant)
- [Ce senzori creează integrarea?](#ce-senzori-creează-integrarea)
- [Ce înseamnă starea „Da" / „Nu" la senzorul Rovinietă activă?](#ce-înseamnă-starea-da--nu-la-senzorul-rovinietă-activă)
- [De ce senzorul Restanțe treceri pod arată „Nu" deși am trecut podul?](#de-ce-senzorul-restanțe-treceri-pod-arată-nu-deși-am-trecut-podul)
- [Setarea „Istoric tranzacții" afectează trecerile de pod?](#setarea-istoric-tranzacții-afectează-trecerile-de-pod)
- [Cum actualizez opțiunile integrării fără a o reinstala?](#cum-actualizez-opțiunile-integrării-fără-a-o-reinstala)
- [Ce versiune de Home Assistant este necesară?](#ce-versiune-de-home-assistant-este-necesară)


## Cum să adaug integrarea în Home Assistant?

[⬆ Înapoi sus](#top)

**Răspuns:**
HACS (Home Assistant Community Store) permite instalarea și gestionarea integrărilor personalizate create de comunitate. Urmează pașii de mai jos:

  - **1. Asigură-te că HACS este instalat**
      - Verifică dacă HACS este deja instalat în Home Assistant.
      - Navighează la **Setări** > **Dispozitive și servicii** > **Integrări** și caută "HACS".
      - Dacă nu este instalat, urmează ghidul oficial de instalare: [HACS Installation Guide](https://hacs.xyz/docs/use).

  - **2. Găsește repository-ul extern**
      - Accesează pagina GitHub a integrării: [https://github.com/cnecrea/erovinieta](https://github.com/cnecrea/erovinieta).

  - **3. Adaugă repository-ul în HACS**
      - În Home Assistant, mergi la **HACS** din bara laterală.
      - Apasă pe butonul cu **cele trei puncte** din colțul din dreapta sus și selectează **Repositories**.
      - În secțiunea "Custom repositories", introdu URL-ul: `https://github.com/cnecrea/erovinieta`.
      - Selectează tipul: **Integration**.
      - Apasă pe **Add** pentru a adăuga repository-ul.

  - **4. Instalează integrarea**
      - După ce repository-ul a fost adăugat, mergi la **HACS** > **Integrations**.
      - Caută **CNAIR eRovinieta** și apasă **Download**.
      - Home Assistant îți va solicita să repornești sistemul.

  - **5. Configurează integrarea**
      - După repornire, mergi la **Setări** > **Dispozitive și servicii** > **Adaugă integrare**.
      - Caută **CNAIR eRovinieta** și introdu datele contului (username, parolă, interval de actualizare, istoric tranzacții).

> **Notă:**
> Asigură-te că Home Assistant și HACS sunt actualizate la cea mai recentă versiune pentru a evita erorile de compatibilitate.


## Ce senzori creează integrarea?

[⬆ Înapoi sus](#top)

**Răspuns:**
Integrarea creează automat următorii senzori:

| Senzor | Stare principală | Per vehicul |
|--------|------------------|-------------|
| **Date utilizator** | ID utilizator | Nu (1 per cont) |
| **Rovinietă activă ({nr})** | Da / Nu | Da |
| **Raport tranzacții** | Număr tranzacții | Nu (1 per cont) |
| **Restanțe treceri pod ({nr})** | Da / Nu | Da |
| **Treceri pod ({nr})** | Număr total treceri | Da |
| **Sold peaje neexpirate ({nr})** | Valoare sold | Da |

Senzorii marcați cu „Per vehicul = Da" se creează câte unul pentru fiecare vehicul din contul eRovinieta.


## Ce înseamnă starea „Da" / „Nu" la senzorul Rovinietă activă?

[⬆ Înapoi sus](#top)

**Răspuns:**
- **Da** — Vehiculul are o rovinietă cu data de expirare în viitor (rovinieta este încă valabilă).
- **Nu** — Vehiculul nu are rovinietă sau rovinieta a expirat.

Detaliile complete (categorie vignietă, dată început, dată sfârșit, zile rămase) sunt disponibile în atributele senzorului.


## De ce senzorul Restanțe treceri pod arată „Nu" deși am trecut podul?

[⬆ Înapoi sus](#top)

**Răspuns:**
Două motive posibile:
1. **Fereastra de 24 de ore**: Senzorul verifică doar trecerile neplătite din ultimele 24 de ore. Dacă trecerea a fost detectată cu mai mult de 24 de ore în urmă, nu va mai apărea.
2. **Intervalul de actualizare**: Datele se actualizează conform intervalului configurat (implicit: 1 oră). Dacă ai trecut podul cu câteva minute în urmă, este posibil ca datele să nu fi fost încă actualizate.

De asemenea, fiecare vehicul este monitorizat independent — restanțele unui vehicul nu afectează statusul celorlalte vehicule din cont.


## Setarea „Istoric tranzacții" afectează trecerile de pod?

[⬆ Înapoi sus](#top)

**Răspuns:**
**Nu.** Setarea „Istoric tranzacții (ani)" din configurare afectează exclusiv senzorul **Raport tranzacții**. Trecerile de pod sunt gestionate separat de API-ul CNAIR, cu un parametru propriu care nu este controlabil din integrare.


## Cum actualizez opțiunile integrării fără a o reinstala?

[⬆ Înapoi sus](#top)

**Răspuns:**
Mergi la **Setări** > **Dispozitive și Servicii** > **CNAIR eRovinieta** > **Configurare**. De acolo poți modifica:
- **Intervalul de actualizare** (în secunde, minim 300, maxim 86400).
- **Istoricul tranzacțiilor** (1–10 ani).

Modificările se aplică imediat, fără repornirea Home Assistant.


## Ce versiune de Home Assistant este necesară?

[⬆ Înapoi sus](#top)

**Răspuns:**
Integrarea este compatibilă cu **Home Assistant 2025.11** și versiunile ulterioare. Dacă folosești o versiune mai veche, este posibil să întâmpini erori de compatibilitate.
