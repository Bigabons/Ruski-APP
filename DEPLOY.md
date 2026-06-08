# Deploy przez Coolify

## 1. GitHub

```bash
cd "/Users/maciej/Desktop/Rosyjski App"
git init
git add .
git commit -m "init"
git remote add origin git@github.com:TWOJ_USER/rosyjski-app.git
git push -u origin main
```

## 2. Coolify — nowa aplikacja

1. **New Resource → GitHub → wybierz repo**
2. Build Pack: **Dockerfile** (wykryje automatycznie)
3. Port: `8000`
4. Domena: np. `rosyjski.belica.site` (Coolify sam obsłuży certyfikat)

## 3. Persistent volume (baza danych!)

W Coolify → zakładka **Storages** dodaj:

| Source path (host) | Destination path (container) |
|--------------------|------------------------------|
| `/data/rosyjski`   | `/data`                      |

Typ: **Directory**

## 4. Zmienne środowiskowe

W Coolify → zakładka **Environment Variables**:

| Zmienna       | Wartość          |
|---------------|------------------|
| `DATA_DIR`    | `/data`          |
| `PIN_MACIEJ`  | twój PIN         |
| `PIN_DOMINIKA`| pin Dominiki     |

> ⚠️ Bez `DATA_DIR=/data` baza będzie w kontenerze i zniknie przy każdym redeploy!

## 5. Deploy

Kliknij **Deploy**. Coolify:
- zbuduje obraz z Dockerfile
- uruchomi `python seed_db.py && uvicorn main:app ...`
- baza zostanie w `/data/rosyjski.db` na hoście

Kolejne deploye (nowe słówka, bugfixy) — `git push`, Coolify sam przebuduje. Baza przeżyje, bo jest na volume.

---

## Zmiana PINu po deployu

W Coolify dodaj/zmień zmienną `PIN_MACIEJ` lub `PIN_DOMINIKA` i zrób redeploy.
Istniejący user nie zostanie nadpisany (seed_db.py sprawdza `already exists`).

Żeby zmienić PIN istniejącego usera — przez Coolify Terminal lub SSH:

```bash
docker exec -it <container_name> python -c "
from auth import hash_pin
from database import get_conn
conn = get_conn()
conn.execute(\"UPDATE users SET pin_hash=? WHERE name=?\", (hash_pin('NOWY_PIN'), 'Maciej'))
conn.commit()
print('OK')
"
```

---

## Dodawanie słówek

Najprościej przez SQLite na hoście:

```bash
sqlite3 /data/rosyjski/rosyjski.db \
  "INSERT INTO words (ru,translit,pl,kategoria,typ) VALUES ('слово','slovo','słowo','podstawy','slowo');"
```

Albo dorzuć do `seed/words.json` i zrób redeploy — `seed_db.py` doda nowe, pominie istniejące.
