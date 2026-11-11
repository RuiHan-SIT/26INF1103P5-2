class FileValidator:

    def __init__(self, max_size=10 * 1024 * 1024):
        self.max_size = max_size  # Default max size is 10 MB
        self.allowed_extensions = [".txt", ".docx"]

    def validate_file(self, uploaded_file):

        if uploaded_file is None:
            raise ValueError("No file uploaded.")

        filename = uploaded_file.name.lower()

        if not any(
            filename.endswith(ext)
            for ext in self.allowed_extensions
        ):
            raise ValueError(
                f"Invalid file type. Only TXT and DOCX are allowed."
            )

        if uploaded_file.size == 0:
            raise ValueError("The uploaded file is empty.")

        if uploaded_file.size > self.max_size:
            raise ValueError(
                f"File size exceeds the maximum limit of 10 MB."
            )
        return True