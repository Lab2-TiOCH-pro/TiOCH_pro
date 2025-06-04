from app.celery_app import celery
from app.sensitive_detector import SensitiveDataDetector
import os
import httpx
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import asyncio
import logging

# Get a logger instance
logger = logging.getLogger(__name__)

async def get_document(document_id: str) -> Dict[str, Any]:
    """
    Retrieves a document from module 3 database.
    
    Args:
        document_id: Document identifier
        
    Returns:
        Document in JSON format
        
    Raises:
        Exception: If document retrieval fails
    """
    try:
        module3_url = os.getenv("MODULE3_API_URL", "http://datastore_api:8000/api/documents/")
        url = f"{module3_url}{document_id}"
        
        # Użyj kontekstu async dla klienta HTTP
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            
        if response.status_code != 200:
            raise Exception(f"Error fetching document: HTTP {response.status_code} - {response.text}")
            
        return response.json()
    except httpx.RequestError as e:
        raise Exception(f"Network error while fetching document {document_id}: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to fetch document {document_id}: {str(e)}")

async def get_normalized_text(document_id: str):
    """
    Retrieves normalized text of a document from module 3.
    
    Args:
        document_id: Document identifier
        
    Returns:
        Tuple containing normalized text and document identifier
        
    Raises:
        Exception: If text retrieval fails
    """
    try:
        document = await get_document(document_id)
        
        normalized_text = document.get("normalizedText")
        if not normalized_text:
            raise Exception(f"Document {document_id} has no normalized text")
        
        document_identifier = document.get("metadata", {}).get("identifier", document_id)
        
        return normalized_text, document_identifier
    except Exception as e:
        raise Exception(f"Failed to get normalized text for document {document_id}: {str(e)}")

async def process_document(document_id: str) -> List[Dict[str, Any]]:
    """
    Processes a document from database, detects sensitive data and updates results in module 3.
    
    Args:
        document_id: Document identifier
        
    Returns:
        List of detected sensitive data
    """
    logger.info(f"process_document started for document_id: {document_id}")
    overall_start_time = time.time() # Start of the entire process_document
    try:
        # Get normalized document text
        logger.info(f"[process_document:{document_id}] Getting normalized text...")
        normalized_text, document_identifier = await get_normalized_text(document_id)
        logger.info(f"[process_document:{document_id}] Normalized text received (length: {len(normalized_text) if normalized_text else 0}). Identifier: {document_identifier}")
        
        # Perform sensitive data detection
        detector = SensitiveDataDetector()
        use_llm = bool(os.getenv("OPENAI_API_KEY"))
        
        logger.info(f"[process_document:{document_id}] Calling detector.detect() with use_llm={use_llm}...")
        detection_start_time = time.time()
        results = detector.detect(normalized_text, use_llm=use_llm)
        detection_duration = time.time() - detection_start_time
        logger.info(f"[process_document:{document_id}] detector.detect() took {detection_duration:.4f}s and returned {len(results) if results is not None else 'None'} items.")
        
        formatted_results = []
        for item in results:
            if "type" in item and "value" in item:
                formatted_item = {
                    "type": item["type"],
                    "value": item["value"],
                    "label": item.get("label", "UNKNOWN")  
                }
                formatted_results.append(formatted_item)
        
        # Calculate total processing time for the function
        total_processing_time = time.time() - overall_start_time
        
        # Prepare data for update in Module 3
        module3_url = os.getenv("MODULE3_API_URL", "http://datastore_api:8000/api/documents/")
        update_url = f"{module3_url}{document_id}"
        
        analysis_result_obj = {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "detectedItems": formatted_results,
            "analysisTime": detection_duration # Use specific detection_duration here
        }
        
        update_payload = {
            "analysisResult": analysis_result_obj,
            "processingTimeSeconds": total_processing_time # Use overall processing time here
        }
        
        # Send update to Module 3
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(update_url, json=update_payload)
        
        if response.status_code != 200:
            print(f"Error updating document {document_id} in Module 3: HTTP {response.status_code} - {response.text}")
        
        return formatted_results
    except Exception as e:
        logger.error(f"[process_document:{document_id}] CRITICAL - Error processing document: {str(e)}", exc_info=True)
        
        # In case of error, update analysis status to "failed"
        try:
            # processing_time_at_failure should still represent overall time up to failure
            processing_time_at_failure = time.time() - overall_start_time 
            error_analysis_result_obj = {
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "detectedItems": [],
                "analysisTime": None # Or a calculated value if detection part was attempted
            }
            error_payload = {
                "analysisResult": error_analysis_result_obj,
                "processingTimeSeconds": processing_time_at_failure
            }
            
            module3_url = os.getenv("MODULE3_API_URL", "http://datastore_api:8000/api/documents/")
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.patch(f"{module3_url}{document_id}", json=error_payload)
        except Exception as update_error:
            print(f"Failed to update error status for document {document_id}: {str(update_error)}")
        
        return []

