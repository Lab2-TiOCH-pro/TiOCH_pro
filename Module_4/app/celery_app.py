import os
import time
import logging
from celery import Celery
from dotenv import load_dotenv, find_dotenv
import socket
import kombu.exceptions

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(find_dotenv())

# Celery broker and backend configuration
broker = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
backend = os.getenv("CELERY_RESULT_BACKEND", "rpc://")

# Funkcja do sprawdzania dostępności RabbitMQ
def wait_for_rabbitmq(host="rabbitmq", port=5672, timeout=120):
    """
    Czeka na dostępność RabbitMQ przed uruchomieniem Celery.
    
    Args:
        host: Host RabbitMQ (domyślnie 'rabbitmq')
        port: Port RabbitMQ (domyślnie 5672)
        timeout: Maksymalny czas oczekiwania w sekundach
        
    Returns:
        bool: True jeśli RabbitMQ jest dostępny, False w przeciwnym razie
    """
    start_time = time.time()
    logger.info(f"Oczekiwanie na dostępność RabbitMQ ({host}:{port})...")
    
    while True:
        try:
            # Próba nawiązania połączenia TCP z RabbitMQ
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                if result == 0:
                    logger.info(f"RabbitMQ jest dostępny po {time.time() - start_time:.1f} sekundach")
                    return True
        except Exception as e:
            logger.warning(f"Błąd podczas sprawdzania dostępności RabbitMQ: {e}")
        
        # Sprawdź czy nie przekroczono limitu czasu
        if time.time() - start_time > timeout:
            logger.error(f"Przekroczono limit czasu ({timeout}s) oczekiwania na RabbitMQ")
            return False
        
        # Odczekaj przed kolejną próbą
        time.sleep(2)

# Czekaj na dostępność RabbitMQ przed inicjalizacją Celery
rabbitmq_host = broker.split('@')[-1].split(':')[0].replace('/', '')
wait_for_rabbitmq(host=rabbitmq_host)

# Initialize Celery app and include the tasks module so tasks are registered
celery = Celery(__name__, broker=broker, backend=backend, include=['app.tasks'])

# Track task start events
celery.conf.task_track_started = True

# Dodanie konfiguracji dla retry
celery.conf.broker_connection_retry = True
celery.conf.broker_connection_retry_on_startup = True
celery.conf.broker_connection_max_retries = 10

# Automatically discover tasks from the included modules
celery.autodiscover_tasks(['app.tasks'])

