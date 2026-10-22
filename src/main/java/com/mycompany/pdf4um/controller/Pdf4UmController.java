package com.mycompany.pdf4um.controller;

import com.mycompany.pdf4um.model.Pdf4UmModel;
import java.io.File;
import java.io.IOException;

public class Pdf4UmController {
    private final Pdf4UmModel model;
    private File[] selectedFiles = new File[0];
    private String password = "";

    public Pdf4UmController() {
        this(new Pdf4UmModel());
    }

    Pdf4UmController(Pdf4UmModel model) {
        this.model = model;
    }

    public void setSelectedFiles(File[] files) {
        selectedFiles = files == null ? new File[0] : files.clone();
    }

    public void setPassword(String password) {
        this.password = password == null ? "" : password;
    }

    public void split(boolean splitByGroup, String pagesPerPart) throws IOException {
        requireExactlyOneFile();
        int pages = 1;
        if (splitByGroup) {
            try {
                pages = Integer.parseInt(pagesPerPart);
            } catch (NumberFormatException ex) {
                throw new IllegalArgumentException("Inserisci un numero di pagine valido.", ex);
            }
            if (pages < 1) {
                throw new IllegalArgumentException("Il numero di pagine deve essere maggiore di zero.");
            }
        }
        model.split(selectedFiles[0], pages);
    }

    public void merge() throws IOException {
        if (selectedFiles.length < 2) {
            throw new IllegalArgumentException("Devi selezionare almeno due file!");
        }
        model.merge(selectedFiles);
    }

    public void rename(boolean sequential, String prefix, int startingNumber, int randomLength,
            boolean useSymbols) {
        requireFiles();
        model.rename(selectedFiles, sequential, prefix, startingNumber, randomLength, useSymbols);
    }

    public void encrypt(boolean allowOpen, boolean allowPrint, boolean allowCopy,
            boolean allowModify, boolean allowAssembly) throws IOException {
        requireFiles();
        model.encrypt(selectedFiles, password, allowOpen, allowPrint, allowCopy, allowModify,
                allowAssembly);
    }

    public void extractText() throws IOException {
        requireExactlyOneFile();
        model.extractText(selectedFiles[0]);
    }

    private void requireExactlyOneFile() {
        if (selectedFiles.length != 1) {
            throw new IllegalArgumentException("Devi selezionare un solo file!");
        }
    }

    private void requireFiles() {
        if (selectedFiles.length == 0) {
            throw new IllegalArgumentException("Devi selezionare almeno un file!");
        }
    }
}
