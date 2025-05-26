from app.celery_app import celery
from app.sensitive_detector import SensitiveDataDetector

@celery.task(bind=True)
def detect_task(self, text: str):
    """
    Celery task that runs sensitive data detection on the given text.
    """
    detector = SensitiveDataDetector()
    return detector.detect(text) 