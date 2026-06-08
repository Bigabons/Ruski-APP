# Aplikacja do nauki rosyjskiego — podsumowanie projektu

Pod wyjazd do Kazachstanu i Kirgistanu. 2 miesiące, codziennie ~10–15 słówek + minimum gramatyki.
Nauka metodą powtórek (SRS). Cyrylica + transliteracja + tłumaczenie PL.

---

## Architektura

Klient–serwer, bo synchronizacja postępu między kompem a telefonem.

```
[Frontend: HTML/JS w przeglądarce]
   uczę się na Macu i na telefonie
            ↕  HTTP (JSON)
[Backend: FastAPI na Ubuntu]
   za Cloudflare Tunnel (jak reszta Twojego stacku)
            ↕
[Baza: SQLite]
   słówka + postęp nauki
```

- **Frontend** — prosta strona (jeden plik HTML lub mały zestaw). Pobiera porcję na dziś, wysyła oceny.
- **Backend** — FastAPI, kilka endpointów. To samo co już ogrywasz przy innych projektach.
- **Baza** — SQLite (plik na serwerze). Przy jednym userze i kilkuset słówkach w zupełności wystarcza, zero stawiania Postgresa.
- **Dostęp z zewnątrz** — Cloudflare Tunnel, tak jak ringostat.belica.site.

---

## Baza danych (SQLite, 2 tabele)

**words** — treść do nauki (wypełniana raz, potem dosypywana):
| pole | przykład |
|------|----------|
| id | 42 |
| ru | сколько стоит |
| translit | skolko stoit |
| pl | ile kosztuje |
| kategoria | zakupy |
| typ | fraza / slowo |

**progress** — stan nauki per słówko (aktualizowany przy każdej ocenie):
| pole | znaczenie |
|------|-----------|
| word_id | które słówko (FK do words) |
| repetitions | ile razy poprawnie z rzędu |
| interval_days | za ile dni następna powtórka |
| ease | współczynnik łatwości (SRS) |
| due_date | kiedy słówko znów wpada do kolejki |
| last_seen | ostatnia powtórka |

> Jeden user, więc bez logowania na start. Postęp wspólny dla wszystkich urządzeń — bo siedzi na serwerze. To rozwiązuje problem „komp vs telefon".

---

## Algorytm SRS

Uproszczony SM-2 (to co stoi za Anki):
- ocena **nie znam** → reset, słówko wraca od razu / dziś
- ocena **średnio** → krótki interwał
- ocena **znam** → interwał rośnie (1d → 3d → 7d → 16d ...), `ease` reguluje tempo

Każda ocena przelicza `interval_days`, `ease`, `due_date` i zapisuje do `progress`.

---

## Endpointy (FastAPI)

| metoda | ścieżka | po co |
|--------|---------|-------|
| GET | `/today` | porcja na dziś: zaległe powtórki + nowe słówka (limit np. 15) |
| POST | `/review` | zapis oceny jednego słówka (`word_id`, `ocena`) → przelicza SRS |
| GET | `/words` | lista wszystkich słówek (przeglądanie per kategoria) |
| POST | `/words` | dodanie nowego słówka (żebyś mógł dosypywać) |
| GET | `/stats` | postęp ogólny: ile opanowanych, seria dni |

---

## Frontend — ekrany

1. **Start** — „Ucz się dziś", licznik serii, postęp.
2. **Fiszka** — słówko (cyrylica + translit) → odsłonięcie PL → ocena (nie znam / średnio / znam).
3. **Przeglądanie** — lista per kategoria.
4. **Dodawanie** — prosty formularz nowego słówka (opcjonalnie).

Wymowa: wbudowany text-to-speech przeglądarki (`SpeechSynthesis`, język ru) — darmowe, bez plików audio.

---

## Kategorie słówek

- **podstawy** — powitania, tak/nie, proszę, dziękuję, przepraszam, liczby 0–1000
- **zakupy** — ceny, „ile kosztuje", „za drogo", woda, jedzenie, torba
- **hotel** — pokój, rezerwacja, klucz, ile nocy, wifi, śniadanie
- **auto / droga** — tankowanie, benzyna, policja drogowa, dokumenty, kierunki, parking
- **podróż** — dworzec, bilet, granica, taksówka, „nie rozumiem", „gdzie jest..."

Start: ~150–200 wpisów, potem dosypywanie.

---

## Stack

- Backend: **Python + FastAPI**, **SQLite** (przez sqlite3 albo SQLModel/SQLAlchemy)
- Frontend: **HTML + vanilla JS** (albo lekki framework, jak wolisz — ale vanilla wystarcza)
- Deploy: **systemd service** + **Cloudflare Tunnel**, jak reszta Twojego stacku
- Dev: lokalnie na M2 Max, potem wrzut na Ubuntu

---

## Kolejność budowy

1. Schemat bazy + seed startowego słownika (CSV/JSON → SQLite).
2. Backend FastAPI: `/today`, `/review`, logika SRS.
3. Frontend: fiszka + ocena, wpięcie w endpointy.
4. Tryb dzienny + statystyki + przeglądanie.
5. Dodawanie słówek, wymowa TTS.
6. Deploy na serwer + Cloudflare Tunnel.

---

## Do ustalenia na start

- Limit nowych słówek dziennie (proponuję 15) i ile powtórek max.
- Czy chcesz w ogóle minimalną ochronę endpointów (token w nagłówku), skoro to wystawione przez Tunnel — warto, nawet przy jednym userze.
- Notki gramatyczne: osobna tabela `grammar` czy na razie pomijamy i dodajemy później.
