package com.mycompany.pdf4um.controller;

import com.mycompany.pdf4um.model.Pdf4UmModel;
import java.io.File;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

/**
 * Stateless request coordinator. Inputs are supplied per operation so no browser request can
 * observe file selections or passwords from another request.
 */
public class Pdf4UmController {
    private final Pdf4UmModel model;

    public Pdf4UmController() {
        this(new Pdf4UmModel());
    }

    Pdf4UmController(Pdf4UmModel model) {
        this.model = model;
    }

    public void split(File[] files, boolean splitByGroup, String pagesPerPart) throws IOException {
        requireExactlyOneFile(files);
        int pages = 1;
        if (splitByGroup) {
            try {
                pages = Integer.parseInt(pagesPerPart);
            } catch (NumberFormatException exception) {
                throw new IllegalArgumentException("Insert a valid pages-per-part number.",
                        exception);
            }
            if (pages < 1) {
                throw new IllegalArgumentException("Pages per part must be greater than zero.");
            }
        }
        model.split(files[0], pages);
    }

    public void merge(File[] files) throws IOException {
        if (files == null || files.length < 2) {
            throw new IllegalArgumentException("Select at least two PDF files.");
        }
        model.merge(files);
    }

    public List<File> renameCopies(File[] files, Path outputDirectory, boolean sequential,
            String prefix, int startingNumber, int randomLength, boolean useSymbols)
            throws IOException {
        requireFiles(files);
        return model.renameCopies(files, outputDirectory, sequential, prefix, startingNumber,
                randomLength, useSymbols);
    }

    public void encrypt(File[] files, String password, boolean allowOpen, boolean allowPrint,
            boolean allowCopy, boolean allowModify, boolean allowAssembly) throws IOException {
        requireFiles(files);
        if (password == null || password.isEmpty()) {
            throw new IllegalArgumentException("Password is required.");
        }
        model.encrypt(files, password, allowOpen, allowPrint, allowCopy, allowModify,
                allowAssembly);
    }

    public String extractText(File[] files) throws IOException {
        requireExactlyOneFile(files);
        return model.extractText(files[0]);
    }

    private static void requireExactlyOneFile(File[] files) {
        if (files == null || files.length != 1) {
            throw new IllegalArgumentException("Select exactly one PDF file.");
        }
    }

    private static void requireFiles(File[] files) {
        if (files == null || files.length == 0) {
            throw new IllegalArgumentException("Select at least one PDF file.");
        }
    }
}
