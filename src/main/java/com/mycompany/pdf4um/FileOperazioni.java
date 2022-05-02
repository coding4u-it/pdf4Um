package com.mycompany.pdf4um;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

public class FileOperazioni {
    
    private String nomeFile;
    private String dir=System.getProperty("user.dir")+System.getProperty("file.separator");
    private String nn="";//memorizza le cifre casuali da aggiungere al nome
    private String jarPath = this.getClass().getProtectionDomain().getCodeSource().getLocation().getPath();
    private final String ESTENSIONE=".pdf";
    
    public FileOperazioni() {
    }
    
    public FileOperazioni(String nomeFile){
        this.nomeFile=dir+nomeFile;
    }
    /**
     * il metodo rinomina i file estraendo l'estensione e portandola alla fine del nuovo nome.
     * il nuovo nome viene calcolato mediante la generazione di n numeri casuali.
     * @param file // individua il file da rinominare
     * @param ccri //codice numerico casuale
     * @return  info restituisce nome file e codice numerico casuale 
     */
    public String rinominaFileCasuale(File file, String ccri){
        nn="";
        String info;
        info=file.getName().substring(file.getName().length()-ESTENSIONE.length());
        nn=ccri;
        rinominaFile(file);
        return info+";"+ccri+"\n";
    }
    
    /**
     * il metodo rinomina i file estraendo l'estensione e portandola alla fine del nuovo nome.
     * che avrà un numero finale per differenziale dal gruppo di file
     * @param file // individua il file da rinominare
     * @param nnf // assegna il nuovo nome
     * @param conta // assegna l'incremento
     */
    public void rinominaFile(File file, String nnf, int conta){
        File nFile=new File (file.getParent()+"/"+nnf+conta+ESTENSIONE);
        if(file.renameTo(nFile))
            System.out.println("ok "+nFile.getName());
    }
   
    /**
     * il metodo rinomina i file estraendo l'estensione e portandola alla fine del nome.
     * @param file // individua il file da rinominare
     */
     public void rinominaFile(File file){
        String tmp=file.getPath().replace(ESTENSIONE, "");//rimuove l'estensione
        File nFile=new File (tmp+nn+ESTENSIONE);//inserisce le cifre casuali e l'estensione
        if(file.renameTo(nFile))
            System.out.println("ok "+nFile.getName());
    }
     
    /**
     * il metodo consente la scrittura in un file di testo
     * @param testo
     * @param ap
     * @return 
     */
    public String scrittura(String testo,boolean ap){
        String tmp="scrittura eseguita con successo!";
        PrintWriter outputStream=null;
        try {
            outputStream= new PrintWriter(new FileOutputStream(nomeFile,ap));
        } 
        catch (FileNotFoundException e){
            tmp="file di testo non trovato";
        }
        outputStream.println(testo);
        outputStream.close();
        return tmp;
    }
    
     /**
     * il metodo consente la scrittura in un file di testo con il metodo writeString
     * @param testo
     * @throws java.io.IOException 
     */
    public void scritturaS(String testo) throws IOException{
        Path nf=Path.of(nomeFile);
        Files.writeString(nf,testo);
    }
    
    /**
     * il metodo consente la lettura del file di testo
     * @return 
     */
    public String lettura(){
        String tmp="File Aperto!\n";
        Scanner inputStream=null;
        try {
            inputStream=new Scanner (new File(nomeFile));
        }
        catch (FileNotFoundException e){
            return tmp="File di lettura non trovato";
        }
        while(inputStream.hasNextLine()){
            String riga=inputStream.nextLine();
            tmp+=riga+"\n";
        }
        inputStream.close();
        return tmp;
    }

    public String getNomeFile() {
        return nomeFile;
    }

    public String getNn() {
        return nn;
    }

    public void setNn(String nn) {
        this.nn = nn;
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

    /**
     * @param nomeFile the nomeFile to set
     */
    public void setNomeFile(String nomeFile) {
        this.nomeFile = nomeFile;
    }
}
