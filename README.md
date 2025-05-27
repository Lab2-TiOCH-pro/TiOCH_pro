## Usługi i porty (`docker-compose`)

| Usługa              | Rola                           | Port lokalny | Port kontenera | Dostęp                                      |
|---------------------|--------------------------------|--------------|----------------|---------------------------------------------|
| **mongo**           | Baza danych (MongoDB)          | `27017`      | `27017`        | —                                           |
| **redis**           | Kolejka Redis (dla Celery)     | `6379`       | `6379`         | —                                           |
| **rabbitmq**        | Kolejka AMQP + UI              | `5672`       | `5672`         | —                                           |
|                     | Panel zarządzania RabbitMQ     | `15672`      | `15672`        | [http://localhost:15672](http://localhost:15672) |
| **extractor**       | API ekstrakcji tekstu (Moduł 2) | `8001`       | `8000`         | [http://localhost:8001/docs](http://localhost:8001/docs) |
| **datastore**       | API zarządzania dokumentami (Moduł 3) | `8002` | `8000`         | [http://localhost:8002/docs](http://localhost:8002/docs) |
| **detector-api**    | API detekcji danych wrażliwych (Moduł 4) | `8003` | `8000` | [http://localhost:8003/docs](http://localhost:8003/docs) |
| **detector-worker** | Celery Worker (Moduł 4)        | —            | —              | —                                           |
| **notifications**   | API powiadomień (Moduł 5)      | `8765`       | `8765`         | [http://localhost:8765/docs](http://localhost:8765/docs) |
| **ui**              | Interfejs użytkownika (Moduł 1) | `80`         | `80`           | [http://localhost](http://localhost)        |
