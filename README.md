# TiOCH_pro
🔧 Infrastruktura
Usługa	Port kontenera	Port hosta	Opis
mongo	27017	27017	Baza danych MongoDB (GridFS)
redis	6379	6379	Kolejka Redis (dla Celery)
rabbitmq	5672	5672	Protokół AMQP (Celery)
15672	15672	UI RabbitMQ (http://localhost:15672)

🔙 Backend (API)
Usługa	Port kontenera	Port hosta	Opis
extractor_api	8000	8001	Moduł 2 – ekstrakcja tekstu z plików
datastore_api	8000	8002	Moduł 3 – zarządzanie dokumentami (MongoDB + API)
detector_api	8000	8003	Moduł 4 – detekcja danych wrażliwych
detector_worker	—	—	Worker Celery dla Modułu 4 (brak portu, działa w tle)
notifications_api	8000	8765	Moduł 5 – API powiadomień e‑mail i Slack

🖥️ Frontend
Usługa	Port kontenera	Port hosta	Opis
tioch_ui	80	80	Moduł 1 – interfejs React (http://localhost)
