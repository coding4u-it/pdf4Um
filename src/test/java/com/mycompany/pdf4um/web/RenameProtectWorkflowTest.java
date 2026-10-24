package com.mycompany.pdf4um.web;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.Map;
import java.net.http.HttpResponse;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.junit.Test;

public class RenameProtectWorkflowTest extends WebWorkflowTestSupport {

    @Test
    public void renameReturnsCopiesAndProtectionCanBeReadWithSubmittedPassword()
            throws Exception {
        byte[] original = createPdf("ORIGINAL CONTENT");
        HttpResponse<byte[]> renamed = post("/api/rename",
                fields("mode", "sequential", "prefix", "Copy-", "startingNumber", "2"),
                file("files", "original.pdf", original));
        assertEquals(200, renamed.statusCode());
        Map<String, byte[]> copies = zipEntries(renamed.body());
        assertTrue(copies.containsKey("Copy-2.pdf"));
        try (PDDocument copy = PDDocument.load(copies.get("Copy-2.pdf"))) {
            assertEquals(1, copy.getNumberOfPages());
        }

        HttpResponse<byte[]> protectedResult = post("/api/encrypt",
                fields("password", "local-test-password", "allowOpen", "false",
                        "allowPrint", "false", "allowCopy", "false",
                        "allowModify", "false", "allowAssembly", "false"),
                file("files", "original.pdf", original));
        assertEquals(200, protectedResult.statusCode());
        Map<String, byte[]> protectedFiles = zipEntries(protectedResult.body());
        assertTrue(protectedFiles.containsKey("original_cript.pdf"));
        try (PDDocument protectedPdf =
                PDDocument.load(protectedFiles.get("original_cript.pdf"), "local-test-password")) {
            assertTrue(protectedPdf.isEncrypted());
            assertEquals(1, protectedPdf.getNumberOfPages());
        }
        try (PDDocument unchangedOriginal = PDDocument.load(original)) {
            assertEquals(1, unchangedOriginal.getNumberOfPages());
        }
    }
}
