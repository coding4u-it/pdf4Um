/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.mycompany.pdf4um.model;

import java.util.Random;

/**
 *
 * @author france
 */
public class Critografia {
    String alfabeto = "[]()abcdefghijklmnopqrstuvwxyz#.&0123456789$£€,ABCDEFGHIJKLMNOPQRSTUVWXYZ@";
    Random cas;
    
    /**
     * metodo che genera una stringa casuale di lunghezza num, formata dai simboli in alfabeto, 
     * @param num cifre da generare
     * @param sw
     * @return 
     */
    public String generaCasuali(int num, boolean sw){
        String critto="";
        cas=new Random();
        for (int i=0; i<num; i++){
            if(sw)
             critto+=alfabeto.charAt(cas.nextInt(alfabeto.length())); 
            else
             critto+=cas.nextInt(10);  
        } 
        return critto;
    }    
}