@celery.task(bind=True, max_retries=3)
def detect_task(self, text: str, document_id: str = None, use_llm: bool = True):
    """
    Celery task for detecting sensitive data in text.
    
    Args:
        text: Text to analyze
        document_id: Optional document identifier for database update
        use_llm: Whether to use LLM model for detection
        
    Returns:
        List of detected sensitive data
    """
    task_id = self.request.id
    overall_task_start_time = time.time()
    logger.info(f"detect_task started. Task ID: {task_id}, Document ID: {document_id}, use_llm: {use_llm}, text length: {len(text) if text else 0}")
    detector = SensitiveDataDetector()
    
    try:
        # Perform detection
        logger.info(f"[detect_task:{task_id}] Calling detector.detect()...")
        detection_start_time = time.time()
        results = detector.detect(text, use_llm=use_llm)
        detection_duration = time.time() - detection_start_time
        logger.info(f"[detect_task:{task_id}] detector.detect() took {detection_duration:.4f}s and returned {len(results) if results is not None else 'None'} items.")
        
        # Ensure results are in the required format
        formatted_results = []
        for item in results:
            if "type" in item and "value" in item:
                formatted_item = {
                    "type": item["type"],
                    "value": item["value"],
                    "label": item.get("label", "UNKNOWN")
                }
                formatted_results.append(formatted_item)
        
        # If document_id is provided, update Module 3 database with results
        if document_id:
            try:
                # Calculate total task processing time
                total_task_processing_time = time.time() - overall_task_start_time
                
                # Prepare data for Module 3 API
                module3_url = os.getenv("MODULE3_API_URL", "http://datastore_api:8000/api/documents/")
                update_url = f"{module3_url}{document_id}"
                
                analysis_result_obj = {
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "detectedItems": formatted_results,
                    "analysisTime": detection_duration # Use specific detection_duration here
                }
                
                update_payload = {
                    "analysisResult": analysis_result_obj,
                    "processingTimeSeconds": total_task_processing_time # Use overall task time here
                }
                
                # Send update to Module 3
                with httpx.Client(timeout=30.0) as client:
                    response = client.patch(update_url, json=update_payload)
                
                if response.status_code != 200:
                    print(f"Error updating document {document_id} in Module 3: HTTP {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Exception updating document {document_id} in Module 3: {str(e)}")
                # Retry the task if updating the database fails
                self.retry(exc=e, countdown=5)
        
        return formatted_results
    except Exception as e:
        # Log total task time even in case of failure for retry block
        failed_task_duration = time.time() - overall_task_start_time 
        logger.error(f"[detect_task:{task_id}] CRITICAL - Error in detect_task (duration: {failed_task_duration:.4f}s): {str(e)}. Retry: {self.request.retries}/{self.max_retries}", exc_info=True)
        # Retry the task if processing fails
        self.retry(exc=e, countdown=5)
        return []
