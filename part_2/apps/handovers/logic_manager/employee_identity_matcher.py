from difflib import SequenceMatcher

class EmployeeIdentityMatcher:
    FUZZY_THRESHOLD = 0.70

    def __init__(self, employees: list) -> None:
        self.__employees = employees

    # Ignore case and spaces during the first, exact matching level.
    def normalize_name(self, name: str) -> str:
        return name.strip().lower().replace(" ", "")

    # Compare name words while allowing different order or missing parts.
    def name_components_match(self, first_name: str, second_name: str) -> bool:
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

    def create_match(self, employee: dict, similarity: float | None = None) -> dict:
        match = {
            "employee_id": employee.get("employee_id"),
            "name": employee.get("name", ""),
            "department": employee.get("department", "")
        }

        if similarity is not None:
            match["similarity"] = round(similarity * 100, 1)

        return match

    def is_registered_employee(self, employee_id: str) -> bool:
        """Check that a selected employee ID belongs to the supplied directory."""
        for employee in self.__employees:
            if employee.get("employee_id") == employee_id:
                return True
        return False

    def match_owners(self, owner_names: list) -> list:
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

                # Very short fragments produce too many weak suggestions.
                if len(owner_normalized) >= 4:
                    for employee in self.__employees:
                        employee_name = employee.get("name", "")
                        employee_parts = employee_name.strip().lower().split()
                        possible_names = [self.normalize_name(employee_name)]

                        # Include consecutive name parts so "rui ha" can match
                        # the beginning of "Rui Han", and "hazi" can match "Haziq".
                        for start_index in range(len(employee_parts)):
                            combined_parts = ""
                            for next_index in range(start_index, len(employee_parts)):
                                combined_parts += self.normalize_name(employee_parts[next_index])
                                possible_names.append(combined_parts)

                        similarity = 0
                        for possible_name in possible_names:
                            current_similarity = SequenceMatcher(
                                None, owner_normalized, possible_name
                            ).ratio()
                            if current_similarity > similarity:
                                similarity = current_similarity

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
