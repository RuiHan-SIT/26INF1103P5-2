// Keep page variables local when a background response replaces the document.
(function () {
const fileInput = document.getElementById("document");
const uploadArea = document.querySelector(".chat-container");
const dropOverlay = document.getElementById("dropOverlay");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const fileSizeLabel = document.getElementById("fileSize");
const changeFile = document.getElementById("changeFile");
const removeFile = document.getElementById("removeFile")
const chatForm = document.getElementById("chat-form");
const chatMessages = document.getElementById("chatMessages");
const sendButton = chatForm ? chatForm.querySelector(".send-btn") : null;

const allowedExtensions = [".docx"];
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
        alert("Only Word (.docx) files are allowed.");
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

    fileName.textContent = file.name;
    fileSizeLabel.textContent = fileSize;
    filePreview.hidden = false;
    uploadArea.classList.add("has-file");
    fileInput.tabIndex = -1;
    document.getElementById("chatDropHint").hidden = true;
    document.querySelector(".upload-file-slot").hidden = false;
    if (sendButton) sendButton.disabled = false;
}

function clearFile() {
    fileInput.value = "";
    fileName.textContent = "";
    fileSizeLabel.textContent = "";
    filePreview.hidden = true;
    uploadArea.classList.remove("has-file");
    fileInput.tabIndex = 0;
    document.getElementById("chatDropHint").hidden = false;
    document.querySelector(".upload-file-slot").hidden = true;
    if (sendButton) sendButton.disabled = true;
}

if (fileInput && filePreview && fileName && removeFile) {

    changeFile.addEventListener("click", () => fileInput.click());

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
            if (activeAiRequest || fileInput.files.length) return;
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
            if (activeAiRequest || fileInput.files.length) return;

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

let activeAiRequest = null;

function cancellationFormData(form) {
    const data = new FormData();
    data.append("csrfmiddlewaretoken", form.querySelector("[name=csrfmiddlewaretoken]").value);
    data.append("request_token", form.querySelector("[name=request_token]").value);
    return data;
}

function attachCancelButton(statusBubble, form, controller) {
    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "ai-cancel-button";
    cancelButton.textContent = "Cancel handover";
    cancelButton.addEventListener("click", async () => {
        if (!window.confirm("Cancel this handover? It will not be saved. The AI request already sent may still finish.")) {
            return;
        }
        cancelButton.disabled = true;
        cancelButton.textContent = "Cancelling…";
        try {
            const response = await fetch(form.dataset.cancelUrl, {
                method: "POST",
                body: cancellationFormData(form),
                credentials: "same-origin",
            });
            const result = await response.json();
            if (!result.cancelled) throw new Error("The handover could not be cancelled.");
            controller.abort();
            activeAiRequest = null;
            window.location.assign(form.dataset.homeUrl || result.redirect_url);
        } catch (error) {
            // A beacon is a best-effort fallback if the cancellation response is lost.
            navigator.sendBeacon(form.dataset.cancelUrl, cancellationFormData(form));
            controller.abort();
            activeAiRequest = null;
            window.location.assign(form.dataset.homeUrl || "/");
        }
    });
    statusBubble.appendChild(cancelButton);
}

async function sendInBackground(form, formData, statusBubble, submitButton) {
    const controller = new AbortController();
    activeAiRequest = {form, controller};
    const reviewActions = form.classList.contains("review-form") || form.classList.contains("detail-edit-form")
        ? Array.from(form.querySelectorAll("button[type=submit]"))
        : [submitButton].filter(Boolean);
    reviewActions.forEach((button) => { button.disabled = true; });
    attachCancelButton(statusBubble, form, controller);

    try {
        const response = await fetch(form.getAttribute("action") || window.location.href, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
            signal: controller.signal,
        });

        if (activeAiRequest !== null) activeAiRequest = null;
        if (response.redirected) {
            window.location.assign(response.url);
            return;
        }

        // Display validation or AI errors only after the background request ends.
        const page = await response.text();
        document.open();
        document.write(page);
        document.close();
    } catch (error) {
        if (error.name === "AbortError") return;
        const cancelButton = form.querySelector(".ai-cancel-button");
        if (cancelButton) cancelButton.remove();
        reviewActions.forEach((button) => { button.disabled = false; });
        if (submitButton === sendButton) {
            const errorMessage = document.createElement("div");
            errorMessage.className = "chat-message ai-message upload-error-message";
            errorMessage.setAttribute("role", "alert");
            errorMessage.textContent = "The request could not reach the server. Please try again.";
            chatMessages.appendChild(errorMessage);
            chatMessages.hidden = false;
            submitButton.textContent = "✦ Extract Tasks with AI";
            submitButton.removeAttribute("aria-busy");
            fileInput.disabled = false;
            changeFile.disabled = false;
            removeFile.disabled = false;
            uploadArea.setAttribute("aria-busy", "false");
        } else {
            statusBubble.firstChild.textContent = "The request could not reach the server. Please try again.";
        }
    } finally {
        if (activeAiRequest && activeAiRequest.controller === controller) activeAiRequest = null;
    }
}

// Refreshing or leaving the page sends a best-effort cancellation notice.
window.addEventListener("pagehide", () => {
    if (!activeAiRequest) return;
    navigator.sendBeacon(
        activeAiRequest.form.dataset.cancelUrl,
        cancellationFormData(activeAiRequest.form)
    );
});

// Keep the page visible and show progress in the conversation while AI works.
if (chatForm && chatMessages) {
    chatForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const file = fileInput && fileInput.files[0];
        if (activeAiRequest || !file) return;
        chatMessages.replaceChildren();
        chatMessages.hidden = true;

        const chatContainer = chatForm.querySelector(".chat-container");
        if (chatContainer) chatContainer.setAttribute("aria-busy", "true");
        if (sendButton) {
            sendButton.disabled = true;
            sendButton.setAttribute("aria-busy", "true");
            sendButton.innerHTML = 'Extracting <span class="extract-loading-dots" aria-hidden="true"><span>•</span><span>•</span><span>•</span></span>';
        }

        const formData = new FormData(chatForm);
        fileInput.disabled = true;
        changeFile.disabled = true;
        removeFile.disabled = true;
        sendInBackground(chatForm, formData, chatForm.querySelector(".upload-actions"), sendButton);
    });
}

