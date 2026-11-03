(function () {
  "use strict";

  const operationLabels = {
    split: "Dividi PDF",
    merge: "Unisci PDF",
    rename: "Rinomina PDF",
    encrypt: "Proteggi PDF",
    extract: "Estrai testo",
    anonymize: "Anonimizza PDF",
    "images-to-pdf": "Converti in PDF",
    "documents-to-pdf": "Converti ODT in PDF",
    "docx-to-pdf": "Converti DOCX in PDF"
  };
  const MAX_FILES = 32;
  const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png"];
  const ODT_EXTENSIONS = [".odt"];
  const DOCX_EXTENSIONS = [".docx"];
  const ANONYMIZE_CATEGORY_LABELS = {
    email: "Email",
    telefono: "Telefono",
    nomi: "Nome e cognome",
    "codice-fiscale": "Codice fiscale",
    "partita-iva": "Partita IVA",
    testo: "Testo cercato"
  };
  const PDF_ACCEPT = ".pdf,application/pdf";
  const IMAGE_ACCEPT = ".jpg,.jpeg,.png,image/jpeg,image/png";
  const ODT_ACCEPT = ".odt,application/vnd.oasis.opendocument.text";
  const DOCX_ACCEPT = ".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

  const state = {
    files: [],
    downloadUrl: null,
    busy: false,
    pendingFocus: null,
    anonymizePreview: null,
    anonymizePage: 0
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
    anonymizePreview: document.getElementById("anonymize-preview"),
    anonymizeSummary: document.getElementById("anonymize-summary"),
    anonymizeNoText: document.getElementById("anonymize-no-text"),
    anonymizePageSelect: document.getElementById("anonymize-page-select"),
    anonymizePageView: document.getElementById("anonymize-page-view"),
    anonymizeSuggestions: document.getElementById("anonymize-suggestions"),
    anonymizeManualAreas: document.getElementById("anonymize-manual-areas"),
    anonymizeConfirmed: document.getElementById("anonymize-confirmed"),
    anonymizePrevious: document.getElementById("anonymize-page-previous"),
    anonymizeNext: document.getElementById("anonymize-page-next"),
    runButton: document.getElementById("run-operation"),
    submitHelp: document.getElementById("submit-help"),
    privacyNote: document.getElementById("privacy-note-text"),
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
  elements.anonymizePageSelect.addEventListener("change", () => {
    state.anonymizePage = Number(elements.anonymizePageSelect.value);
    renderAnonymizationPage();
  });
  elements.anonymizePrevious.addEventListener("click", () => changeAnonymizationPage(-1));
  elements.anonymizeNext.addEventListener("click", () => changeAnonymizationPage(1));
  elements.anonymizeConfirmed.addEventListener("change", updateControls);
  document.querySelectorAll('input[name="anonymize-category"], #anonymize-terms').forEach((input) => {
    input.addEventListener("input", invalidateAnonymizationPreview);
    input.addEventListener("change", invalidateAnonymizationPreview);
  });

  function currentOperation() {
    const selected = elements.operationRadios.find((radio) => radio.checked);
    return selected ? selected.value : "split";
  }

  function addSelectedFiles() {
    const keys = new Set(state.files.map(fileKey));
    let excessFiles = 0;
    let unsupportedFiles = 0;
    const imageOperation = currentOperation() === "images-to-pdf";
    const documentOperation = isDocumentOperation(currentOperation());
    const documentLimit = documentOperation ? 1 : MAX_FILES;
    Array.from(elements.picker.files || []).forEach((file) => {
      if (!keys.has(fileKey(file))) {
        if (!isSupportedFile(file, imageOperation, currentOperation())) {
          unsupportedFiles += 1;
        } else if (state.files.length >= documentLimit) {
          excessFiles += 1;
        } else {
          state.files.push(file);
          keys.add(fileKey(file));
        }
      }
    });
    elements.picker.value = "";
    state.anonymizePreview = null;
    elements.anonymizeConfirmed.checked = false;
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
          : currentOperation() === "docx-to-pdf"
            ? "Con questa operazione puoi selezionare solo un file DOCX."
            : documentOperation
              ? "È supportato un solo documento ODT o DOCX."
            : "Per questa operazione seleziona solo file PDF.");
      }
      if (excessFiles > 0) {
        messages.push(documentOperation
          ? "Seleziona un solo documento ODT o DOCX."
          : "Puoi selezionare al massimo 32 file per operazione.");
      }
      elements.resultError.textContent = messages.join(" ");
    }
  }

  function isDocumentOperation(operation) {
    return operation === "documents-to-pdf" || operation === "docx-to-pdf";
  }

  function isSupportedFile(file, imageOperation, operation) {
    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (imageOperation) return IMAGE_EXTENSIONS.includes(extension);
    if (operation === "documents-to-pdf") return ODT_EXTENSIONS.includes(extension);
    if (operation === "docx-to-pdf") return DOCX_EXTENSIONS.includes(extension);
    return extension === ".pdf";
  }

  function clearSelectedFiles() {
    state.files = [];
    state.anonymizePreview = null;
    elements.anonymizeConfirmed.checked = false;
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
    const documentOperation = isDocumentOperation(currentOperation());
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
    const operation = currentOperation();
    const imageOperation = operation === "images-to-pdf";
    if (state.files.some((file) => !isSupportedFile(file, imageOperation, operation))) {
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
    const documentOperation = isDocumentOperation(operation);
    elements.picker.accept = imageOperation
      ? IMAGE_ACCEPT
      : operation === "docx-to-pdf" ? DOCX_ACCEPT
        : operation === "documents-to-pdf" ? ODT_ACCEPT : PDF_ACCEPT;
    elements.pickerTitle.textContent = imageOperation
      ? "Scegli immagini"
      : operation === "docx-to-pdf" ? "Scegli DOCX"
        : operation === "documents-to-pdf" ? "Scegli ODT" : "Scegli PDF";
    elements.pickerHelp.textContent = imageOperation
      ? "JPG o PNG · massimo 32 immagini e 100 MiB complessivi"
      : operation === "docx-to-pdf" ? "Un file DOCX · massimo 100 MiB"
        : operation === "documents-to-pdf" ? "Un file ODT · massimo 100 MiB"
        : "Massimo 32 PDF e 100 MiB complessivi per operazione";
    elements.operationRadios.forEach((radio) => { radio.disabled = state.busy; });
    document.querySelectorAll(
      ".settings-panel input, .settings-panel textarea, .settings-panel select, .settings-panel button"
    ).forEach((control) => { control.disabled = state.busy; });

    const splitMode = document.querySelector('input[name="split-mode"]:checked').value;
    elements.pagesField.hidden = splitMode !== "groups";
    const renameMode = document.querySelector('input[name="rename-mode"]:checked').value;
    elements.renamePanels.forEach((panel) => {
      panel.hidden = panel.dataset.renamePanel !== renameMode;
    });

    const requirement = getRequirement(operation);
    elements.runButton.textContent = operationLabels[operation];
    if (operation === "anonymize") {
      elements.runButton.textContent = hasCurrentAnonymizationPreview()
        ? "Anonimizza e scarica PDF"
        : "Analizza PDF";
    }
    elements.runButton.disabled = state.busy || !requirement.valid ||
      (operation === "anonymize" && hasCurrentAnonymizationPreview() &&
        !elements.anonymizeConfirmed.checked);
    elements.submitHelp.textContent = requirement.message;
    elements.clearSelection.disabled = state.files.length === 0 || state.busy;
    elements.selectionRequirement.textContent = selectionRequirement(operation);
    elements.selectionHint.textContent = imageOperation
      ? "L'ordine mostrato qui verrà mantenuto nelle pagine del PDF."
      : documentOperation
        ? "Per questa operazione puoi selezionare un solo documento."
        : "Per unire i PDF, usa i pulsanti su e giù per impostare l'ordine: il primo file determina il nome del risultato.";
    elements.privacyNote.textContent = "I documenti vengono elaborati sul server e rimossi al termine della richiesta.";
    syncFieldErrors(operation);
  }

  function selectionRequirement(operation) {
    if (operation === "anonymize") {
      return "Seleziona un solo PDF da esaminare e anonimizzare.";
    }
    if (operation === "split" || operation === "extract") {
      return operation === "split"
        ? "Per dividere il documento, seleziona esattamente un PDF."
        : "Per estrarre il testo, seleziona esattamente un PDF.";
    }
    if (operation === "images-to-pdf") {
      return "Seleziona da una a 32 immagini JPG o PNG da convertire.";
    }
    if (operation === "documents-to-pdf") {
      return "Per convertire il documento, seleziona un solo file ODT.";
    }
    if (operation === "docx-to-pdf") {
      return "Per convertire il documento, seleziona un solo file DOCX.";
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
    if (state.files.some((file) => !isSupportedFile(file, imageOperation, operation))) {
      return {
        valid: false,
        message: imageOperation
          ? "Seleziona solo immagini JPG o PNG."
          : operation === "docx-to-pdf"
            ? "Seleziona solo un file DOCX."
            : operation === "documents-to-pdf"
              ? "Seleziona solo un file ODT."
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
    } else if (operation === "anonymize" && state.files.length !== 1) {
      return { valid: false, message: "Seleziona un solo PDF da anonimizzare." };
    } else if (operation === "images-to-pdf" && state.files.length < 1) {
      return { valid: false, message: "Seleziona almeno un'immagine JPG o PNG da convertire." };
    } else if (operation === "documents-to-pdf" && state.files.length !== 1) {
      return { valid: false, message: "Seleziona un solo documento ODT da convertire." };
    } else if (operation === "docx-to-pdf" && state.files.length !== 1) {
      return { valid: false, message: "Seleziona un solo documento DOCX da convertire." };
    }
    return { valid: true, message: operation === "merge"
      ? "I PDF saranno uniti nell'ordine mostrato nell'elenco."
      : operation === "anonymize" && hasCurrentAnonymizationPreview()
        ? "Controlla le aree e conferma prima di rimuovere i dati."
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
    if (operation === "anonymize" && hasCurrentAnonymizationPreview() &&
        !elements.anonymizeConfirmed.checked) return;

    if (operation === "anonymize" && !hasCurrentAnonymizationPreview()) {
      await analyzeAnonymization();
      return;
    }

    const formData = buildRequest(operation);
    clearResult();
    showResult();
    setResultState("working");
    elements.resultStatus.textContent =
      "Preparazione dei file per " + operationLabels[operation].toLocaleLowerCase("it-IT") + ".";
    elements.resultError.textContent = "";
    elements.progress.hidden = false;
    state.busy = true;
    updateControls();
    renderFiles();

    try {
      const apiOperation = operation === "docx-to-pdf"
        ? "documents-to-pdf"
        : operation === "extract" ? "extract-text" : operation;
      const response = await fetch("api/" + apiOperation, {
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
      if (operation === "anonymize") {
        state.anonymizePreview = null;
        elements.anonymizePreview.hidden = true;
        elements.anonymizeConfirmed.checked = false;
      }
    } catch (error) {
      setResultState("error");
      elements.resultStatus.textContent = "";
      elements.resultError.textContent =
        "Impossibile raggiungere l'applicazione. Verifica la connessione al server e riprova.";
    } finally {
      state.busy = false;
      elements.progress.hidden = true;
      updateControls();
      renderFiles();
      if (state.pendingFocus && !state.pendingFocus.disabled) state.pendingFocus.focus();
      state.pendingFocus = null;
    }
  }

  async function analyzeAnonymization() {
    if (state.busy || state.files.length !== 1) return;
    const formData = new FormData();
    formData.append("file", state.files[0], state.files[0].name);
    formData.append(
      "categories",
      JSON.stringify(Array.from(document.querySelectorAll('input[name="anonymize-category"]:checked'))
        .map((input) => input.value))
    );
    formData.append("terms", document.getElementById("anonymize-terms").value);

    clearResult();
    showResult();
    setResultState("working");
    elements.resultStatus.textContent = "Analisi del PDF in corso.";
    elements.progress.hidden = false;
    state.busy = true;
    updateControls();

    try {
      const response = await fetch("api/anonymize-preview", { method: "POST", body: formData });
      if (!response.ok) {
        await handleFailure(response, "anonymize");
        return;
      }
      const result = await response.json();
      if (!Array.isArray(result.pages) || !Array.isArray(result.suggestions) ||
          typeof result.hasExtractableText !== "boolean") {
        throw new Error("Invalid anonymization preview response.");
      }
      state.anonymizePreview = {
        fileKey: fileKey(state.files[0]),
        pages: result.pages,
        hasExtractableText: result.hasExtractableText,
        suggestions: result.suggestions.map((suggestion) => ({ ...suggestion, selected: true })),
        manualAreas: []
      };
      state.anonymizePage = 0;
      elements.anonymizeConfirmed.checked = false;
      renderAnonymizationPreview();
      setResultState("success");
      elements.resultStatus.textContent =
        "Analisi completata. Rivedi le proposte e conferma prima di creare il PDF.";
      elements.resultError.textContent = "";
      elements.anonymizePreview.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      setResultState("error");
      elements.resultStatus.textContent = "";
      elements.resultError.textContent =
        "Non è stato possibile analizzare il PDF. Verifica la connessione e riprova.";
    } finally {
      state.busy = false;
      elements.progress.hidden = true;
      updateControls();
      renderFiles();
    }
  }

  function hasCurrentAnonymizationPreview() {
    return state.anonymizePreview !== null &&
      state.files.length === 1 &&
      state.anonymizePreview.fileKey === fileKey(state.files[0]);
  }

  function invalidateAnonymizationPreview() {
    if (!state.anonymizePreview) return;
    state.anonymizePreview = null;
    elements.anonymizePreview.hidden = true;
    elements.anonymizeConfirmed.checked = false;
    clearResult();
    updateControls();
  }

  function renderAnonymizationPreview() {
    const preview = state.anonymizePreview;
    if (!preview) return;
    elements.anonymizePreview.hidden = false;
    elements.anonymizePageSelect.replaceChildren();
    preview.pages.forEach((_page, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = String(index + 1);
      elements.anonymizePageSelect.append(option);
    });
    elements.anonymizePageSelect.value = String(state.anonymizePage);
    elements.anonymizePageSelect.disabled = preview.pages.length < 2;
    elements.anonymizePrevious.disabled = state.anonymizePage <= 0;
    elements.anonymizeNext.disabled = state.anonymizePage >= preview.pages.length - 1;
    elements.anonymizeSummary.textContent =
      preview.suggestions.length + " corrispondenze proposte · " +
      preview.manualAreas.length + " aree manuali";
    elements.anonymizeNoText.hidden = preview.hasExtractableText;

    elements.anonymizeSuggestions.replaceChildren();
    if (preview.suggestions.length === 0) {
      const empty = document.createElement("p");
      empty.className = "anonymize-empty";
      empty.textContent = "Nessuna corrispondenza trovata. Puoi comunque selezionare aree nel documento.";
      elements.anonymizeSuggestions.append(empty);
    } else {
      preview.suggestions.forEach((suggestion, index) => {
        const label = document.createElement("label");
        label.className = "anonymize-suggestion";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = suggestion.selected;
        checkbox.addEventListener("change", () => {
          suggestion.selected = checkbox.checked;
          elements.anonymizeConfirmed.checked = false;
          renderAnonymizationPage();
          updateControls();
        });
        const details = document.createElement("span");
        const category = document.createElement("strong");
        category.textContent = ANONYMIZE_CATEGORY_LABELS[suggestion.category] ||
          suggestion.category;
        const matchedText = document.createElement("small");
        matchedText.textContent = "“" + suggestion.text + "” · pagina " + (suggestion.page + 1);
        details.append(category, matchedText);
        label.append(checkbox, details);
        elements.anonymizeSuggestions.append(label);
      });
    }

    elements.anonymizeManualAreas.replaceChildren();
    if (preview.manualAreas.length === 0) {
      const empty = document.createElement("p");
      empty.className = "anonymize-empty";
      empty.textContent = "Nessuna area aggiunta.";
      elements.anonymizeManualAreas.append(empty);
    } else {
      preview.manualAreas.forEach((area, index) => {
        const item = document.createElement("div");
        item.className = "anonymize-manual-item";
        const description = document.createElement("span");
        description.textContent = "Area " + (index + 1) + " · pagina " + (area.page + 1);
        const remove = document.createElement("button");
        remove.className = "button button-quiet";
        remove.type = "button";
        remove.textContent = "Rimuovi";
        remove.setAttribute("aria-label", "Rimuovi area " + (index + 1));
        remove.addEventListener("click", () => {
          preview.manualAreas.splice(index, 1);
          elements.anonymizeConfirmed.checked = false;
          renderAnonymizationPreview();
          updateControls();
        });
        item.append(description, remove);
        elements.anonymizeManualAreas.append(item);
      });
    }
    renderAnonymizationPage();
  }

  function renderAnonymizationPage() {
    const preview = state.anonymizePreview;
    if (!preview || !preview.pages[state.anonymizePage]) return;
    const page = preview.pages[state.anonymizePage];
    const layer = document.createElement("div");
    layer.className = "anonymize-page-layer";
    const image = document.createElement("img");
    image.alt = "Anteprima della pagina " + (state.anonymizePage + 1);
    image.src = "data:image/png;base64," + page.image;
    image.width = page.width;
    image.height = page.height;
    const overlay = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    overlay.setAttribute("viewBox", "0 0 " + page.width + " " + page.height);
    overlay.setAttribute("aria-label", "Selezione delle aree da oscurare");
    overlay.style.pointerEvents = "all";

    const addOverlay = (area, className) => {
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", String(area.x0 * page.width));
      rect.setAttribute("y", String(area.y0 * page.height));
      rect.setAttribute("width", String((area.x1 - area.x0) * page.width));
      rect.setAttribute("height", String((area.y1 - area.y0) * page.height));
      rect.setAttribute("class", className);
      overlay.append(rect);
    };
    preview.suggestions.forEach((suggestion) => {
      if (suggestion.page === state.anonymizePage && suggestion.selected) {
        addOverlay(suggestion, "anonymize-suggested-area");
      }
    });
    preview.manualAreas.forEach((area) => {
      if (area.page === state.anonymizePage) addOverlay(area, "anonymize-manual-area");
    });

    let dragStart = null;
    let dragRect = null;
    const pointFor = (event) => {
      const bounds = overlay.getBoundingClientRect();
      return {
        x: Math.max(0, Math.min(page.width, (event.clientX - bounds.left) * page.width / bounds.width)),
        y: Math.max(0, Math.min(page.height, (event.clientY - bounds.top) * page.height / bounds.height))
      };
    };
    overlay.addEventListener("pointerdown", (event) => {
      if (state.busy || event.button !== 0) return;
      dragStart = pointFor(event);
      dragRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      dragRect.setAttribute("class", "anonymize-drawing-area");
      overlay.append(dragRect);
      overlay.setPointerCapture(event.pointerId);
    });
    overlay.addEventListener("pointermove", (event) => {
      if (!dragStart || !dragRect) return;
      const point = pointFor(event);
      dragRect.setAttribute("x", String(Math.min(dragStart.x, point.x)));
      dragRect.setAttribute("y", String(Math.min(dragStart.y, point.y)));
      dragRect.setAttribute("width", String(Math.abs(point.x - dragStart.x)));
      dragRect.setAttribute("height", String(Math.abs(point.y - dragStart.y)));
    });
    overlay.addEventListener("pointerup", (event) => {
      if (!dragStart) return;
      const end = pointFor(event);
      if (Math.abs(end.x - dragStart.x) > 4 && Math.abs(end.y - dragStart.y) > 4) {
        preview.manualAreas.push({
          page: state.anonymizePage,
          x0: Math.min(dragStart.x, end.x) / page.width,
          y0: Math.min(dragStart.y, end.y) / page.height,
          x1: Math.max(dragStart.x, end.x) / page.width,
          y1: Math.max(dragStart.y, end.y) / page.height
        });
        elements.anonymizeConfirmed.checked = false;
        renderAnonymizationPreview();
        updateControls();
      } else if (dragRect) {
        dragRect.remove();
      }
      dragStart = null;
      dragRect = null;
    });
    layer.append(image, overlay);
    elements.anonymizePageView.replaceChildren(layer);
  }

  function changeAnonymizationPage(delta) {
    const preview = state.anonymizePreview;
    if (!preview) return;
    state.anonymizePage = Math.max(
      0,
      Math.min(preview.pages.length - 1, state.anonymizePage + delta)
    );
    renderAnonymizationPreview();
  }

  function buildRequest(operation) {
    const formData = new FormData();
    const fileField = operation === "split" || operation === "extract" || operation === "anonymize" ||
      operation === "documents-to-pdf" || operation === "docx-to-pdf"
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
    } else if (operation === "anonymize") {
      const areas = [
        ...state.anonymizePreview.suggestions.filter((suggestion) => suggestion.selected),
        ...state.anonymizePreview.manualAreas
      ].map(({ page, x0, y0, x1, y1 }) => ({ page, x0, y0, x1, y1 }));
      formData.append("areas", JSON.stringify(areas));
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
        : operation === "anonymize"
          ? message || "Il PDF supera i limiti di pagine o dimensioni per l'anteprima."
          : "La richiesta supera il limite di 100 MiB. Seleziona meno file o documenti più piccoli.";
    } else if (response.status === 415) {
      elements.resultError.textContent = operation === "images-to-pdf"
        ? "Seleziona solo immagini JPG o PNG."
        : operation === "documents-to-pdf" || operation === "docx-to-pdf"
          ? "Seleziona un file DOCX o ODT valido."
          : "Uno o più file non sono in formato PDF. Seleziona documenti PDF e riprova.";
    } else if (response.status === 422) {
      elements.resultError.textContent = operation === "images-to-pdf"
        ? "Una o più immagini non sono leggibili. Verifica che i file JPG o PNG siano validi."
        : operation === "documents-to-pdf" || operation === "docx-to-pdf"
          ? "Non è stato possibile convertire il documento. Verifica che il file DOCX o ODT sia valido."
          : "Non è stato possibile leggere " +
            (state.files.length === 1 ? "il PDF selezionato." : "uno dei PDF selezionati.") +
            " Verifica che il documento sia valido e non protetto da un'altra password.";
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
    if (operation === "documents-to-pdf" || operation === "docx-to-pdf") return "documento.pdf";
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
