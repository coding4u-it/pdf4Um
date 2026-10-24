package com.mycompany.pdf4um.web;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.junit.After;
import org.junit.Before;

abstract class WebWorkflowTestSupport {
    private static final String BOUNDARY = "pdf4um-workflow-test-boundary";

    protected Pdf4UmWebServer server;
    protected HttpClient client;

    @Before
    public void startWorkflowServer() throws Exception {
        server = new Pdf4UmWebServer(0);
        server.start();
        client = HttpClient.newHttpClient();
    }

    @After
    public void stopWorkflowServer() {
        if (server != null) {
            server.close();
        }
    }

    protected HttpResponse<byte[]> get(String path) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(uri(path)).GET().build();
        return client.send(request, HttpResponse.BodyHandlers.ofByteArray());
    }

    protected HttpResponse<byte[]> post(String path, List<FormField> fields, FilePart... files)
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

    protected URI uri(String path) {
        return URI.create("http://127.0.0.1:" + server.getPort() + path);
    }

    protected static byte[] createPdf(String... pageTexts) throws IOException {
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

    protected static List<FormField> fields(String... values) {
        if (values.length % 2 != 0) {
            throw new IllegalArgumentException("Fields must be supplied as name/value pairs.");
        }
        List<FormField> result = new ArrayList<>();
        for (int i = 0; i < values.length; i += 2) {
            result.add(new FormField(values[i], values[i + 1]));
        }
        return result;
    }

    protected static FilePart file(String field, String filename, byte[] contents) {
        return new FilePart(field, filename, contents);
    }

    protected static Map<String, byte[]> zipEntries(byte[] content) throws IOException {
        Map<String, byte[]> result = new LinkedHashMap<>();
        try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(content))) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                ByteArrayOutputStream output = new ByteArrayOutputStream();
                zip.transferTo(output);
                result.put(entry.getName(), output.toByteArray());
            }
        }
        return result;
    }

    protected static String responseText(HttpResponse<byte[]> response) {
        return new String(response.body(), StandardCharsets.UTF_8);
    }

    private static void write(ByteArrayOutputStream output, String value) throws IOException {
        output.write(value.getBytes(StandardCharsets.UTF_8));
    }

    protected static final class FormField {
        private final String name;
        private final String value;

        private FormField(String name, String value) {
            this.name = name;
            this.value = value;
        }
    }

    protected static final class FilePart {
        private final String field;
        private final String filename;
        private final byte[] contents;

        private FilePart(String field, String filename, byte[] contents) {
            this.field = field;
            this.filename = filename;
            this.contents = contents;
        }
    }
}
