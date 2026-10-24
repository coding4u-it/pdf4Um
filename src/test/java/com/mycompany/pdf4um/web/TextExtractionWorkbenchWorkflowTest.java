package com.mycompany.pdf4um.web;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.net.http.HttpResponse;
import org.junit.Test;

public class TextExtractionWorkbenchWorkflowTest extends WebWorkflowTestSupport {

    @Test
    public void workbenchResourcesAndTextDownloadAreAvailableFromSameOrigin()
            throws Exception {
        HttpResponse<byte[]> page = get("/");
        assertEquals(200, page.statusCode());
        String html = responseText(page);
        assertTrue(html.contains("Disponibile solo su questo computer"));
        assertTrue(html.contains("Estrai testo"));
        assertTrue(html.contains("Proteggi"));

        assertEquals(200, get("/app.js").statusCode());
        assertEquals(200, get("/styles.css").statusCode());

        HttpResponse<byte[]> extracted = post("/api/extract-text", fields(),
                file("file", "notes.pdf", createPdf("WORKFLOW EXTRACTED TEXT")));
        assertEquals(200, extracted.statusCode());
        assertEquals("text/plain; charset=utf-8",
                extracted.headers().firstValue("Content-Type").orElse(""));
        assertTrue(extracted.headers().firstValue("Content-Disposition").orElse("")
                .contains("notes_text.txt"));
        assertTrue(responseText(extracted).contains("WORKFLOW EXTRACTED TEXT"));
    }
}