document.querySelectorAll(".review-form").forEach((form) => {
    form.addEventListener("input", (event) => {
        const panel = event.target.closest("[data-task-questions]");
        if (panel && [...panel.querySelectorAll("textarea")].some((input) => input.value.trim())) {
            panel.querySelector(".question-error")?.remove();
        }
    });
    form.addEventListener("submit", (event) => {
        if (!event.submitter || event.submitter.value !== "refine") return;
        event.preventDefault();
        let missingAnswers = false;
        form.querySelectorAll("[data-task-questions]").forEach((panel) => {
            panel.querySelector(".question-error")?.remove();
            if (![...panel.querySelectorAll("textarea")].some((input) => input.value.trim())) {
                const error = document.createElement("p");
                error.className = "question-error";
                error.setAttribute("role", "alert");
                error.textContent = "Answer at least one question for this task.";
                panel.append(error);
                missingAnswers = true;
            }
        });
        if (missingAnswers) {
            form.querySelector(".question-error")?.scrollIntoView({block: "center", behavior: "smooth"});
            return;
        }
        const formData = new FormData(form);
        formData.set("action", "refine");
        const status = document.createElement("div");
        status.className = "review-ai-progress";
        status.setAttribute("role", "status");
        status.append("AI is reviewing your answers. This may take a little while. ");
        const dots = document.createElement("span");
        dots.className = "extract-loading-dots";
        dots.setAttribute("aria-hidden", "true");
        for (let index = 0; index < 3; index += 1) {
            const dot = document.createElement("span");
            dot.textContent = "•";
            dots.append(dot);
        }
        status.append(dots);
        form.querySelector(".review-actions").prepend(status);
        sendInBackground(form, formData, status, event.submitter);
    });
});

document.querySelectorAll(".detail-edit-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
        if (!event.submitter || event.submitter.value !== "ai_refine") return;
        event.preventDefault();
        const formData = new FormData(form);
        formData.set("action", "ai_refine");
        const status = form.querySelector(".detail-ai-status");
        status.hidden = false;
        status.className = "detail-ai-status review-ai-progress";
        status.textContent = "AI is reviewing your edited handover. Its suggestions will not be applied until you confirm.";
        sendInBackground(form, formData, status, event.submitter);
    });
});

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

if (profileButton && profilePopover) {
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
}

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

})();
