from django.core.files.uploadedfile import UploadedFile


class FileValidator:
    def __init__(self, max_size: int = 10 * 1024 * 1024) -> None:
        self.max_size: int = max_size  # Default maximum size is 10 MB
        self.allowed_extensions: list[str] = [".docx"]

    def validate_file(self, uploaded_file: UploadedFile | None) -> bool:
        if uploaded_file is None:
            raise ValueError("No file uploaded.")

        filename: str = uploaded_file.name.lower()

        if not any(
            filename.endswith(ext)
            for ext in self.allowed_extensions
        ):
            raise ValueError(
                "Invalid file type. Only Word (.docx) files are allowed."
            )

        if uploaded_file.size == 0:
            raise ValueError("The uploaded file is empty.")

        if uploaded_file.size > self.max_size:
            raise ValueError("File size exceeds the maximum limit of 10 MB.")

        return True