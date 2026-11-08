from difflib import SequenceMatcher


class EmployeeIdentityMatcher:
    FUZZY_THRESHOLD = 0.70

    def __init__(self, employees):
        self.__employees = employees

    def normalize_name(self, name):
        return name.strip().lower().replace(" ", "")

    def name_components_match(self, first_name, second_name):
        first_parts = first_name.strip().lower().split()
        second_parts = second_name.strip().lower().split()

        if len(first_parts) > len(second_parts):
            first_parts, second_parts = second_parts, first_parts

        for first_part in first_parts:
            found_part = False

            for start_index in range(len(second_parts)):
                combined_parts = ""

                for next_index in range(start_index, len(second_parts)):
                    combined_parts += second_parts[next_index]

                    if combined_parts == first_part:
                        found_part = True
                        break

                    if len(combined_parts) >= len(first_part):
                        break

                if found_part:
                    break

            if not found_part:
                return False

        return True

    def create_match(self, employee, similarity=None):
        match = {
            "employee_id": employee.get("employee_id"),
            "name": employee.get("name", ""),
            "department": employee.get("department", "")
        }

        if similarity is not None:
            match["similarity"] = round(similarity * 100, 1)

        return match

    def match_owners(self, owner_names):
        results = []

        for owner_name in owner_names:
            matches = []
            match_level = None

            # Level 1: exact after ignoring spaces and capitalization.
            for employee in self.__employees:
                employee_name = employee.get("name", "")

                if self.normalize_name(owner_name) == self.normalize_name(employee_name):
                    matches.append(self.create_match(employee))

            if matches:
                match_level = "exact"

            # Level 2: match complete name parts in any order.
            if not matches:
                for employee in self.__employees:
                    employee_name = employee.get("name", "")

                    if self.name_components_match(owner_name, employee_name):
                        matches.append(self.create_match(employee))

                if matches:
                    match_level = "components"

            # Level 3: suggest close spellings; the user still confirms.
            if not matches:
                owner_normalized = self.normalize_name(owner_name)

                for employee in self.__employees:
                    employee_name = employee.get("name", "")
                    employee_normalized = self.normalize_name(employee_name)
                    similarity = SequenceMatcher(
                        None, owner_normalized, employee_normalized
                    ).ratio()

                    if similarity >= self.FUZZY_THRESHOLD:
                        matches.append(self.create_match(employee, similarity))

                if matches:
                    match_level = "fuzzy"

            if matches:
                status = "confirmation_required"
            else:
                status = "unmatched"

            results.append({
                "owner_name": owner_name,
                "status": status,
                "match_level": match_level,
                "matches": matches
            })

        return results
