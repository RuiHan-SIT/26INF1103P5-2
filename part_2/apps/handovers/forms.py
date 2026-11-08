from django import forms

class HandoverUploadForm(forms.Form):
    document = forms.FileField(
        label="Word handover document",
        help_text="Upload a .docx file."
    )

    def clean_document(self):
        document = self.cleaned_data["document"]

        if not document.name.lower().endswith(".docx"):
            raise forms.ValidationError("Please upload a .docx Word document.")

        return document
