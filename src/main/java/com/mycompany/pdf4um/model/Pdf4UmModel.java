package com.mycompany.pdf4um.model;

import java.io.File;
import java.io.IOException;

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

    public void rename(File[] files, boolean sequential, String prefix, int startingNumber,
            int randomLength, boolean useSymbols) {
        if (sequential) {
            int number = startingNumber;
            for (File file : files) {
                fileOperations.rinominaFile(file, prefix, number++);
            }
            return;
        }

        StringBuilder export = new StringBuilder();
        for (File file : files) {
            String randomCode = critografia.generaCasuali(randomLength, useSymbols);
            export.append(fileOperations.rinominaFileCasuale(file, randomCode));
        }
        new FileOperazioni("esporta.csv").scrittura(export.toString(), false);
    }

    public void encrypt(File[] files, String password, boolean allowOpen, boolean allowPrint,
            boolean allowCopy, boolean allowModify, boolean allowAssembly) throws IOException {
        for (File file : files) {
            pdfTools.criptPDF(file, password, allowOpen, allowPrint, allowCopy, allowModify,
                    allowAssembly);
        }
    }

    public void extractText(File file) throws IOException {
        FileOperazioni textFile = new FileOperazioni();
        textFile.setNomeFile(file.getPath().replace(".pdf", "_text.txt"));
        textFile.scritturaS(pdfTools.strip(file));
    }
}
