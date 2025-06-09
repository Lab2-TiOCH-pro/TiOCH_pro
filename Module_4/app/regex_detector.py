import re
from typing import List, Dict, Any

class RegexDetector:
    def __init__(self):
        
        self.patterns = {
            "PESEL": {
                "regex": re.compile(r"\b(?<!\d)([0-9]{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9]|3[01])[0-9]{5})(?!\d)\b"),
                "type": "ID",
                "validator": self._validate_pesel,
                "priority": 10
            },
            "NIP": {
                "regex": re.compile(r"\b(?<!\d)(\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}|\d{10})(?!\d)\b"),
                "type": "ID",
                "validator": self._validate_nip,
                "priority": 9
            },
            "REGON": {
                "regex": re.compile(r"\b(?<!\d)(\d{9}|\d{14})(?!\d)\b"),
                "type": "ID",
                "validator": self._validate_regon,
                "priority": 8
            },
            "PASSPORT": {
                "regex": re.compile(r"\b(?<!\w)([A-Z]{2}\d{7})(?!\w)\b"),
                "type": "ID",
                "priority": 10
            },
            "ID_CARD": {
                "regex": re.compile(r"\b(?<!\w)([A-Z]{3}\s?\d{6})(?!\w)\b"),
                "type": "ID",
                "priority": 9
            },
            
            "DATE_BIRTH": {
                "regex": re.compile(r"\b((?:19[0-9]{2}|20[0-2][0-9])[-./](?:0[1-9]|1[0-2])[-./](?:0[1-9]|[12][0-9]|3[01])|(?:0[1-9]|[12][0-9]|3[01])[-./](?:0[1-9]|1[0-2])[-./](?:19[0-9]{2}|20[0-2][0-9]))\b"),
                "type": "dane_osobowe",
                "validator": self._validate_date,
                "priority": 7
            },
            
            "EMAIL": {
                "regex": re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b"),
                "type": "kontakt",
                "validator": self._validate_email,
                "priority": 10
            },
            
            "PHONE": {
                "regex": re.compile(r"\b(?<!\d)((?:\+?(?:48|49|33|39|44|43|42|34|31|32|36|30|351|352|353|354|356|357|358|359|370|371|372|373|374|375|376|377|378|380|381|382|383|385|386|387|389|420|421|423)\s?)?(?:\(?[1-9]\d{1,2}\)?[-\s]?)?(?:[1-9]\d{2}[-\s]?[0-9]{3}[-\s]?[0-9]{3}|[1-9]\d{1}[-\s]?[0-9]{2}[-\s]?[0-9]{2}[-\s]?[0-9]{2}))(?!\d)\b"),
                "type": "kontakt",
                "validator": self._validate_phone,
                "priority": 8
            },
            
            "ADDRESS": {
                "regex": re.compile(r"\b((?:ul\.|ulica|al\.|aleja|os\.|osiedle|pl\.|plac|rondo|bulwar|bul\.|skwer|skw\.|park)\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż\s,.-]+\s+\d+[A-Za-z]?(?:/\d+[A-Za-z]?)?)\b", re.IGNORECASE),
                "type": "kontakt",
                "priority": 6
            },
            
            "POSTAL_CODE": {
                "regex": re.compile(r"\b(?<!\d)(\d{2}[-\s]?\d{3})(?!\d)\b"),
                "type": "kontakt",
                "validator": self._validate_postal_code,
                "priority": 7
            },
            
            "STUDENT_ID": {
                "regex": re.compile(r"\b(?:nr\s+)?([A-Z]{2,4}\s?\d{4,8})(?!\d)\b", re.IGNORECASE),
                "type": "edukacyjne",
                "priority": 6
            },
            
            "DIPLOMA_NUMBER": {
                "regex": re.compile(r"\b(?:dyplom|certyfikat|świadectwo)\s+(?:nr\.?\s+)?([A-Z]*\d{4,8})\b", re.IGNORECASE),
                "type": "edukacyjne",
                "priority": 7
            },
            
            "ACCOUNT": {
                "regex": re.compile(r"\b([A-Z]{2}\d{2}[-\s]?(?:\d{4}[-\s]?){5}\d{4}|\d{26})\b"),
                "type": "finansowe",
                "validator": self._validate_iban,
                "priority": 9
            },
            
            "CREDIT_CARD": {
                "regex": re.compile(r"\b(?<!\d)((?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}))(?!\d)\b"),
                "type": "finansowe",
                "validator": self._validate_credit_card,
                "priority": 10
            },
            
            
            "BIRTH_PLACE": {
                "regex": re.compile(r"\b(?:miejsce\s+ur\.?\:?\s*|ur\.\s+w\s+|urodzona\s+w\s+|urodzony\s+w\s+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\s]+)(?:\s|$)", re.IGNORECASE),
                "type": "dane_osobowe",
                "priority": 8
            }
        }
        

    def detect(self, text: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        
        for name, pat in self.patterns.items():
            for match in pat["regex"].finditer(text):
                value = match.group(1) if match.groups() else match.group()
                
                if "validator" in pat and callable(pat["validator"]):
                    if not pat["validator"](value):
                        continue
                
                results.append({
                    "type": pat["type"],
                    "value": value,
                    "label": name,
                    "priority": pat.get("priority", 5),
                    "start": match.start(),
                    "end": match.end()
                })
        
        
        results.sort(key=lambda x: (-x.get("priority", 5), x.get("start", 0)))
        
        filtered_results = []
        for result in results:
            is_overlapping = False
            for existing in filtered_results:
                if self._ranges_overlap(
                    (result.get("start", 0), result.get("end", 0)),
                    (existing.get("start", 0), existing.get("end", 0))
                ):
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                clean_result = {k: v for k, v in result.items() if k not in ["priority", "start", "end"]}
                filtered_results.append(clean_result)
        
        unique_results = []
        seen = set()
        for r in filtered_results:
            key = (r.get("type"), r.get("value"), r.get("label"))
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        return unique_results

    def _ranges_overlap(self, range1, range2):
        """Sprawdza czy dwa zakresy się nakładają"""
        return range1[0] < range2[1] and range2[0] < range1[1]

    def _validate_name(self, name: str) -> bool:
        """Walidacja imion i nazwisk - wykluczenie nazw instytucji i miejsc"""
        name_lower = name.lower()
        
        
        # Sprawdź minimalną długość
        parts = name.split()
        if len(parts) < 2:
            return False
            
        # Sprawdź czy każda część ma odpowiednią długość
        for part in parts:
            if len(part) < 2 or len(part) > 25:
                return False
                
        return True

    def _validate_date(self, date_str: str) -> bool:
        """Walidacja daty"""
        try:
            # Usuń separator i sprawdź format
            date_clean = re.sub(r'[-./]', '', date_str)
            if len(date_clean) != 8:
                return False
                
            # Sprawdź czy to mogą być rzeczywiste daty urodzenia (1900-2020)
            if date_str.startswith(('19', '20')):
                year = int(date_str[:4])
                return 1900 <= year <= 2020
            else:
                # Format DD-MM-YYYY
                year = int(date_clean[4:8])
                return 1900 <= year <= 2020
        except (ValueError, IndexError):
            return False

    def _validate_phone(self, phone: str) -> bool:
        """Ulepszona walidacja numeru telefonu"""
        phone_clean = re.sub(r'[-\s()+]', '', phone)
        
        # Usuń kod kraju jeśli jest
        if phone_clean.startswith('48'):
            phone_clean = phone_clean[2:]
        elif phone_clean.startswith('+48'):
            phone_clean = phone_clean[3:]
            
        # Polski numer telefonu: 9 cyfr
        if len(phone_clean) == 9 and phone_clean.isdigit():
            # Sprawdź czy zaczyna się od właściwej cyfry
            return phone_clean[0] in '456789'
            
        return False

    # Reszta funkcji walidacyjnych pozostaje bez zmian
    def _validate_pesel(self, pesel: str) -> bool:
        """Walidacja numeru PESEL"""
        pesel = pesel.replace(" ", "").replace("-", "")
        if len(pesel) != 11:
            return False
        
        try:
            weights = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
            control_sum = sum(int(pesel[i]) * weights[i] for i in range(10))
            control_digit = (10 - (control_sum % 10)) % 10
            return control_digit == int(pesel[10])
        except (ValueError, IndexError):
            return False

    def _validate_nip(self, nip: str) -> bool:
        """Walidacja numeru NIP"""
        nip = nip.replace(" ", "").replace("-", "")
        if len(nip) != 10:
            return False
        
        try:
            weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
            control_sum = sum(int(nip[i]) * weights[i] for i in range(9))
            control_sum %= 11
            return control_sum == int(nip[9])
        except (ValueError, IndexError):
            return False

    def _validate_regon(self, regon: str) -> bool:
        """Walidacja numeru REGON (9 lub 14 cyfr)"""
        regon = regon.replace(" ", "").replace("-", "")
        if len(regon) not in [9, 14]:
            return False
        
        try:
            if len(regon) == 9:
                weights = [8, 9, 2, 3, 4, 5, 6, 7]
                control_sum = sum(int(regon[i]) * weights[i] for i in range(8))
                control_sum %= 11
                if control_sum == 10:
                    control_sum = 0
                return control_sum == int(regon[8])
            else:  # 14 cyfr
                weights = [2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8]
                control_sum = sum(int(regon[i]) * weights[i] for i in range(13))
                control_sum %= 11
                if control_sum == 10:
                    control_sum = 0
                return control_sum == int(regon[13])
        except (ValueError, IndexError):
            return False

    def _validate_iban(self, iban: str) -> bool:
        """Podstawowa walidacja numeru IBAN"""
        iban = iban.replace(" ", "").replace("-", "")
        if len(iban) < 15:
            return False
        
        if not (iban[:2].isalpha() and iban[2:4].isdigit()):
            return False
        
        if iban.startswith("PL") and len(iban) != 28:
            return False
            
        return True

    def _validate_credit_card(self, card: str) -> bool:
        """Walidacja numeru karty kredytowej algorytmem Luhna"""
        card = card.replace(" ", "").replace("-", "")
        if not card.isdigit() or len(card) < 13:
            return False
            
        # Algorytm Luhna
        digits = [int(d) for d in card]
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
            
        return checksum % 10 == 0

    def _validate_email(self, email: str) -> bool:
        """Rozszerzona walidacja adresu email"""
        if "@" not in email or "." not in email.split("@")[1]:
            return False
            
        local, domain = email.split("@", 1)
        if not local or not domain:
            return False
            
        if len(local) > 64 or len(domain) > 255:
            return False
            
        domain_parts = domain.split(".")
        if len(domain_parts[-1]) < 2:
            return False
            
        return True

    def _validate_postal_code(self, code: str) -> bool:
        """Walidacja kodu pocztowego"""
        code = code.replace(" ", "").replace("-", "")
        return len(code) == 5 and code.isdigit()