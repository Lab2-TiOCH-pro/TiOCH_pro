# Notifications

Micro‑serwis **Django REST** umożliwiający wysyłanie powiadomień e‑mail oraz Slack za pośrednictwem jednego, prostego API.

---

## Wymagania

* **Python ≥ 3.10**
* **pip** lub **pipx**
* (Opcjonalnie) **Docker 24+**
* (Opcjonalnie) **Redis ≥ 6** – potrzebny, jeśli chcesz używać *Celery* do kolejkowania zadań

---

## Szybki start

1. **Przejdź do katalogu projektu**

   ```bash
   cd /ścieżka/do/notifications_project
   ```

2. **Uruchom**

   ```bash
   python -m venv venv
   # Linux / macOS
   source venv/bin/activate
   # Windows (PowerShell)
   .\venv\Scripts\Activate.ps1
   ```

3. **Zainstaluj zależności**

   ```bash
   pip install -r requirements.txt
   ```

4. **Uruchom aplikację przez Docker Compose**

   ```bash
   docker compose up --build        # uruchomienie interaktywne
   docker compose up --build -d     # uruchomienie w tle
   ```

   > **Uwaga (PowerShell)**
   > Jeśli pojawi się błąd dotyczący zasad wykonywania skryptów, pozwól jednorazowo na ich
   > uruchamianie:
   > `Set-ExecutionPolicy Unrestricted -Scope Process`

5. **Sprawdź API**

   * Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   * ReDoc:      [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

6. **Zatrzymaj kontenery**

   ```bash
   docker compose down        # zatrzymuje kontenery
   docker compose down -v     # + usuwa wolumeny (np. dane bazy)
   ```

   > **Uwaga (PowerShell)**
   > Jeśli wcześniej zmieniałeś *ExecutionPolicy*, przywróć domyślną wartość:
   > `Set-ExecutionPolicy Restricted -Scope Process`

---

## Endpointy API

| Metoda | Ścieżka                   | Opis                                                                                                                        |
| ------ | ------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| POST   | `/api/send-notification/` | Wysyła powiadomienie e‑mail i/lub Slack. W treści JSON należy podać przynajmniej jedno z pól `email` lub `slack_recipient`. |
| GET    | `/docs`                   | Interaktywna dokumentacja Swagger UI.                                                                                       |
| GET    | `/redoc`                  | Alternatywna dokumentacja ReDoc.                                                                                            |
| GET    | `/health/`                | Prosty *health‑check* aplikacji (jeśli endpoint jest włączony w `urls.py`).                                                 |

---

## Struktura projektu

```
notifications/
├── manage.py
├── requirements.txt
├── notifications/           # aplikacja Django
│   ├── views.py             # endpoint API
│   ├── schemas.py           # walidacja żądań
│   ├── services/            # logika wysyłki
│   │   ├── email.py
│   │   ├── slack.py
│   │   └── dispatcher.py
│   └── migrations/
└── notifications_project/   # konfiguracja Django
    ├── settings.py
    ├── urls.py
    └── wsgi.py
```
