package com.mycompany.pdf4um.model;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class Pdf4UmModel {
    private final PdfTools pdfTools = new PdfTools();
    private final FileOperazioni fileOperations = new FileOperazioni();
    private final Critografia critografia = new Critografia();

    public void split(File file, int pagesPerPart) throws IOException {
        pdfTools.split(file, pagesPerPart);
    }

    public void merge(File[] files) throws IOException {
        pdfTools.merge(files);
    }

    /**
     * Creates renamed copies in a caller-owned workspace without changing the input files or
     * writing the random-mode CSV to the process working directory.
     *
     * @return output PDFs, followed by esporta.csv in random mode
     */
    public List<File> renameCopies(File[] files, Path outputDirectory, boolean sequential,
            String prefix, int startingNumber, int randomLength, boolean useSymbols)
            throws IOException {
        Files.createDirectories(outputDirectory);
        List<File> outputs = new ArrayList<>();
        StringBuilder export = new StringBuilder();
        int number = startingNumber;

        for (File file : files) {
            String outputName;
            if (sequential) {
                outputName = prefix + number++ + ".pdf";
            } else {
                String randomCode = critografia.generaCasuali(randomLength, useSymbols);
                outputName = file.getName().substring(0,
                        file.getName().length() - ".pdf".length()) + randomCode + ".pdf";
                // The legacy export format starts with the extension, not the source stem.
                export.append(".pdf;").append(randomCode).append('\n');
            }
            Path target = outputDirectory.toAbsolutePath().normalize().resolve(outputName).normalize();
            if (!target.getParent().equals(outputDirectory.toAbsolutePath().normalize())) {
                throw new IllegalArgumentException("Invalid output filename.");
            }
            outputs.add(fileOperations.copyTo(file, target.toAbsolutePath().normalize()));
        }

        if (!sequential) {
            Path exportFile = outputDirectory.resolve("esporta.csv");
            fileOperations.writeText(exportFile, export.toString());
            outputs.add(exportFile.toFile());
        }
        return outputs;
    }

    public void encrypt(File[] files, String password, boolean allowOpen, boolean allowPrint,
            boolean allowCopy, boolean allowModify, boolean allowAssembly) throws IOException {
        for (File file : files) {
            pdfTools.criptPDF(file, password, allowOpen, allowPrint, allowCopy, allowModify,
                    allowAssembly);
        }
    }

    public String extractText(File file) throws IOException {
        return pdfTools.strip(file);
    }
}
