package com.mycompany.pdf4um.web;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

public class Pdf4UmWebServerTest {
    private static final String BOUNDARY = "pdf4um-test-boundary";

    private Pdf4UmWebServer server;
    private HttpClient client;
    private byte[] twoPagePdf;
    private byte[] onePagePdf;

    @Before
    public void startServer() throws Exception {
        server = new Pdf4UmWebServer(0);
        server.start();
        client = HttpClient.newHttpClient();
        twoPagePdf = createPdf("first page text", "second page text");
        onePagePdf = createPdf("third page text");
    }

    @After
    public void stopServer() {
        if (server != null) {
            server.close();
        }
    }

    @Test
    public void bindsToLoopbackAndSupportsAllPdfWorkflows() throws Exception {
        assertTrue(server.getAddress().isLoopbackAddress());
        assertEquals("127.0.0.1", server.getAddress().getHostAddress());

        HttpResponse<byte[]> split = post("/api/split",
                fields("pagesPerPart", "1"),
                files("file", "Report.pdf", twoPagePdf));
        assertEquals(200, split.statusCode());
        assertEquals("application/zip", split.headers().firstValue("Content-Type").orElse(""));
        List<String> splitNames = zipEntries(split.body()).names;
        assertEquals(2, splitNames.size());
        assertTrue(splitNames.contains("Report_0001.pdf"));
        assertTrue(splitNames.contains("Report_0002.pdf"));

        HttpResponse<byte[]> splitWithPdfInStem = post("/api/split", fields(),
                files("file", "Report.pdf.review.pdf", onePagePdf));
        assertEquals(200, splitWithPdfInStem.statusCode());
        assertTrue(zipEntries(splitWithPdfInStem.body()).names
                .contains("Report.pdf.review_0001.pdf"));

        HttpResponse<byte[]> merged = post("/api/merge", fields(),
                files("files", "Report.pdf", twoPagePdf),
                files("files", "Appendix.pdf", onePagePdf));
        assertEquals(200, merged.statusCode());
        try (PDDocument document = PDDocument.load(merged.body())) {
            assertEquals(3, document.getNumberOfPages());
        }
        assertTrue(merged.headers().firstValue("Content-Disposition").orElse("")
                .contains("Report_merged.pdf"));

        HttpResponse<byte[]> renamed = post("/api/rename",
                fields("mode", "sequential", "prefix", "Chapter-", "startingNumber", "4"),
                files("files", "Report.pdf", twoPagePdf),
                files("files", "Appendix.pdf", onePagePdf));
        assertEquals(200, renamed.statusCode());
        List<String> renameNames = zipEntries(renamed.body()).names;
        assertTrue(renameNames.contains("Chapter-4.pdf"));
        assertTrue(renameNames.contains("Chapter-5.pdf"));

        HttpResponse<byte[]> randomRenamed = post("/api/rename",
                fields("mode", "random", "codeLength", "8", "useSymbols", "false"),
                files("files", "Report.pdf", twoPagePdf));
        assertEquals(200, randomRenamed.statusCode());
        ZipContents randomZip = zipEntries(randomRenamed.body());
        assertTrue(randomZip.names.contains("esporta.csv"));
        assertTrue(randomZip.text("esporta.csv").matches("(?s)\\.pdf;[0-9]{8}\\R"));

        HttpResponse<byte[]> encrypted = post("/api/encrypt",
                fields("password", "test-secret", "allowOpen", "false", "allowPrint", "false",
                        "allowCopy", "false", "allowModify", "false", "allowAssembly", "false"),
                files("files", "Report.pdf", twoPagePdf));
        assertEquals(200, encrypted.statusCode());
        byte[] protectedPdf = zipEntries(encrypted.body()).firstPdf();
        try (PDDocument document = PDDocument.load(protectedPdf, "test-secret")) {
            assertTrue(document.isEncrypted());
            assertEquals(2, document.getNumberOfPages());
        }

        HttpResponse<byte[]> extracted = post("/api/extract-text", fields(),
                files("file", "Report.pdf", twoPagePdf));
        assertEquals(200, extracted.statusCode());
        assertEquals("text/plain; charset=utf-8",
                extracted.headers().firstValue("Content-Type").orElse(""));
        String extractedText = new String(extracted.body(), StandardCharsets.UTF_8);
        assertTrue(extractedText.contains("first page text"));
        assertTrue(extractedText.contains("second page text"));
    }

