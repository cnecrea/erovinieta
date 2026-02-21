
# Debugging pentru integrarea CNAIR eRovinieta

Acest ghid oferă pașii necesari pentru a activa logarea detaliată și pentru a analiza problemele din integrare.

---

## 1. Activează logarea detaliată

### Adaugă în `configuration.yaml`:
Pentru a activa logarea detaliată pentru integrare, editează fișierul `configuration.yaml` și adaugă următoarele:
```yaml
logger:
  default: warning
  logs:
    custom_components.erovinieta: debug
    homeassistant.const: critical
    homeassistant.loader: critical
    homeassistant.helpers.frame: critical
```

### Restartează sistemul
După ce ai salvat fișierul, repornește sistemul Home Assistant pentru ca modificările să fie aplicate.

---

## 2. Analizează logurile

### Localizarea logurilor
Logurile se află, de obicei, în fișierul `home-assistant.log`, în directorul principal al Home Assistant.

### Filtrarea logurilor
Pentru a găsi rapid informațiile relevante despre integrare, poți folosi comanda:
```bash
grep 'custom_components.erovinieta' home-assistant.log
```

### Ce să cauți în loguri:
- **`INFO`** — Mesaje informative: autentificare reușită, date actualizate cu succes, senzori adăugați.
- **`WARNING`** — Avertismente: vehicule cu date incomplete, tranzacții sau vehicule negăsite.
- **`ERROR`** — Erori: autentificare eșuată, erori API, erori la crearea senzorilor.
- **`DEBUG`** — Detalii granulare: răspunsuri brute de la API, cereri HTTP, valori intermediare.

### Exemple de mesaje relevante:
```
INFO     custom_components.erovinieta: Configurăm integrarea CNAIR eRovinieta pentru utilizatorul example@email.com
INFO     custom_components.erovinieta.coordinator: Datele au fost actualizate cu succes.
ERROR    custom_components.erovinieta.api: Cerere de autentificare eșuată: ConnectionError
WARNING  custom_components.erovinieta.coordinator: Date incomplete pentru vehicul: VIN=N/A, PlateNo=N/A
```

---

## 3. Probleme frecvente

### Autentificarea eșuează
- Verifică dacă username-ul și parola sunt corecte.
- Verifică dacă site-ul [erovinieta.ro](https://www.erovinieta.ro) este accesibil.
- Verifică logurile pentru mesajul exact de eroare.

### Senzorii nu apar
- Verifică dacă autentificarea a reușit (caută `Autentificarea a reușit` în loguri).
- Verifică dacă datele de la coordinator sunt disponibile (caută erori la `get_paginated_data` sau `get_user_data`).
- Asigură-te că ai cel puțin un vehicul înregistrat în contul eRovinieta.

### Starea senzorului „Rovinietă activă" este „Nu" deși ar trebui să fie „Da"
- Verifică atributul **Data sfârșit vignietă** al senzorului — data ar putea fi în trecut.
- Forțează o actualizare manuală a integrării din **Setări > Dispozitive și Servicii**.

### Restanțele treceri pod arată „Nu" deși am trecut podul
- Senzorul verifică doar trecerile neplătite din **ultimele 24 de ore**.
- Datele depind de frecvența de actualizare configurată (implicit: 1 oră).

---

## Notă
Asigură-te că toate configurațiile din `configuration.yaml` sunt corecte înainte de a începe procesul de debugging.

---

# Cum să postezi cod în discuții

Pentru a posta cod în mod corect și lizibil, utilizează blocuri de cod delimitate de trei backticks (```) urmate de limbajul codului. De exemplu, pentru YAML, folosește:

<pre>
```yaml
2025-01-20 15:35:12 INFO     custom_components.erovinieta: Configurăm integrarea CNAIR eRovinieta pentru utilizatorul test_user
2025-01-20 15:35:13 DEBUG    custom_components.erovinieta.coordinator: Începem actualizarea datelor în ErovinietaCoordinator...
2025-01-20 15:35:14 INFO     custom_components.erovinieta.coordinator: Datele au fost actualizate cu succes.
2025-01-20 15:35:15 ERROR    custom_components.erovinieta.api: Cerere de autentificare eșuată: ConnectionError
```
</pre>

Rezultatul va arăta astfel:

```yaml
2025-01-20 15:35:12 INFO     custom_components.erovinieta: Configurăm integrarea CNAIR eRovinieta pentru utilizatorul test_user
2025-01-20 15:35:13 DEBUG    custom_components.erovinieta.coordinator: Începem actualizarea datelor în ErovinietaCoordinator...
2025-01-20 15:35:14 INFO     custom_components.erovinieta.coordinator: Datele au fost actualizate cu succes.
2025-01-20 15:35:15 ERROR    custom_components.erovinieta.api: Cerere de autentificare eșuată: ConnectionError
```

## Pași pentru a posta cod:
1. Scrie ` ```yaml ` (trei backticks urmate de "yaml").
2. Adaugă codul tău pe liniile următoare.
3. Încheie cu alte trei backticks: ` ``` `.

Astfel, codul va fi formatat corespunzător și ușor de citit de ceilalți utilizatori.
