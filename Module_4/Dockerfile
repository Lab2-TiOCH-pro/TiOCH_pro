# Użyj oficjalnego obrazu Python jako obrazu bazowego
FROM python:3.11

# Ustaw katalog roboczy w kontenerze
WORKDIR /app

# Skopiuj plik requirements.txt do katalogu roboczego
COPY requirements.txt .

# Zainstaluj zależności
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj resztę kodu aplikacji do katalogu roboczego
COPY ./app ./app

# Uruchomienie Spacy model download (jeśli jest potrzebny)
# Jeśli NERDetector używa konkretnego modelu Spacy, który trzeba pobrać,
# odkomentuj i dostosuj poniższą linię:
RUN python -m spacy download pl_core_news_sm && python -m spacy download xx_ent_wiki_sm

# Ujawnij port, na którym działa aplikacja
EXPOSE 8000

# Polecenie uruchamiające aplikację FastAPI z Uvicorn
# Zakładamy, że główny plik to main.py wewnątrz katalogu app,
# a instancja FastAPI nazywa się 'app'
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 