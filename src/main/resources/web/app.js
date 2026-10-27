(function () {
  "use strict";

  const operationLabels = {
    split: "Dividi PDF",
    merge: "Unisci PDF",
    rename: "Rinomina PDF",
    encrypt: "Proteggi PDF",
    extract: "Estrai testo",
    "images-to-pdf": "Converti in PDF",
    "documents-to-pdf": "Converti DOCX / ODT in PDF"
  };
  const MAX_FILES = 32;
  const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png"];
  const DOCUMENT_EXTENSIONS = [".docx", ".odt"];
  const PDF_ACCEPT = ".pdf,application/pdf";
  const IMAGE_ACCEPT = ".jpg,.jpeg,.png,image/jpeg,image/png";
  const DOCUMENT_ACCEPT = ".docx,.odt,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.oasis.opendocument.text";

  const state = {
    files: [],
    downloadUrl: null,
    busy: false,
    pendingFocus: null
  };

  const elements = {
    picker: document.getElementById("file-picker"),
    pickerTitle: document.getElementById("picker-title"),
    pickerHelp: document.getElementById("picker-help"),
    selectedFiles: document.getElementById("selected-files"),
    selectionCount: document.getElementById("selection-count"),
    selectionEmpty: document.getElementById("selection-empty"),
    selectionRequirement: document.getElementById("selection-requirement"),
    selectionHint: document.getElementById("selection-hint"),
    clearSelection: document.getElementById("clear-selection"),
    operationRadios: Array.from(document.querySelectorAll('input[name="operation"]')),
    panels: Array.from(document.querySelectorAll("[data-panel]")),
    splitModeRadios: Array.from(document.querySelectorAll('input[name="split-mode"]')),
    pagesField: document.getElementById("pages-field"),
    pagesPerPart: document.getElementById("pages-per-part"),
    renameModeRadios: Array.from(document.querySelectorAll('input[name="rename-mode"]')),
    renamePanels: Array.from(document.querySelectorAll("[data-rename-panel]")),
    startingNumber: document.getElementById("starting-number"),
    codeLength: document.getElementById("code-length"),
    password: document.getElementById("password"),
    runButton: document.getElementById("run-operation"),
    submitHelp: document.getElementById("submit-help"),
    resultSection: document.getElementById("result-section"),
    resultIcon: document.getElementById("result-icon"),
    resultStatus: document.getElementById("result-status"),
    resultError: document.getElementById("result-error"),
    downloadLink: document.getElementById("download-link"),
    progress: document.getElementById("progress-indicator")
  };

  elements.picker.addEventListener("change", addSelectedFiles);
  elements.clearSelection.addEventListener("click", clearSelectedFiles);
  elements.operationRadios.forEach((radio) => radio.addEventListener("change", onOperationChange));
  elements.splitModeRadios.forEach((radio) => radio.addEventListener("change", updateControls));
  elements.renameModeRadios.forEach((radio) => radio.addEventListener("change", updateControls));
  document.querySelectorAll(".settings-panel input").forEach((input) => {
    input.addEventListener("input", onSettingsChange);
    input.addEventListener("change", onSettingsChange);
  });
  elements.runButton.addEventListener("click", submitOperation);

  function currentOperation() {
    const selected = elements.operationRadios.find((radio) => radio.checked);
    return selected ? selected.value : "split";
  }

  function addSelectedFiles() {
    const keys = new Set(state.files.map(fileKey));
    let excessFiles = 0;
    let unsupportedFiles = 0;
    const imageOperation = currentOperation() === "images-to-pdf";
    const documentOperation = currentOperation() === "documents-to-pdf";
    Array.from(elements.picker.files || []).forEach((file) => {
      if (!keys.has(fileKey(file))) {
        if (!isSupportedFile(file, imageOperation, documentOperation)) {
          unsupportedFiles += 1;
        } else if (state.files.length >= MAX_FILES) {
          excessFiles += 1;
        } else {
          state.files.push(file);
          keys.add(fileKey(file));
        }
      }
    });
    elements.picker.value = "";
    clearResult();
    renderFiles();
    updateControls();
    if (excessFiles > 0 || unsupportedFiles > 0) {
      showResult();
      setResultState("error");
      const messages = [];
      if (unsupportedFiles > 0) {
        messages.push(imageOperation
          ? "Sono supportate solo immagini JPG e PNG."
          : documentOperation
            ? "Sono supportati solo documenti DOCX e ODT."
            : "Per questa operazione seleziona solo file PDF.");
      }
      if (excessFiles > 0) messages.push("Puoi selezionare al massimo 32 file per operazione.");
      elements.resultError.textContent = messages.join(" ");
    }
  }

  function isSupportedFile(file, imageOperation, documentOperation) {
    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (imageOperation) return IMAGE_EXTENSIONS.includes(extension);
    if (documentOperation) return DOCUMENT_EXTENSIONS.includes(extension);
    return extension === ".pdf";
  }

  function clearSelectedFiles() {
    state.files = [];
    elements.picker.value = "";
    clearResult();
    renderFiles();
    updateControls();
    elements.picker.focus();
  }

  function fileKey(file) {
    return [file.name, file.size, file.lastModified, file.type].join("\u0000");
  }

  function renderFiles(focusTarget) {
    elements.selectedFiles.replaceChildren();
    elements.selectionEmpty.hidden = state.files.length > 0;
    elements.selectionHint.hidden = state.files.length < 2;
    const imageOperation = currentOperation() === "images-to-pdf";
    const documentOperation = currentOperation() === "documents-to-pdf";
    elements.selectionCount.textContent = state.files.length === 0
      ? imageOperation ? "Nessuna immagine selezionata" : documentOperation ? "Nessun documento selezionato" : "Nessun PDF selezionato"
      : state.files.length + (imageOperation
        ? state.files.length === 1 ? " immagine selezionata" : " immagini selezionate"
        : documentOperation
          ? state.files.length === 1 ? " documento selezionato" : " documenti selezionati"
          : state.files.length === 1 ? " PDF selezionato" : " PDF selezionati");
    elements.selectedFiles.setAttribute(
      "aria-label",
      imageOperation ? "Immagini selezionate, nell'ordine del PDF" : documentOperation
        ? "Documenti selezionati" : "PDF selezionati, nell'ordine di elaborazione"
    );
    elements.clearSelection.disabled = state.files.length === 0 || state.busy;

    state.files.forEach((file, index) => {
      const item = document.createElement("li");
      item.className = "file-item";

      const details = document.createElement("div");
      details.className = "file-details";
      const name = document.createElement("span");
      name.className = "file-name";
      name.textContent = file.name;
      const size = document.createElement("span");
      size.className = "file-size";
      size.textContent = formatSize(file.size);
      details.append(name, size);

      const actions = document.createElement("div");
      actions.className = "file-actions";
      actions.append(
        makeFileAction("↑", "Sposta " + file.name + " in alto", index, -1, index === 0),
        makeFileAction("↓", "Sposta " + file.name + " in basso", index, 1, index === state.files.length - 1),
        makeRemoveAction(file, index)
      );

      item.append(details, actions);
      elements.selectedFiles.append(item);
    });

    if (focusTarget) {
      const button = elements.selectedFiles.querySelector('[data-focus-key="' + focusTarget + '"]');
      if (button) button.focus();
    }
  }

  function makeFileAction(label, accessibleName, index, direction, disabled) {
    const button = document.createElement("button");
    button.className = "icon-button";
    button.type = "button";
    button.textContent = label;
    button.setAttribute("aria-label", accessibleName);
    button.disabled = disabled || state.busy;
    button.addEventListener("click", function () {
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= state.files.length) return;
      [state.files[index], state.files[nextIndex]] = [state.files[nextIndex], state.files[index]];
      clearResult();
      renderFiles("move-" + nextIndex);
      updateControls();
    });
    button.dataset.focusKey = "move-" + index;
    return button;
  }

  function makeRemoveAction(file, index) {
    const button = document.createElement("button");
    button.className = "remove-button";
    button.type = "button";
    button.textContent = "Rimuovi";
    button.setAttribute("aria-label", "Rimuovi " + file.name);
    button.disabled = state.busy;
    button.addEventListener("click", function () {
      state.files.splice(index, 1);
      clearResult();
      const focusIndex = Math.min(index, state.files.length - 1);
      renderFiles(focusIndex >= 0 ? "remove-" + focusIndex : null);
      updateControls();
      if (focusIndex < 0) elements.picker.focus();
    });
    button.dataset.focusKey = "remove-" + index;
    return button;
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toLocaleString("it-IT", { maximumFractionDigits: 1 }) + " KB";
    return (bytes / (1024 * 1024)).toLocaleString("it-IT", { maximumFractionDigits: 1 }) + " MB";
  }

  function onOperationChange() {
    const imageOperation = currentOperation() === "images-to-pdf";
    if (state.files.some((file) => !isSupportedFile(file, imageOperation))) {
      state.files = [];
      elements.picker.value = "";
      renderFiles();
    }
    clearResult();
    updateControls();
  }

  function onSettingsChange(event) {
    const input = event.target;
    if (input.id) clearFieldError(input.id);
    updateControls();
  }

  function updateControls() {
    const operation = currentOperation();
    elements.panels.forEach((panel) => {
      panel.hidden = panel.dataset.panel !== operation;
    });
    elements.picker.disabled = state.busy;
    const imageOperation = operation === "images-to-pdf";
    const documentOperation = operation === "documents-to-pdf";
    elements.picker.accept = imageOperation ? IMAGE_ACCEPT : documentOperation ? DOCUMENT_ACCEPT : PDF_ACCEPT;
    elements.pickerTitle.textContent = imageOperation ? "Scegli immagini" : documentOperation ? "Scegli DOCX o ODT" : "Scegli PDF";
    elements.pickerHelp.textContent = imageOperation
      ? "JPG o PNG · massimo 32 immagini e 100 MiB complessivi"
      : documentOperation ? "Un file DOCX o ODT · massimo 100 MiB"
        : "Massimo 32 PDF e 100 MiB complessivi per operazione";
    elements.operationRadios.forEach((radio) => { radio.disabled = state.busy; });
    document.querySelectorAll(".settings-panel input").forEach((input) => { input.disabled = state.busy; });

    const splitMode = document.querySelector('input[name="split-mode"]:checked').value;
    elements.pagesField.hidden = splitMode !== "groups";
    const renameMode = document.querySelector('input[name="rename-mode"]:checked').value;
    elements.renamePanels.forEach((panel) => {
      panel.hidden = panel.dataset.renamePanel !== renameMode;
    });

    const requirement = getRequirement(operation);
    elements.runButton.textContent = operationLabels[operation];
    elements.runButton.disabled = state.busy || !requirement.valid;
    elements.submitHelp.textContent = requirement.message;
    elements.clearSelection.disabled = state.files.length === 0 || state.busy;
    elements.selectionRequirement.textContent = selectionRequirement(operation);
    elements.selectionHint.textContent = imageOperation
      ? "L'ordine mostrato qui verrà mantenuto nelle pagine del PDF."
      : documentOperation
        ? "Per questa operazione puoi selezionare un solo documento."
        : "Per unire i PDF, usa i pulsanti su e giù per impostare l'ordine: il primo file determina il nome del risultato.";
    syncFieldErrors(operation);
  }

  function selectionRequirement(operation) {
    if (operation === "split" || operation === "extract") {
      return operation === "split"
        ? "Per dividere il documento, seleziona esattamente un PDF."
        : "Per estrarre il testo, seleziona esattamente un PDF.";
    }
    if (operation === "images-to-pdf") {
      return "Seleziona da una a 32 immagini JPG o PNG da convertire.";
    }
    if (operation === "documents-to-pdf") {
      return "Per convertire il documento, seleziona un solo file DOCX o ODT.";
    }
    if (operation === "merge") return "Per unire i PDF, seleziona almeno due documenti e controlla il loro ordine.";
    if (operation === "rename") return "Per rinominare, seleziona uno o più PDF.";
    return "Per proteggere, seleziona uno o più PDF e inserisci una password.";
  }

  function syncFieldErrors(operation) {
    const splitGroups = operation === "split" &&
      document.querySelector('input[name="split-mode"]:checked').value === "groups";
    setFieldValidity("pages-per-part", splitGroups
      ? validInteger(elements.pagesPerPart.value, 1, Number.MAX_SAFE_INTEGER)
      : true, "Inserisci un numero intero maggiore di zero.");

    const renameMode = document.querySelector('input[name="rename-mode"]:checked').value;
    setFieldValidity("starting-number", operation !== "rename" || renameMode !== "sequential" ||
      validInteger(elements.startingNumber.value, 0, 9), "Inserisci un numero intero da 0 a 9.");
    setFieldValidity("code-length", operation !== "rename" || renameMode !== "random" ||
      validInteger(elements.codeLength.value, 4, 20), "Inserisci un numero intero da 4 a 20.");
    setFieldValidity("password", operation !== "encrypt" || Boolean(elements.password.value),
      "Inserisci una password per continuare.");
  }

  function setFieldValidity(id, valid, message) {
    const input = document.getElementById(id);
    const error = document.getElementById(id + "-error");
    if (!input || !error) return;
    if (valid) {
      input.removeAttribute("aria-invalid");
      error.textContent = "";
    } else {
      input.setAttribute("aria-invalid", "true");
      error.textContent = message;
    }
  }

  function getRequirement(operation) {
    const imageOperation = operation === "images-to-pdf";
    const documentOperation = operation === "documents-to-pdf";
    if (state.files.some((file) => !isSupportedFile(file, imageOperation, documentOperation))) {
      return {
        valid: false,
        message: imageOperation
          ? "Seleziona solo immagini JPG o PNG."
          : documentOperation
            ? "Seleziona solo file DOCX o ODT."
            : "Seleziona solo file PDF."
      };
    }

    if (operation === "split") {
      if (state.files.length !== 1) return { valid: false, message: "Seleziona un solo PDF per dividere il documento." };
      if (document.querySelector('input[name="split-mode"]:checked').value === "groups" &&
          !validInteger(elements.pagesPerPart.value, 1, Number.MAX_SAFE_INTEGER)) {
        return { valid: false, message: "Indica quante pagine includere in ogni gruppo." };
      }
    } else if (operation === "merge" && state.files.length < 2) {
      return { valid: false, message: "Seleziona almeno due PDF; l'ordine dell'elenco sarà mantenuto." };
    } else if (operation === "rename") {
      if (state.files.length < 1) return { valid: false, message: "Seleziona uno o più PDF da rinominare." };
      if (document.querySelector('input[name="rename-mode"]:checked').value === "sequential" &&
          !validInteger(elements.startingNumber.value, 0, 9)) {
        return { valid: false, message: "Il numero iniziale deve essere un intero da 0 a 9." };
      }
      if (document.querySelector('input[name="rename-mode"]:checked').value === "random" &&
          !validInteger(elements.codeLength.value, 4, 20)) {
        return { valid: false, message: "La lunghezza del codice deve essere un intero da 4 a 20." };
      }
    } else if (operation === "encrypt") {
      if (state.files.length < 1) return { valid: false, message: "Seleziona uno o più PDF da proteggere." };
      if (!elements.password.value) return { valid: false, message: "Inserisci una password per proteggere i PDF." };
    } else if (operation === "extract" && state.files.length !== 1) {
      return { valid: false, message: "Seleziona un solo PDF da cui estrarre il testo." };
    } else if (operation === "images-to-pdf" && state.files.length < 1) {
      return { valid: false, message: "Seleziona almeno un'immagine JPG o PNG da convertire." };
    } else if (operation === "documents-to-pdf" && state.files.length !== 1) {
      return { valid: false, message: "Seleziona un solo documento DOCX o ODT da convertire." };
    }
    return { valid: true, message: operation === "merge"
      ? "I PDF saranno uniti nell'ordine mostrato nell'elenco."
      : "I file originali non verranno modificati." };
  }

  function validInteger(value, minimum, maximum) {
    if (value.trim() === "") return false;
    const number = Number(value);
    return Number.isInteger(number) && number >= minimum && number <= maximum;
  }

  function clearFieldError(id) {
    const input = document.getElementById(id);
    const error = document.getElementById(id + "-error");
    if (input) input.removeAttribute("aria-invalid");
    if (error) error.textContent = "";
  }

  function focusWhenReady(element) {
    if (state.busy) state.pendingFocus = element;
    else element.focus();
  }

  function showFieldError(id, message) {
    const input = document.getElementById(id);
    const error = document.getElementById(id + "-error");
    if (input) {
      input.setAttribute("aria-invalid", "true");
      focusWhenReady(input);
    }

    if (error) error.textContent = message;
    showResult();
    setResultState("error");
    elements.resultStatus.textContent = "";
    elements.resultError.textContent = message;
  }

  function validateBeforeSubmit(operation) {
    if (operation === "split" &&
        document.querySelector('input[name="split-mode"]:checked').value === "groups" &&
        !validInteger(elements.pagesPerPart.value, 1, Number.MAX_SAFE_INTEGER)) {
      showFieldError("pages-per-part", "Inserisci un numero intero maggiore di zero.");
      return false;
    }
    if (operation === "rename") {
      const mode = document.querySelector('input[name="rename-mode"]:checked').value;
      if (mode === "sequential" && !validInteger(elements.startingNumber.value, 0, 9)) {
        showFieldError("starting-number", "Inserisci un numero intero da 0 a 9.");
        return false;
      }
      if (mode === "random" && !validInteger(elements.codeLength.value, 4, 20)) {
        showFieldError("code-length", "Inserisci un numero intero da 4 a 20.");
        return false;
      }
    }
    if (operation === "encrypt" && !elements.password.value) {
      showFieldError("password", "Inserisci una password per continuare.");
      return false;
    }
    return true;
  }

  async function submitOperation() {
    if (state.busy) return;
    const operation = currentOperation();
    const requirement = getRequirement(operation);
    if (!requirement.valid) return;
    if (!validateBeforeSubmit(operation)) return;

    const formData = buildRequest(operation);
    clearResult();
    showResult();
    setResultState("working");
    elements.resultStatus.textContent = "Preparazione dei file per " + operationLabels[operation].toLocaleLowerCase("it-IT") + ".";
    elements.resultError.textContent = "";
    elements.progress.hidden = false;
    state.busy = true;
    updateControls();
    renderFiles();

    try {
      const response = await fetch("api/" + (operation === "extract" ? "extract-text" : operation), {
        method: "POST",
        body: formData
      });
      if (!response.ok) {
        await handleFailure(response, operation);
        return;
      }

      const blob = await response.blob();
      const filename = responseFilename(response.headers.get("Content-Disposition")) || defaultFilename(operation);
      state.downloadUrl = URL.createObjectURL(blob);
      elements.downloadLink.href = state.downloadUrl;
      elements.downloadLink.download = filename;
      elements.downloadLink.textContent = "Scarica " + filename;
      elements.downloadLink.hidden = false;
      setResultState("success");
      elements.resultStatus.textContent = "Operazione completata. Il download è stato avviato.";
      elements.resultError.textContent = "";
      elements.downloadLink.click();
      if (operation === "encrypt") elements.password.value = "";
    } catch (error) {
      setResultState("error");
      elements.resultStatus.textContent = "";
      elements.resultError.textContent = "Impossibile raggiungere l'applicazione. Verifica la connessione al server e riprova.";
    } finally {
      state.busy = false;
      elements.progress.hidden = true;
      updateControls();
      renderFiles();
      if (state.pendingFocus && !state.pendingFocus.disabled) state.pendingFocus.focus();
      state.pendingFocus = null;
    }
  }

  function buildRequest(operation) {
    const formData = new FormData();
    const fileField = operation === "split" || operation === "extract" || operation === "documents-to-pdf"
      ? "file"
      : operation === "images-to-pdf" ? "images" : "files";
    state.files.forEach((file) => formData.append(fileField, file, file.name));

    if (operation === "split") {
      if (document.querySelector('input[name="split-mode"]:checked').value === "groups") {
        formData.append("pagesPerPart", elements.pagesPerPart.value);
      } else {
        formData.append("pagesPerPart", "1");
      }
    } else if (operation === "rename") {
      const mode = document.querySelector('input[name="rename-mode"]:checked').value;
      formData.append("mode", mode);
      if (mode === "sequential") {
        formData.append("prefix", document.getElementById("rename-prefix").value);
        formData.append("startingNumber", elements.startingNumber.value);
      } else {
        formData.append("codeLength", elements.codeLength.value);
        formData.append("useSymbols", String(document.getElementById("use-symbols").checked));
      }
    } else if (operation === "encrypt") {
      formData.append("password", elements.password.value);
      document.querySelectorAll('input[name="permission"]').forEach((checkbox) => {
        formData.append(checkbox.value, String(checkbox.checked));
      });
    }
    return formData;
  }

  async function handleFailure(response, operation) {
    let message = "";
    try {
      const body = await response.json();
      message = typeof body.error === "string" ? body.error
        : typeof body.message === "string" ? body.message : "";
    } catch (error) {
      message = "";
    }

    setResultState("error");
    elements.resultStatus.textContent = "";
    if (response.status === 400) {
      const lowerMessage = message.toLowerCase();
      if (lowerMessage.includes("pages per part")) {
        showFieldError("pages-per-part", "Inserisci un numero intero maggiore di zero.");
        return;
      }
      if (lowerMessage.includes("starting number")) {
        showFieldError("starting-number", "Inserisci un numero intero da 0 a 9.");
        return;
      }
      if (lowerMessage.includes("code length")) {
        showFieldError("code-length", "Inserisci un numero intero da 4 a 20.");
        return;
      }
      if (lowerMessage.includes("password")) {
        showFieldError("password", "Inserisci una password per continuare.");
        return;
      }
      elements.resultError.textContent = operation === "merge"
        ? "Seleziona almeno due PDF per unirli."
        : message || "Controlla i file selezionati e le impostazioni, quindi riprova.";
      focusWhenReady(elements.picker);
    } else if (response.status === 413) {
      elements.resultError.textContent = operation === "images-to-pdf" &&
        message.toLowerCase().includes("pixel")
        ? "Le immagini superano il limite di dimensioni supportato. Riduci la risoluzione o seleziona meno immagini."
        : "La richiesta supera il limite di 100 MiB. Seleziona meno file o documenti più piccoli.";
    } else if (response.status === 415) {
      elements.resultError.textContent = operation === "images-to-pdf"
        ? "Seleziona solo immagini JPG o PNG."
        : operation === "documents-to-pdf"
          ? "Seleziona un file DOCX o ODT valido."
        : "Uno o più file non sono in formato PDF. Seleziona documenti PDF e riprova.";
    } else if (response.status === 422) {
      elements.resultError.textContent = operation === "images-to-pdf"
        ? "Una o più immagini non sono leggibili. Verifica che i file JPG o PNG siano validi."
        : operation === "documents-to-pdf"
          ? "Non è stato possibile convertire il documento. Verifica che il file DOCX o ODT sia valido."
        : "Non è stato possibile leggere " +
          (state.files.length === 1 ? "il PDF selezionato." : "uno dei PDF selezionati.") +
          " Verifica che il documento sia valido e non protetto da un'altra password.";
    } else if (operation === "documents-to-pdf" && response.status === 503) {
      elements.resultError.textContent = "La conversione DOCX/ODT non è disponibile sul server: è necessario installare o configurare LibreOffice.";
    } else if (operation === "documents-to-pdf" && response.status === 504) {
      elements.resultError.textContent = "La conversione ha superato il tempo massimo. Prova con un documento più semplice o più piccolo.";
    } else {
      elements.resultError.textContent = "Non è stato possibile completare l'operazione. Riprova.";
    }
  }

  function responseFilename(disposition) {
    if (!disposition) return "";
    const extended = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (extended) {
      try {
        return decodeURIComponent(extended[1].replace(/^"|"$/g, ""));
      } catch (error) {
        return "";
      }
    }
    const basic = disposition.match(/filename="?([^";]+)"?/i);
    return basic ? basic[1] : "";
  }

  function defaultFilename(operation) {
    if (operation === "split") return "split-pdfs.zip";
    if (operation === "merge") return "documento_merged.pdf";
    if (operation === "rename") return "renamed-pdfs.zip";
    if (operation === "encrypt") return "encrypted-pdfs.zip";
    if (operation === "images-to-pdf") return "immagini.pdf";
    if (operation === "documents-to-pdf") return "documento.pdf";
    return "testo-estratto.txt";
  }

  function showResult() {
    elements.resultSection.hidden = false;
  }

  function setResultState(resultState) {
    const icons = { idle: "•", working: "…", success: "✓", error: "!" };
    elements.resultSection.dataset.state = resultState;
    elements.resultIcon.textContent = icons[resultState] || icons.idle;
  }

  function clearResult() {
    if (state.downloadUrl) {
      URL.revokeObjectURL(state.downloadUrl);
      state.downloadUrl = null;
    }
    elements.resultSection.hidden = true;
    setResultState("idle");
    elements.resultStatus.textContent = "";
    elements.resultError.textContent = "";
    elements.downloadLink.hidden = true;
    elements.downloadLink.removeAttribute("href");
    elements.progress.hidden = true;
  }

  renderFiles();
  updateControls();
}());
