(function () {
  "use strict";

  const operationLabels = {
    split: "Dividi PDF",
    merge: "Unisci PDF",
    rename: "Rinomina PDF",
    encrypt: "Proteggi PDF",
    extract: "Estrai testo",
    "images-to-pdf": "Converti in PDF",
    "documents-to-pdf": "Converti ODT in PDF",
    "docx-to-pdf-browser": "Converti DOCX in PDF"
  };
  const MAX_FILES = 32;
  const MAX_DOCX_BYTES = 50 * 1024 * 1024;
  const MAX_DOCX_PAGES = 50;
  const DOCX_CAPTURE_SCALE = 1.5;
  const CSS_PIXELS_TO_MM = 25.4 / 96;
  const A4_TOLERANCE_MM = 1;
  const A4_PORTRAIT = [210, 297];
  const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png"];
  const ODT_EXTENSIONS = [".odt"];
  const DOCX_EXTENSIONS = [".docx"];
  const PDF_ACCEPT = ".pdf,application/pdf";
  const IMAGE_ACCEPT = ".jpg,.jpeg,.png,image/jpeg,image/png";
  const ODT_ACCEPT = ".odt,application/vnd.oasis.opendocument.text";
  const DOCX_ACCEPT = ".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

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
        } else if (currentOperation() === "docx-to-pdf-browser" && file.size > MAX_DOCX_BYTES) {
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
          : currentOperation() === "docx-to-pdf-browser"
            ? "Con questa operazione puoi selezionare solo un file DOCX."
            : documentOperation
              ? "È supportato un solo documento ODT."
            : "Per questa operazione seleziona solo file PDF.");
      }
      if (excessFiles > 0) {
        messages.push(currentOperation() === "docx-to-pdf-browser"
          ? "Seleziona un solo DOCX, non più grande di 50 MiB."
          : documentOperation
            ? "Seleziona un solo documento ODT."
            : "Puoi selezionare al massimo 32 file per operazione.");
      }
      elements.resultError.textContent = messages.join(" ");
    }
  }

  function isDocumentOperation(operation) {
    return operation === "documents-to-pdf" || operation === "docx-to-pdf-browser";
  }

  function isSupportedFile(file, imageOperation, operation) {
    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (imageOperation) return IMAGE_EXTENSIONS.includes(extension);
    if (operation === "documents-to-pdf") return ODT_EXTENSIONS.includes(extension);
    if (operation === "docx-to-pdf-browser") return DOCX_EXTENSIONS.includes(extension);
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
      : operation === "docx-to-pdf-browser" ? DOCX_ACCEPT
        : operation === "documents-to-pdf" ? ODT_ACCEPT : PDF_ACCEPT;
    elements.pickerTitle.textContent = imageOperation
      ? "Scegli immagini"
      : operation === "docx-to-pdf-browser" ? "Scegli DOCX"
        : operation === "documents-to-pdf" ? "Scegli ODT" : "Scegli PDF";
    elements.pickerHelp.textContent = imageOperation
      ? "JPG o PNG · massimo 32 immagini e 100 MiB complessivi"
      : operation === "docx-to-pdf-browser" ? "Un file DOCX · massimo 50 MiB · conversione nel browser"
        : operation === "documents-to-pdf" ? "Un file ODT · massimo 100 MiB"
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
      : operation === "docx-to-pdf-browser"
        ? "Il DOCX viene convertito interamente nel browser e non viene inviato al server."
        : documentOperation
        ? "Per questa operazione puoi selezionare un solo documento."
        : "Per unire i PDF, usa i pulsanti su e giù per impostare l'ordine: il primo file determina il nome del risultato.";
    elements.privacyNote.textContent = operation === "docx-to-pdf-browser"
      ? "Il DOCX e il PDF restano sul tuo dispositivo; il file non viene inviato al server."
      : "I documenti vengono elaborati sul server e rimossi al termine della richiesta.";
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
      return "Per convertire il documento, seleziona un solo file ODT.";
    }
    if (operation === "docx-to-pdf-browser") {
      return "Seleziona un solo DOCX fino a 50 MiB; la conversione avviene nel browser.";
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
          : operation === "docx-to-pdf-browser"
            ? "Seleziona solo un file DOCX."
            : operation === "documents-to-pdf"
              ? "Seleziona solo un file ODT."
            : "Seleziona solo file PDF."
      };
    }

    if (operation === "docx-to-pdf-browser" &&
        state.files.some((file) => file.size > MAX_DOCX_BYTES)) {
      return { valid: false, message: "Il file DOCX deve essere più piccolo di 50 MiB." };
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
      return { valid: false, message: "Seleziona un solo documento ODT da convertire." };
    } else if (operation === "docx-to-pdf-browser" && state.files.length !== 1) {
      return { valid: false, message: "Seleziona un solo documento DOCX da convertire." };
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

    const browserDocxOperation = operation === "docx-to-pdf-browser";
    const formData = browserDocxOperation ? null : buildRequest(operation);
    clearResult();
    showResult();
    setResultState("working");
    elements.resultStatus.textContent = browserDocxOperation
      ? "Render del documento e creazione del PDF nel browser."
      : "Preparazione dei file per " + operationLabels[operation].toLocaleLowerCase("it-IT") + ".";
    elements.resultError.textContent = "";
    elements.progress.hidden = false;
    state.busy = true;
    updateControls();
    renderFiles();

    try {
      let blob;
      let filename;
      if (browserDocxOperation) {
        blob = await renderDocxToPdf(state.files[0]);
        filename = state.files[0].name.replace(/\.docx$/i, ".pdf");
      } else {
        const response = await fetch("api/" + (operation === "extract" ? "extract-text" : operation), {
          method: "POST",
          body: formData
        });
        if (!response.ok) {
          await handleFailure(response, operation);
          return;
        }
        blob = await response.blob();
        filename = responseFilename(response.headers.get("Content-Disposition")) || defaultFilename(operation);
      }

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
      if (browserDocxOperation) console.error("Browser DOCX conversion failed.", error);
      setResultState("error");
      elements.resultStatus.textContent = "";
      elements.resultError.textContent = browserDocxOperation
        ? error instanceof Error && (
          error.message.startsWith("Librerie di conversione") ||
          error.message.startsWith("Il documento supera il limite") ||
          error.message.startsWith("Il documento non contiene") ||
          error.message.startsWith("Una pagina del documento")
        )
          ? error.message
          : "Il browser non è riuscito a renderizzare questo DOCX. Prova con un documento più semplice o aggiornato in Word."
        : "Impossibile raggiungere l'applicazione. Verifica la connessione al server e riprova.";
    } finally {
      state.busy = false;
      elements.progress.hidden = true;
      updateControls();
      renderFiles();
      if (state.pendingFocus && !state.pendingFocus.disabled) state.pendingFocus.focus();
      state.pendingFocus = null;
    }
  }

  async function renderDocxToPdf(file) {
    if (!window.docx || typeof window.docx.renderAsync !== "function" ||
        typeof window.html2canvas !== "function" || !window.jspdf || !window.jspdf.jsPDF) {
      throw new Error("Librerie di conversione non disponibili. Verifica la connessione e ricarica la pagina.");
    }

    const stage = document.createElement("div");
    stage.className = "docx-render-stage";
    stage.setAttribute("aria-hidden", "true");
    stage.style.position = "fixed";
    stage.style.left = "-100000px";
    stage.style.top = "0";
    stage.style.zIndex = "-1";
    document.body.append(stage);

    try {
      await window.docx.renderAsync(file, stage, stage, {
        breakPages: true,
        ignoreLastRenderedPageBreak: false,
        renderHeaders: true,
        renderFooters: true,
        useBase64URL: true
      });
      if (document.fonts && document.fonts.ready) await document.fonts.ready;

      const pages = Array.from(stage.querySelectorAll("section.docx"));
      if (pages.length === 0) {
        throw new Error("Il documento non contiene pagine renderizzabili.");
      }
      if (pages.length > MAX_DOCX_PAGES) {
        throw new Error("Il documento supera il limite di " + MAX_DOCX_PAGES + " pagine.");
      }

      const { jsPDF } = window.jspdf;
      const renderedPages = pages.map((page) => {
        const bounds = page.getBoundingClientRect();
        const computedStyle = window.getComputedStyle(page);
        const widthPx = bounds.width;
        const heightPx = Number.parseFloat(computedStyle.minHeight) || bounds.height;
        if (widthPx <= 0 || heightPx <= 0) {
          throw new Error("Una pagina del documento non ha dimensioni valide.");
        }

        page.style.minHeight = "0";
        page.style.height = "auto";
        page.style.maxHeight = "none";
        page.style.overflow = "visible";
        const contentHeightPx = Math.max(page.scrollHeight, page.getBoundingClientRect().height);
        return {
          element: page,
          widthPx,
          heightPx,
          pageCount: Math.max(1, Math.ceil(contentHeightPx / heightPx))
        };
      });
      const pageCount = renderedPages.reduce((count, page) => count + page.pageCount, 0);
      if (pageCount > MAX_DOCX_PAGES) {
        throw new Error("Il documento supera il limite di " + MAX_DOCX_PAGES + " pagine.");
      }

      let pdf = null;
      let outputPage = 0;
      for (const renderedPage of renderedPages) {
        const { element, widthPx, heightPx, pageCount: sectionPageCount } = renderedPage;
        const pageFormat = docxPageFormat(widthPx, heightPx);
        const [widthMm, heightMm] = pageFormat;
        const orientation = widthMm > heightMm ? "landscape" : "portrait";

        for (let sectionPage = 0; sectionPage < sectionPageCount; sectionPage += 1) {
          outputPage += 1;
          elements.resultStatus.textContent = "Conversione della pagina " +
            outputPage + " di " + pageCount + " nel browser.";
          const canvas = await window.html2canvas(element, {
            backgroundColor: "#ffffff",
            height: heightPx,
            logging: false,
            scale: DOCX_CAPTURE_SCALE,
            useCORS: false,
            width: widthPx,
            y: sectionPage * heightPx
          });
          if (!pdf) {
            pdf = new jsPDF({
              orientation,
              unit: "mm",
              format: pageFormat,
              compress: true
            });
          } else {
            pdf.addPage(pageFormat, orientation);
          }
          pdf.addImage(canvas.toDataURL("image/jpeg", 0.94), "JPEG", 0, 0, widthMm, heightMm);
          canvas.width = 0;
          canvas.height = 0;
          await new Promise((resolve) => requestAnimationFrame(resolve));
        }
      }
      return pdf.output("blob");
    } finally {
      stage.remove();
    }
  }

  function docxPageFormat(widthPx, heightPx) {
    const widthMm = widthPx * CSS_PIXELS_TO_MM;
    const heightMm = heightPx * CSS_PIXELS_TO_MM;
    const portrait = widthMm <= heightMm;
    const expectedWidth = portrait ? A4_PORTRAIT[0] : A4_PORTRAIT[1];
    const expectedHeight = portrait ? A4_PORTRAIT[1] : A4_PORTRAIT[0];
    if (Math.abs(widthMm - expectedWidth) <= A4_TOLERANCE_MM &&
        Math.abs(heightMm - expectedHeight) <= A4_TOLERANCE_MM) {
      return [expectedWidth, expectedHeight];
    }
    return [widthMm, heightMm];
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
