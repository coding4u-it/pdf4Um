package com.mycompany.pdf4um.web;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.net.http.HttpResponse;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.junit.Test;

public class SplitMergeWorkflowTest extends WebWorkflowTestSupport {

    @Test
    public void splitAndMergeKeepPageContentAndRequestedOrder() throws Exception {
        byte[] firstInput = createPdf("FIRST DOCUMENT");
        byte[] secondInput = createPdf("SECOND DOCUMENT");

        HttpResponse<byte[]> split = post("/api/split", fields("pagesPerPart", "1"),
                file("file", "first.pdf", createPdf("PAGE ONE", "PAGE TWO")));
        assertEquals(200, split.statusCode());
        Map<String, byte[]> parts = zipEntries(split.body());
        assertTrue(parts.containsKey("first_0001.pdf"));
        assertTrue(parts.containsKey("first_0002.pdf"));
        try (PDDocument firstPart = PDDocument.load(parts.get("first_0001.pdf"));
                PDDocument secondPart = PDDocument.load(parts.get("first_0002.pdf"))) {
            assertEquals(1, firstPart.getNumberOfPages());
            assertEquals("PAGE ONE", new PDFTextStripper().getText(firstPart).trim());
            assertEquals("PAGE TWO", new PDFTextStripper().getText(secondPart).trim());
        }

        HttpResponse<byte[]> merged = post("/api/merge", fields(),
                file("files", "first.pdf", firstInput),
                file("files", "second.pdf", secondInput));
        assertEquals(200, merged.statusCode());
        assertTrue(merged.headers().firstValue("Content-Disposition").orElse("")
                .contains("first_merged.pdf"));
        try (PDDocument document = PDDocument.load(new ByteArrayInputStream(merged.body()))) {
            assertEquals(2, document.getNumberOfPages());
            String mergedText = new PDFTextStripper().getText(document);
            assertTrue(mergedText.indexOf("FIRST DOCUMENT")
                    < mergedText.indexOf("SECOND DOCUMENT"));
        }
    }
}
