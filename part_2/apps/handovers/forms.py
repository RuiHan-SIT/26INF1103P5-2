from django import forms

class HandoverUploadForm(forms.Form):
    document = forms.FileField(
        label="Word handover document",
        help_text="Upload a .txt or .docx file.(Max 10 MB)"
    )

    def clean_document(self):
        document = self.cleaned_data["document"]

        if not document.name.lower().endswith((".txt",".docx")):
            raise forms.ValidationError("Please upload a .txt or .docx Word document.")

        if document.size == 0:
            raise forms.ValidationError(
                "The uploaded file cannot be empty"
            )

        if document.size > 10 * 1024 *1024:
            raise forms.ValidationError(
                "File size must not exceed 10 MB"
            )
        return document
