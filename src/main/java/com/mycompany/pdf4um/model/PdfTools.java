/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.mycompany.pdf4um.model;

import java.util.List;
import java.io.File;
import java.io.IOException;
import org.apache.pdfbox.multipdf.PDFMergerUtility;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.apache.pdfbox.multipdf.Splitter; 
import org.apache.pdfbox.pdmodel.encryption.AccessPermission;
import org.apache.pdfbox.pdmodel.encryption.StandardProtectionPolicy;
import org.apache.pdfbox.text.PDFTextStripper;

/**
 *
 * @author france
 */
public class PdfTools {
    private PDDocument doc;
    private PDPage page;
    private final String dir=System.getProperty("user.dir")+System.getProperty("file.separator");
    private String classeCon;
    private String jarPath = this.getClass().getProtectionDomain().getCodeSource().getLocation().getPath();
    private final String ESTENSIONE=".pdf";
    
    public PdfTools() {
    }
      
   /**
    * il metodo effettua un taglio nel file pdf per tutte le pagine
    * @param nomeFile individua il file da tagliare
     * @param num
     * @return 
    */
    public String cutStrip (File nomeFile,int num){
        String nnf="errore";
        try{
          setDoc(PDDocument.load(nomeFile));
          for(int i=0;i<doc.getNumberOfPages();i++){
              page = (PDPage)doc.getDocumentCatalog().getPages().get(i);
              page.setCropBox(new PDRectangle(0,21,800,820));
          }
          page = (PDPage)doc.getDocumentCatalog().getPages().get(0);
          page.setCropBox(new PDRectangle(0,21,800,690));
          classeCon=nomeFile.getName().substring(20,23);//estrae la classe di concorso dal file
          nnf=nomeFile.getName().substring(0, 3)+classeCon+num+ESTENSIONE;//estrae e inserisce l'estensione del file
          doc.save(getDir()+nnf);
          doc.close();
        } catch (IOException e) {       }
        return nnf;
    }

    /**
     * Il metodo crea un nuovo, o modifica, un file pdf 
     * la scelta avviene con il parametro oldfile 
     * se viene inserito null, si crea un nuovo pdf, altrimenti se viene inserito il nome del file
     * viene eseguita la modifica ti tale file con inserimento del testo;
     * 
     * @param nomeFile assegna il nome al nuovo file / modifica il nuome con mod
     * @param oldFile  carica il file da modificare null se si deve creare nuovo file
     * @param testo inserisce il testo al nuovo file / o lo aggiunge al file modificato
     * @throws java.io.IOException
     */
    public void creaModifyPdf(String nomeFile, File oldFile, String testo) throws IOException {
      doc = PDDocument.load(oldFile);
      //Retrieving the pages of the doc 
      PDPage page = doc.getPage(0);
      PDPageContentStream contentStream = new PDPageContentStream(doc, page, PDPageContentStream.AppendMode.APPEND,false);
      //Begin the Content stream 
      contentStream.beginText(); 
      //Setting the font to the Content stream  
      contentStream.setFont(PDType1Font.TIMES_BOLD, 14);
      //Setting the position for the line 
      contentStream.newLineAtOffset(50, 700);
      //Adding text in the form of string 
      contentStream.showText("Classe Concorso: "+testo);      
      //Ending the content stream
      contentStream.endText();
      //Closing the content stream
      contentStream.close();
      //Saving the doc
      doc.save(new File(nomeFile));
      doc.close();
    }  
      
    /**
     * Il metodo suddivide un documento PDF in input in più file PDF, ognuno 
     * contiene un intervallo pag di pagine del documento di origine.
     * i file splittati saranno differenziati attraverso un progressivo
     * @param sourceFile file sorgente
     * @param pag
     * @throws java.io.IOException
    */
    public void split(File sourceFile, int pag) throws IOException{
        Splitter splitter = new Splitter();
        splitter.setSplitAtPage(pag);
        try (PDDocument source = PDDocument.load(sourceFile)) {
            List<PDDocument> pages = splitter.split(source);
            try {
                int i = 0;
                String nome = "_000";
                for (PDDocument part : pages) {
                    i++;
                    if (i == 10) {
                        nome = "_00";
                    }
                    if (i == 100) {
                        nome = "_0";
                    }
                    part.save(outputPath(sourceFile, nome + i));
                }
            } finally {
                for (PDDocument part : pages) {
                    part.close();
                }
            }
        }
    }
    
    /**
     * Il metodo unisce più documenti PDF in input in un singolo file PDF
     * il nome del file destinazione corrisponde al nome del primo documento _merged 
     * @param sourceFile lista file sorgente
     * @throws java.io.IOException
    */
    public void merge(File[] sourceFile) throws IOException{
          // instantiatE PDFMergerUtility class
          PDFMergerUtility pdfMerger = new PDFMergerUtility();
          // set destination file path
          pdfMerger.setDestinationFileName(outputPath(sourceFile[0], "_merged"));
          // add all source files, to be merged, to pdfMerger
          for(File ff:sourceFile)
            pdfMerger.addSource(ff);
          // merge documents
          pdfMerger.mergeDocuments(null);
    }
    
    /**
     * Il metodo cripta un documento PDF in input 
     * @param sourceFile file sorgente
     * @throws java.io.IOException
    */
    public void criptPDF(File sourceFile, String pass, boolean ...i) throws IOException{
        try (PDDocument document = PDDocument.load(sourceFile)) {
            // Define the length of the encryption key.
            int keyLength = 256;
            String admin = pass + pass;
            AccessPermission ap = new AccessPermission();
            if (!i[0]) {
                ap.setReadOnly();
            }
            ap.setCanPrint(!i[1]);
            ap.setCanExtractContent(!i[2]);
            ap.setCanModify(!i[3]);
            ap.setCanAssembleDocument(!i[4]);

            StandardProtectionPolicy policy = new StandardProtectionPolicy(admin, pass, ap);
            policy.setEncryptionKeyLength(keyLength);
            policy.setPermissions(ap);
            document.protect(policy);
            document.save(outputPath(sourceFile, "_cript"));
        }
    }

    private String outputPath(File sourceFile, String suffix) {
        String name = sourceFile.getName();
        int extension = name.toLowerCase(java.util.Locale.ROOT).lastIndexOf(ESTENSIONE);
        String stem = extension < 0 ? name : name.substring(0, extension);
        return sourceFile.toPath().resolveSibling(stem + suffix + ESTENSIONE).toString();
    }
    
    /**
     * il metodo estrae tutto il testo da un file pdf.
     * @param sourceFile 
     * @return  
     */
    public String strip(File sourceFile) throws IOException {
        try (PDDocument document = PDDocument.load(sourceFile)) {
            return new PDFTextStripper().getText(document);
        }
    }
    
    /**
     * @return the doc
     */
    public PDDocument getDoc() {
        return doc;
    }

    /**
     * @param doc the doc to set
     */
    public void setDoc(PDDocument doc) {
        this.doc = doc;
    }

    /**
     * @return the classeCon
     */
    public String getClasseCon() {
        return classeCon;
    }

    /**
     * @return the dir
     */
    public String getDir() {
        return dir;
    }
    
    public String getJarPath() {
        return jarPath;
    }
}