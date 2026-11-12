const fileInput = document.getElementById("document");
const uploadArea = document.querySelector(".chat-container");
const dropOverlay = document.getElementById("dropOverlay");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const removeFile = document.getElementById("removeFile")
const chatForm = document.getElementById("chat-form");
const chatMessages = document.getElementById("chatMessages");
const chatMessageInput = document.getElementById("chat-message");
const sendButton = chatForm ? chatForm.querySelector(".send-btn") : null;

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
        statusBubble.firstChild.textContent = "The request could not reach the server. Please try again.";
        const cancelButton = statusBubble.querySelector(".ai-cancel-button");
        if (cancelButton) cancelButton.remove();
        reviewActions.forEach((button) => { button.disabled = false; });
        if (submitButton === sendButton) submitButton.textContent = "Send";
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
        const typedMessage = chatMessageInput ? chatMessageInput.value.trim() : "";
        if (filePreview) filePreview.hidden = true;
        const userBubble = document.createElement("div");
        userBubble.className = "chat-message user-message";
        userBubble.setAttribute("aria-label", "Your message");

        if (file) {
            const attachment = document.createElement("strong");
            attachment.className = "chat-attachment-name";
            attachment.textContent = file.name;
            const size = document.createElement("small");
            size.textContent = file.size < 1024
                ? `${file.size} bytes`
                : `${(file.size / 1024).toFixed(1)} KB`;
            userBubble.append(attachment, size);
        }

        if (typedMessage) {
            const message = document.createElement("span");
            message.textContent = typedMessage;
            userBubble.appendChild(message);
        }

        if (file || typedMessage) chatMessages.appendChild(userBubble);

        const loadingBubble = document.createElement("div");
        loadingBubble.className = "chat-message ai-loading";
        loadingBubble.setAttribute("role", "status");
        loadingBubble.id = "aiLoadingBubble";
        const loadingText = document.createElement("span");
        loadingText.textContent = "Reviewing your handover with AI. This can take a little while.";
        const loadingDots = document.createElement("span");
        loadingDots.className = "loading-dots";
        loadingDots.setAttribute("aria-hidden", "true");
        loadingDots.textContent = "•••";
        loadingBubble.append(loadingText, loadingDots);
        chatMessages.appendChild(loadingBubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        const chatContainer = chatForm.querySelector(".chat-container");
        if (chatContainer) chatContainer.setAttribute("aria-busy", "true");
        if (sendButton) {
            sendButton.textContent = "Reviewing…";
        }

        const formData = new FormData(chatForm);
        sendInBackground(chatForm, formData, loadingBubble, sendButton);
    });
}

document.querySelectorAll(".review-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
        if (!event.submitter || event.submitter.value !== "refine") return;
        event.preventDefault();
        const formData = new FormData(form);
        formData.set("action", "refine");
        const status = document.createElement("div");
        status.className = "review-ai-progress";
        status.setAttribute("role", "status");
        status.append("AI is reviewing your answers. This may take a little while. ");
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
