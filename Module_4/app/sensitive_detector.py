from typing import List, Dict, Any
from app.regex_detector import RegexDetector
from app.llm import LLMDetector

class SensitiveDataDetector:
    """
    Optimized wrapper for sensitive data detection using RegexDetector and LLMDetector.
    """
    def __init__(self):
        self.regex = RegexDetector()
        self.llm = LLMDetector()

    def detect(self, text: str, use_llm: bool = True) -> List[Dict[str, Any]]:
        """
        Detects sensitive data in text by combining results from regex and LLM.
        
        Args:
            text: Text to analyze
            use_llm: Whether to use LLM model for detection (default True)
            
        Returns:
            List of detected sensitive data in required format
        """
        all_raw_results: List[Dict[str, Any]] = []
        
        # Step 1: Collect LLM results
        if use_llm:
            try:
                llm_detections = self.llm.detect(text)
                for item in llm_detections:
                    if item.get("value", "").strip():
                        item["source"] = "llm"
                        all_raw_results.append(item)
            except Exception as e:
                print(f"LLM detection error: {str(e)}")
        
        # Step 2: Collect Regex results
        try:
            regex_detections = self.regex.detect(text)
            for item in regex_detections:
                if item.get("value", "").strip():
                    item["source"] = "regex"
                    all_raw_results.append(item)
        except Exception as e:
            print(f"Regex detection error: {str(e)}")

        # Step 3: Deduplication - Stage 1 (normalized key, LLM priority)
        stage1_unique_items: List[Dict[str, Any]] = []
        seen_normalized = set()

        # Process LLM results first
        for r in [res for res in all_raw_results if res["source"] == "llm"]:
            original_value = r.get("value", "")
            normalized_value = original_value.strip().lower()
            item_type = r.get("type", "other")
            key = (normalized_value, item_type)

            if key not in seen_normalized:
                seen_normalized.add(key)
                stage1_unique_items.append({
                    "type": item_type,
                    "value": original_value,
                    "label": r.get("label", "UNKNOWN"),
                    "source": "llm"
                })

        # Then process regex results
        for r in [res for res in all_raw_results if res["source"] == "regex"]:
            original_value = r.get("value", "")
            normalized_value = original_value.strip().lower()
            item_type = r.get("type", "other")
            key = (normalized_value, item_type)

            if key not in seen_normalized:
                seen_normalized.add(key)
                stage1_unique_items.append({
                    "type": item_type,
                    "value": original_value,
                    "label": r.get("label", "UNKNOWN"),
                    "source": "regex"
                })
        
        # Step 4: Deduplication - Stage 2 (substring/overlap handling)
        # Sort by value length (descending), then by source (LLM preferred)
        sorted_for_overlap_dedup = sorted(
            stage1_unique_items,
            key=lambda x: (-len(x.get("value", "")), 0 if x.get("source") == "llm" else 1)
        )

        stage2_unique_items: List[Dict[str, Any]] = []
        for item_to_consider in sorted_for_overlap_dedup:
            current_val = item_to_consider.get("value", "")
            current_type = item_to_consider.get("type")
            is_redundant_substring = False

            # Check if item_to_consider is a substring of an already added item of the same type
            for existing_item in stage2_unique_items:
                if existing_item.get("type") == current_type and \
                   current_val in existing_item.get("value", "") and \
                   current_val != existing_item.get("value", ""):
                    is_redundant_substring = True
                    break
            
            if is_redundant_substring:
                continue

            # Remove from stage2_unique_items those that are substrings of item_to_consider
            new_stage2_list = []
            for existing_item in stage2_unique_items:
                if existing_item.get("type") == current_type and \
                   existing_item.get("value", "") in current_val and \
                   existing_item.get("value", "") != current_val:
                    continue
                new_stage2_list.append(existing_item)
            stage2_unique_items = new_stage2_list
            
            stage2_unique_items.append(item_to_consider)

        # Step 5: Prepare final result (remove 'source' and sort)
        final_results = [
            {"type": r.get("type"), "value": r.get("value"), "label": r.get("label")}
            for r in stage2_unique_items
        ]
        
        final_results = sorted(final_results, key=lambda x: (x.get("type", ""), x.get("value", "")))
        
        return final_results
