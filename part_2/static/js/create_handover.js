const fileInput = document.getElementById("document");
const uploadArea = document.getElementById("uploadArea");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const removeFile = document.getElementById("removeFile")

const allowedExtensions = [".txt", ".docx"];
const maxSize = 10 * 1024 * 1024;

function displayFile(file){
    if (!file){
        clearFile();
        return;
    }

    const extension = file.name
    .slice(file.name.lastIndexOf("."))
    .toLowerCase();

    if(!allowedExtensions.includes(extension)){
        alert("Only TXT and DOCX files are allowed.");
        clearFile();
        return;
    }

    if (file.size === 0){
        alert("The selected file is empty.");
        clearFile();
        return;
    }

    if (file.size > maxSize){
        alert("File exceeds the maximum size of 10MB.");
        clearFile();
        return;
    }

    const fileSize = file.size < 1024
        ? `${file.size} bytes`
        : `${(file.size / 1024).toFixed(1)} KB`;

    fileName.textContent = `${file.name} (${fileSize})`;
    filePreview.hidden = false;
}

function clearFile(){
    fileInput.value = "";
    fileName.textContent = "";
    filePreview.hidden = true;
}

fileInput.addEventListener("change", function(){
    console.log("File selected:", fileInput.files[0]);
    displayFile(fileInput.files[0]);
});

removeFile.addEventListener("click", function (event){
    event.preventDefault();
    clearFile();
});

uploadArea.addEventListener("dragover", function(event){
    event.preventDefault();
    uploadArea.classList.add("drag-over");
});
uploadArea.addEventListener("dragleave", function(event){
    event.preventDefault();
    uploadArea.classList.remove("drag-over");
});
uploadArea.addEventListener("drop", function(event){
    event.preventDefault();
    uploadArea.classList.remove("drag-over");
    
    const files = event.dataTransfer.files;

    if (files.length != 1){
        alert("Please upload exactly one document.");
        clearFile();
        return;
    }

    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(files[0]);
    fileInput.files = dataTransfer.files;

    displayFile(fileInput.files[0]);

})
    
