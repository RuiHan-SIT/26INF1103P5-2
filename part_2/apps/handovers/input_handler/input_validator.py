import logging
import re
import scrubadub

logger = logging.getLogger(__name__)

class InputValidator:

    def __init__(self):
        self.scrubber = scrubadub.Scrubber()
        self.scrubber.remove_detector('phone')

    def has_alphanumeric_char(self, text: str) -> bool:
        return bool(text.strip()) and any(
            char.isalpha() for char in text
        )

    def validate_name(self, name:str) -> bool:
        return self.has_alphanumeric_char(name)

    def validate_department(self, department: str) -> bool:
        return self.has_alphanumeric_char(department)

    def validate_employee_id(self, employee_id: str) -> bool:
        return len(employee_id) == 7 and employee_id.isdigit()

    def validate_user_input(self, text: str):

        detected_types = {
            filth.type for filth in self.scrubber.iter_filth(text)
        }

        sensitive_keywords = [
            "password",
            "passport"
        ]

        sensitive_patterns = {
            "NRIC/FIN": r"\b[STFGM]\d{7}[A-Z]\b",
            "Passport": r"\b[E]\d{7}[A-Z]\b"
        }

        text_lower = text.lower()

        for keyword in sensitive_keywords:
            if keyword in text_lower:
                detected_types.add("Sensitive Keyword")

        for label, pattern in sensitive_patterns.items():
            if re.search(pattern, text):
                detected_types.add(label)

        if detected_types:
            logger.warning(
                "Sensitive information detected in your input. Please remove the following types of sensitive information before proceeding: "
                f"{', '.join(sorted(detected_types))}."
            )
            return True
        return False