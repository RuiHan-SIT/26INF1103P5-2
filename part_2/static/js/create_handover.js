const fileInput = document.getElementById("document");
const uploadArea = document.querySelector(".chat-container");
const dropOverlay = document.getElementById("dropOverlay");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const removeFile = document.getElementById("removeFile")

const allowedExtensions = [".txt", ".docx"];
const maxSize = 10 * 1024 * 1024;

function displayFile(file) {
    if (!file) {
        clearFile();
        return;
    }

    const extension = file.name
        .slice(file.name.lastIndexOf("."))
        .toLowerCase();

    if (!allowedExtensions.includes(extension)) {
        alert("Only TXT and DOCX files are allowed.");
        clearFile();
        return;
    }

    if (file.size === 0) {
        alert("The selected file is empty.");
        clearFile();
        return;
    }

    if (file.size > maxSize) {
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

function clearFile() {
    fileInput.value = "";
    fileName.textContent = "";
    filePreview.hidden = true;
}

if (fileInput && filePreview && fileName && removeFile) {

    fileInput.addEventListener("change", function () {
        displayFile(fileInput.files[0]);
    });

    removeFile.addEventListener("click", function (event) {
        event.preventDefault();
        clearFile();
    });


    if (fileInput && uploadArea) {
        let dragDepth = 0;

        function hideDropOverlay() {
            dragDepth = 0;
            uploadArea.classList.remove("drag-over");

            if (dropOverlay) {
                dropOverlay.hidden = true;
            }
        }

        uploadArea.addEventListener("dragenter", function (event) {
            event.preventDefault();
            dragDepth++;

            uploadArea.classList.add("drag-over");

            if (dropOverlay) {
                dropOverlay.hidden = false;
            }
        });

        uploadArea.addEventListener("dragover", function (event) {
            event.preventDefault();
            event.dataTransfer.dropEffect = "copy";
        });

        uploadArea.addEventListener("dragleave", function (event) {
            event.preventDefault();
            dragDepth--;

            if (dragDepth <= 0) {
                hideDropOverlay();
            }
        });

        uploadArea.addEventListener("drop", function (event) {
            event.preventDefault();
            event.stopPropagation();
            hideDropOverlay();

            const files = event.dataTransfer.files;

            if (files.length !== 1) {
                alert("Please upload exactly one document.");
                return;
            }

            const file = files[0];

            const extension = file.name
                .slice(file.name.lastIndexOf("."))
                .toLowerCase();

            if (!allowedExtensions.includes(extension) ||
                file.size === 0 ||
                file.size > maxSize) {
                displayFile(file);
                return;
            }

            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);

            fileInput.files = dataTransfer.files;
            displayFile(file);
        });
    }

}

document.querySelectorAll("[data-employee-search]").forEach((search) => {
    const fieldName = search.dataset.employeeSearch;
    const directory = search.closest("[data-owner-directory]");
    const departmentFilter = directory.querySelector(`[data-department-filter="${fieldName}"]`);

    function filterDirectory() {
        const fieldName = search.dataset.employeeSearch;
        const searchText = search.value.trim().toLowerCase();
        const department = departmentFilter.value;
        const choices = directory.querySelectorAll("[data-employee-choice]");

        choices.forEach((choice) => {
            const matchesName = choice.dataset.search.includes(searchText);
            const matchesDepartment = !department || choice.dataset.search.includes(department);
            choice.hidden = !matchesName || !matchesDepartment;
        });
    }

    search.addEventListener("input", filterDirectory);
    departmentFilter.addEventListener("change", filterDirectory);
});

document.querySelectorAll(".owner-review").forEach((ownerReview) => {
    const suggestions = ownerReview.querySelector("[data-owner-suggestions]");
    const directory = ownerReview.querySelector("[data-owner-directory]");
    const confirmedPanel = ownerReview.querySelector("[data-owner-confirmed]");
    const confirmationField = ownerReview.querySelector("[data-owner-confirmation]");
    const confirmButton = ownerReview.querySelector("[data-confirm-owner]");
    const radios = ownerReview.querySelectorAll('input[type="radio"]');

    radios.forEach((radio) => {
        radio.addEventListener("change", () => {
            confirmButton.disabled = !ownerReview.querySelector('input[type="radio"]:checked');
        });
    });

    confirmButton.addEventListener("click", () => {
        const selected = ownerReview.querySelector('input[type="radio"]:checked');
        if (!selected) return;

        if (selected.hasAttribute("data-directory-option")) {
            selected.checked = false;
            confirmButton.disabled = true;
            suggestions.hidden = true;
            directory.hidden = false;
            directory.querySelector("[data-employee-search]").focus();
            return;
        }

        const selectedName = selected.closest("label").querySelector("strong").textContent;
        ownerReview.querySelector("[data-confirmed-name]").textContent = selectedName;
        confirmationField.value = "yes";
        suggestions.hidden = true;
        directory.hidden = true;
        confirmedPanel.hidden = false;
        confirmButton.hidden = true;
    });

    ownerReview.querySelector("[data-back-suggestions]").addEventListener("click", () => {
        directory.hidden = true;
        suggestions.hidden = false;
    });

    ownerReview.querySelector("[data-change-owner]").addEventListener("click", () => {
        confirmationField.value = "";
        confirmedPanel.hidden = true;
        confirmButton.hidden = false;
        confirmButton.disabled = !ownerReview.querySelector('input[type="radio"]:checked');
        suggestions.hidden = false;
    });
});


const profileButton = document.getElementById("profile-menu-button");
const profilePopover = document.getElementById("profile-menu");

profileButton.addEventListener("click", () => {
    const isOpen = profileButton.getAttribute("aria-expanded") === "true";
    profileButton.setAttribute("aria-expanded", String(!isOpen));
    profilePopover.hidden = isOpen;
});

document.addEventListener("click", (event) => {
    if (!profilePopover.contains(event.target) && !profileButton.contains(event.target)) {
        profilePopover.hidden = true;
        profileButton.setAttribute("aria-expanded", "false");
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        profilePopover.hidden = true;
        profileButton.setAttribute("aria-expanded", "false");
    }
});

window.addEventListener("dragover", function (event) {
    if (event.dataTransfer.types.includes("Files")) {
        event.preventDefault();
    }
});

window.addEventListener("drop", function (event) {
    if (event.dataTransfer.types.includes("Files")) {
        event.preventDefault();
    }
});