    @Test
    public void rejectsInvalidInputsWithContractStatuses() throws Exception {
        HttpResponse<byte[]> tooFewForMerge = post("/api/merge", fields(),
                files("files", "Report.pdf", onePagePdf));
        assertEquals(400, tooFewForMerge.statusCode());

        HttpResponse<byte[]> unsupported = post("/api/split", fields(),
                files("file", "picture.png", new byte[] {1, 2, 3}));
        assertEquals(415, unsupported.statusCode());

        HttpResponse<byte[]> unreadable = post("/api/extract-text", fields(),
                files("file", "broken.pdf", "not a PDF".getBytes(StandardCharsets.UTF_8)));
        assertEquals(422, unreadable.statusCode());

        HttpRequest unknownRoute = HttpRequest.newBuilder(uri("/api/unknown"))
                .GET().build();
        assertEquals(404, client.send(unknownRoute, HttpResponse.BodyHandlers.ofByteArray())
                .statusCode());
    }

    private HttpResponse<byte[]> post(String path, List<FormField> fields, FilePart... files)
            throws Exception {
        ByteArrayOutputStream body = new ByteArrayOutputStream();
        for (FormField field : fields) {
            write(body, "--" + BOUNDARY + "\r\n"
                    + "Content-Disposition: form-data; name=\"" + field.name + "\"\r\n\r\n"
                    + field.value + "\r\n");
        }
        for (FilePart file : files) {
            write(body, "--" + BOUNDARY + "\r\n"
                    + "Content-Disposition: form-data; name=\"" + file.field + "\"; filename=\""
                    + file.filename + "\"\r\n"
                    + "Content-Type: application/pdf\r\n\r\n");
            body.write(file.contents);
            write(body, "\r\n");
        }
        write(body, "--" + BOUNDARY + "--\r\n");

        HttpRequest request = HttpRequest.newBuilder(uri(path))
                .header("Content-Type", "multipart/form-data; boundary=" + BOUNDARY)
                .POST(HttpRequest.BodyPublishers.ofByteArray(body.toByteArray()))
                .build();
        return client.send(request, HttpResponse.BodyHandlers.ofByteArray());
    }

    private URI uri(String path) {
        return URI.create("http://127.0.0.1:" + server.getPort() + path);
    }

    private static byte[] createPdf(String... pageTexts) throws IOException {
        try (PDDocument document = new PDDocument();
                ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            for (String text : pageTexts) {
                PDPage page = new PDPage();
                document.addPage(page);
                try (PDPageContentStream content = new PDPageContentStream(document, page)) {
                    content.beginText();
                    content.setFont(PDType1Font.HELVETICA, 12);
                    content.newLineAtOffset(50, 700);
                    content.showText(text);
                    content.endText();
                }
            }
            document.save(output);
            return output.toByteArray();
        }
    }

    private static List<FormField> fields(String... values) {
        List<FormField> result = new ArrayList<>();
        for (int i = 0; i + 1 < values.length; i += 2) {
            result.add(new FormField(values[i], values[i + 1]));
        }
        return result;
    }

    private static FilePart files(String field, String filename, byte[] contents) {
        return new FilePart(field, filename, contents);
    }

    private static void write(ByteArrayOutputStream output, String value) throws IOException {
        output.write(value.getBytes(StandardCharsets.UTF_8));
    }

    private static ZipContents zipEntries(byte[] content) throws IOException {
        List<String> names = new ArrayList<>();
        java.util.Map<String, byte[]> entries = new java.util.LinkedHashMap<>();
        try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(content),
                StandardCharsets.UTF_8)) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                names.add(entry.getName());
                entries.put(entry.getName(), zip.readAllBytes());
            }
        }
        return new ZipContents(names, entries);
    }

    private static final class FormField {
        final String name;
        final String value;

        FormField(String name, String value) {
            this.name = name;
            this.value = value;
        }
    }

    private static final class FilePart {
        final String field;
        final String filename;
        final byte[] contents;

        FilePart(String field, String filename, byte[] contents) {
            this.field = field;
            this.filename = filename;
            this.contents = contents;
        }
    }

    private static final class ZipContents {
        final List<String> names;
        final java.util.Map<String, byte[]> entries;

        ZipContents(List<String> names, java.util.Map<String, byte[]> entries) {
            this.names = names;
            this.entries = entries;
        }

        String text(String name) {
            return new String(entries.get(name), StandardCharsets.UTF_8);
        }

        byte[] firstPdf() {
            for (String name : names) {
                if (name.toLowerCase(java.util.Locale.ROOT).endsWith(".pdf")) {
                    return entries.get(name);
                }
            }
            assertFalse("ZIP contains an encrypted PDF", true);
            return new byte[0];
        }
    }
}
