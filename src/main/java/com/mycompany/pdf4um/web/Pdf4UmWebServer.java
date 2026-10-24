package com.mycompany.pdf4um.web;

import com.mycompany.pdf4um.controller.Pdf4UmController;
import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Stream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.apache.pdfbox.pdmodel.PDDocument;

/**
 * Same-origin HTTP boundary for the PDF workbench. The listener is always bound to IPv4 loopback.
 */
public final class Pdf4UmWebServer implements AutoCloseable {
    public static final int DEFAULT_PORT = 8080;
    private static final int MAX_REQUEST_BYTES = 100 * 1024 * 1024;
    private static final Logger LOGGER = Logger.getLogger(Pdf4UmWebServer.class.getName());
    private static final String[] STATIC_FILES = {"index.html", "app.js", "styles.css"};

    private final HttpServer server;
    private final ExecutorService executor;

    public Pdf4UmWebServer(int port) throws IOException {
        if (port < 0 || port > 65535) {
            throw new IllegalArgumentException("Port must be between 0 and 65535.");
        }
        InetAddress loopback = InetAddress.getByName("127.0.0.1");
        server = HttpServer.create(new InetSocketAddress(loopback, port), 0);
        executor = Executors.newFixedThreadPool(Math.max(2,
                Math.min(8, Runtime.getRuntime().availableProcessors())));
        server.setExecutor(executor);
        server.createContext("/", this::handle);
    }

    public void start() {
        server.start();
    }

    public int getPort() {
        return server.getAddress().getPort();
    }

    public InetAddress getAddress() {
        return server.getAddress().getAddress();
    }

    @Override
    public void close() {
        server.stop(0);
        executor.shutdownNow();
    }

    private void handle(HttpExchange exchange) throws IOException {
        exchange.getResponseHeaders().set("X-Content-Type-Options", "nosniff");
        exchange.getResponseHeaders().set("Referrer-Policy", "no-referrer");
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        try {
            String path = exchange.getRequestURI().getPath();
            if (path.startsWith("/api/")) {
                handleApi(exchange, path);
            } else {
                handleStatic(exchange, path);
            }
        } catch (HttpProblem problem) {
            sendJsonError(exchange, problem.status, problem.getMessage());
        } catch (MultipartFormData.PayloadTooLargeException exception) {
            sendJsonError(exchange, 413, "The upload exceeds the 100 MB request limit.");
        } catch (IllegalArgumentException exception) {
            sendJsonError(exchange, 400, exception.getMessage());
        } catch (IOException exception) {
            if (exchange.getResponseCode() < 0) {
                LOGGER.log(Level.WARNING, "PDF workbench request failed.", exception);
                sendJsonError(exchange, 500, "The operation could not be completed.");
            } else {
                LOGGER.log(Level.FINE, "Client disconnected during response.", exception);
            }
        } catch (RuntimeException exception) {
            LOGGER.log(Level.WARNING, "Unexpected PDF workbench request failure.", exception);
            if (exchange.getResponseCode() < 0) {
                sendJsonError(exchange, 500, "The operation could not be completed.");
            }
        } finally {
            exchange.close();
        }
    }

    private void handleStatic(HttpExchange exchange, String path) throws IOException, HttpProblem {
        if (!"GET".equals(exchange.getRequestMethod())) {
            throw new HttpProblem(405, "Method not allowed.");
        }
        String resourceName;
        if ("/".equals(path)) {
            resourceName = "index.html";
        } else if ("/app.js".equals(path)) {
            resourceName = "app.js";
        } else if ("/styles.css".equals(path)) {
            resourceName = "styles.css";
        } else {
            throw new HttpProblem(404, "Not found.");
        }
        if (!contains(STATIC_FILES, resourceName)) {
            throw new HttpProblem(404, "Not found.");
        }
        try (InputStream resource = getClass().getClassLoader()
                .getResourceAsStream("web/" + resourceName)) {
            if (resource == null) {
                throw new HttpProblem(503, "The browser workbench has not been packaged.");
            }
            byte[] bytes = resource.readAllBytes();
            String contentType = resourceName.endsWith(".html") ? "text/html; charset=utf-8"
                    : resourceName.endsWith(".js") ? "text/javascript; charset=utf-8"
                    : "text/css; charset=utf-8";
            exchange.getResponseHeaders().set("Content-Type", contentType);
            exchange.sendResponseHeaders(200, bytes.length);
            exchange.getResponseBody().write(bytes);
        }
    }

    private void handleApi(HttpExchange exchange, String path) throws IOException, HttpProblem {
        if (!("/api/split".equals(path) || "/api/merge".equals(path)
                || "/api/rename".equals(path) || "/api/encrypt".equals(path)
                || "/api/extract-text".equals(path))) {
            throw new HttpProblem(404, "Not found.");
        }
        if (!"POST".equals(exchange.getRequestMethod())) {
            throw new HttpProblem(405, "Method not allowed.");
        }

        long contentLength = parseContentLength(exchange);
        MultipartFormData form = MultipartFormData.parse(exchange.getRequestBody(),
                exchange.getRequestHeaders().getFirst("Content-Type"), contentLength,
                MAX_REQUEST_BYTES);
        Path workspace = Files.createTempDirectory("pdf4um-request-");
        try {
            Path inputDirectory = Files.createDirectory(workspace.resolve("input"));
            if ("/api/split".equals(path)) {
                split(exchange, form, inputDirectory);
            } else if ("/api/merge".equals(path)) {
                merge(exchange, form, inputDirectory);
            } else if ("/api/rename".equals(path)) {
                rename(exchange, form, inputDirectory);
            } else if ("/api/encrypt".equals(path)) {
                encrypt(exchange, form, inputDirectory);
            } else {
                extractText(exchange, form, inputDirectory);
            }
        } finally {
            deleteWorkspace(workspace);
        }
    }

    private void split(HttpExchange exchange, MultipartFormData form, Path workDirectory)
            throws IOException, HttpProblem {
        FileSet upload = saveFiles(form, "file", 1, 1, workDirectory);
        int pagesPerPart = integer(form.text("pagesPerPart", "1"), "pagesPerPart");
        if (pagesPerPart < 1) {
            throw new HttpProblem(400, "Pages per part must be greater than zero.");
        }
        validatePdfs(upload.files);
        new Pdf4UmController().split(upload.files, pagesPerPart != 1,
                Integer.toString(pagesPerPart));

        String stem = stem(upload.files[0].getName());
        List<Path> outputs = new ArrayList<>();
        try (Stream<Path> files = Files.list(workDirectory)) {
            files.filter(Files::isRegularFile)
                    .filter(path -> path.getFileName().toString().startsWith(stem + "_"))
                    .filter(path -> path.getFileName().toString().toLowerCase(Locale.ROOT)
                            .endsWith(".pdf"))
                    .forEach(outputs::add);
        }
        outputs.sort((left, right) -> left.getFileName().toString()
                .compareTo(right.getFileName().toString()));
        if (outputs.isEmpty()) {
            throw new IOException("No split documents were generated.");
        }
        sendZip(exchange, outputs, "split-pdfs.zip");
    }

    private void merge(HttpExchange exchange, MultipartFormData form, Path workDirectory)
            throws IOException, HttpProblem {
        FileSet upload = saveFiles(form, "files", 2, 32, workDirectory);
        validatePdfs(upload.files);
        new Pdf4UmController().merge(upload.files);
        Path output = workDirectory.resolve(stem(upload.files[0].getName()) + "_merged.pdf");
        sendFile(exchange, output, "application/pdf", output.getFileName().toString());
    }

    private void rename(HttpExchange exchange, MultipartFormData form, Path workDirectory)
            throws IOException, HttpProblem {
        FileSet upload = saveFiles(form, "files", 1, 32, workDirectory);
        String mode = form.text("mode", "");
        if (!"sequential".equals(mode) && !"random".equals(mode)) {
            throw new HttpProblem(400, "Rename mode must be sequential or random.");
        }
        boolean sequential = "sequential".equals(mode);
        String prefix = safePrefix(form.text("prefix", ""));
        int startingNumber = integer(form.text("startingNumber", "0"), "startingNumber");
        int codeLength = integer(form.text("codeLength", "8"), "codeLength");
        boolean useSymbols = booleanValue(form, "useSymbols", false);
        if (startingNumber < 0 || startingNumber > 9) {
            throw new HttpProblem(400, "Starting number must be between 0 and 9.");
        }
        if (codeLength < 4 || codeLength > 20) {
            throw new HttpProblem(400, "Random code length must be between 4 and 20.");
        }
        validatePdfs(upload.files);
        Path outputDirectory = Files.createDirectory(workDirectory.resolve("renamed"));
        List<File> outputFiles = new Pdf4UmController().renameCopies(upload.files, outputDirectory,
                sequential, prefix, startingNumber, codeLength, useSymbols);
        sendZip(exchange, toPaths(outputFiles), "renamed-pdfs.zip");
    }

    private void encrypt(HttpExchange exchange, MultipartFormData form, Path workDirectory)
            throws IOException, HttpProblem {
        FileSet upload = saveFiles(form, "files", 1, 32, workDirectory);
        String password = form.text("password", "");
        if (password.isEmpty()) {
            throw new HttpProblem(400, "Password is required.");
        }
        boolean allowOpen = booleanValue(form, "allowOpen", false);
        boolean allowPrint = booleanValue(form, "allowPrint", false);
        boolean allowCopy = booleanValue(form, "allowCopy", false);
        boolean allowModify = booleanValue(form, "allowModify", false);
        boolean allowAssembly = booleanValue(form, "allowAssembly", false);
        validatePdfs(upload.files);
        new Pdf4UmController().encrypt(upload.files, password, allowOpen, allowPrint, allowCopy,
                allowModify, allowAssembly);

        List<Path> outputs = new ArrayList<>();
        for (File file : upload.files) {
            outputs.add(workDirectory.resolve(stem(file.getName()) + "_cript.pdf"));
        }
        sendZip(exchange, outputs, "encrypted-pdfs.zip");
    }

    private void extractText(HttpExchange exchange, MultipartFormData form, Path workDirectory)
            throws IOException, HttpProblem {
        FileSet upload = saveFiles(form, "file", 1, 1, workDirectory);
        validatePdfs(upload.files);
        String extracted = new Pdf4UmController().extractText(upload.files);
        Path output = workDirectory.resolve(stem(upload.files[0].getName()) + "_text.txt");
        Files.writeString(output, extracted, StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW);
        sendFile(exchange, output, "text/plain; charset=utf-8", output.getFileName().toString());
    }

    private FileSet saveFiles(MultipartFormData form, String fieldName, int minimum, int maximum,
            Path workDirectory) throws IOException, HttpProblem {
        List<MultipartFormData.Part> parts = form.get(fieldName);
        if (parts.size() < minimum || parts.size() > maximum) {
            String message = minimum == 2 ? "Select at least two PDF files."
                    : minimum == 1 && maximum == 1 ? "Select exactly one PDF file."
                    : "Select at least one PDF file.";
            throw new HttpProblem(400, message);
        }
        Set<String> names = new HashSet<>();
        File[] files = new File[parts.size()];
        for (int i = 0; i < parts.size(); i++) {
            MultipartFormData.Part part = parts.get(i);
            if (!part.isFile() || part.filename == null || part.filename.trim().isEmpty()) {
                throw new HttpProblem(400, "A PDF file is required.");
            }
            String filename = safePdfFilename(part.filename, i + 1, names);
            Path destination = workDirectory.resolve(filename);
            Files.write(destination, part.data, StandardOpenOption.CREATE_NEW);
            files[i] = destination.toFile();
        }
        return new FileSet(files);
    }

    private static String safePdfFilename(String suppliedName, int index, Set<String> usedNames)
            throws HttpProblem {
        String leaf = suppliedName.replace('\\', '/');
        leaf = leaf.substring(leaf.lastIndexOf('/') + 1);
        leaf = leaf.replaceAll("[\\p{Cntrl}]", "").trim();
        if (!leaf.toLowerCase(Locale.ROOT).endsWith(".pdf")) {
            throw new HttpProblem(415, "Only PDF files are supported.");
        }
        String base = leaf.substring(0, leaf.length() - 4)
                .replaceAll("[<>:\"/\\\\|?*]", "_").trim();
        if (base.isEmpty() || ".".equals(base) || "..".equals(base)) {
            base = "upload-" + index;
        }
        String filename = base + ".pdf";
        int duplicate = 2;
        while (!usedNames.add(filename.toLowerCase(Locale.ROOT))) {
            filename = base + " (" + duplicate++ + ").pdf";
        }
        return filename;
    }

    private static void validatePdfs(File[] files) throws HttpProblem {
        for (File file : files) {
            try (PDDocument ignored = PDDocument.load(file)) {
                // Parsing the document here lets malformed/encrypted input map to HTTP 422.
            } catch (IOException exception) {
                throw new HttpProblem(422, "One or more PDFs are unreadable or password protected.");
            }
        }
    }

    private static void sendFile(HttpExchange exchange, Path file, String contentType,
            String downloadName) throws IOException {
        if (!Files.isRegularFile(file)) {
            throw new IOException("Expected output file was not created.");
        }
        long size = Files.size(file);
        Headers headers = exchange.getResponseHeaders();
        headers.set("Content-Type", contentType);
        headers.set("Content-Disposition", attachmentHeader(downloadName));
        exchange.sendResponseHeaders(200, size);
        try (OutputStream output = exchange.getResponseBody()) {
            Files.copy(file, output);
        }
    }

    private static void sendZip(HttpExchange exchange, List<Path> files, String downloadName)
            throws IOException {
        if (files.isEmpty()) {
            throw new IOException("No output files were created.");
        }
        for (Path file : files) {
            if (!Files.isRegularFile(file)) {
                throw new IOException("Expected output file was not created.");
            }
        }
        Headers headers = exchange.getResponseHeaders();
        headers.set("Content-Type", "application/zip");
        headers.set("Content-Disposition", attachmentHeader(downloadName));
        exchange.sendResponseHeaders(200, 0);
        try (ZipOutputStream zip = new ZipOutputStream(exchange.getResponseBody(),
                StandardCharsets.UTF_8)) {
            for (Path file : files) {
                zip.putNextEntry(new ZipEntry(file.getFileName().toString()));
                Files.copy(file, zip);
                zip.closeEntry();
            }
        }
    }

    private static String attachmentHeader(String filename) {
        String asciiName = filename.replaceAll("[^\\x20-\\x7E]", "_")
                .replace("\\", "_").replace("\"", "_");
        String encoded = URLEncoder.encode(filename, StandardCharsets.UTF_8).replace("+", "%20");
        return "attachment; filename=\"" + asciiName + "\"; filename*=UTF-8''" + encoded;
    }

    private static void sendJsonError(HttpExchange exchange, int status, String message)
            throws IOException {
        if (exchange.getResponseCode() >= 0) {
            return;
        }
        String json = "{\"error\":\"" + jsonEscape(message == null ? "Request failed." : message)
                + "\"}";
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
    }

    private static String jsonEscape(String value) {
        StringBuilder escaped = new StringBuilder();
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            switch (ch) {
                case '"':
                    escaped.append("\\\"");
                    break;
                case '\\':
                    escaped.append("\\\\");
                    break;
                case '\n':
                    escaped.append("\\n");
                    break;
                case '\r':
                    escaped.append("\\r");
                    break;
                case '\t':
                    escaped.append("\\t");
                    break;
                default:
                    if (ch < 0x20) {
                        escaped.append(String.format("\\u%04x", (int) ch));
                    } else {
                        escaped.append(ch);
                    }
            }
        }
        return escaped.toString();
    }

    private static long parseContentLength(HttpExchange exchange) throws HttpProblem {
        String value = exchange.getRequestHeaders().getFirst("Content-Length");
        if (value == null) {
            return -1;
        }
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException exception) {
            throw new HttpProblem(400, "Invalid Content-Length.");
        }
    }

    private static int integer(String value, String field) throws HttpProblem {
        try {
            return Integer.parseInt(value.trim());
        } catch (NumberFormatException exception) {
            throw new HttpProblem(400, "Invalid " + field + " value.");
        }
    }

    private static boolean booleanValue(MultipartFormData form, String name, boolean defaultValue)
            throws HttpProblem {
        String value = form.text(name, null);
        if (value == null || value.isEmpty()) {
            return defaultValue;
        }
        switch (value.trim().toLowerCase(Locale.ROOT)) {
            case "true":
            case "on":
            case "1":
            case "yes":
                return true;
            case "false":
            case "off":
            case "0":
            case "no":
                return false;
            default:
                throw new HttpProblem(400, "Invalid " + name + " value.");
        }
    }

    private static String safePrefix(String prefix) {
        String safe = prefix.replaceAll("[\\p{Cntrl}]", "")
                .replaceAll("[<>:\"/\\\\|?*]", "_");
        return safe.length() > 100 ? safe.substring(0, 100) : safe;
    }

    private static String stem(String filename) {
        return filename.substring(0, filename.length() - ".pdf".length());
    }

    private static List<Path> toPaths(List<File> files) {
        List<Path> paths = new ArrayList<>();
        for (File file : files) {
            paths.add(file.toPath());
        }
        return paths;
    }

    private static void deleteWorkspace(Path workspace) {
        if (workspace == null || !Files.exists(workspace)) {
            return;
        }
        try (Stream<Path> paths = Files.walk(workspace)) {
            paths.sorted(Collections.reverseOrder()).forEach(path -> {
                try {
                    Files.deleteIfExists(path);
                } catch (IOException exception) {
                    LOGGER.log(Level.FINE, "Unable to remove request workspace.", exception);
                }
            });
        } catch (IOException exception) {
            LOGGER.log(Level.FINE, "Unable to remove request workspace.", exception);
        }
    }

    private static boolean contains(String[] values, String sought) {
        for (String value : values) {
            if (value.equals(sought)) {
                return true;
            }
        }
        return false;
    }

    private static final class FileSet {
        final File[] files;

        FileSet(File[] files) {
            this.files = files;
        }
    }

    private static final class HttpProblem extends Exception {
        private static final long serialVersionUID = 1L;
        final int status;

        HttpProblem(int status, String message) {
            super(message);
            this.status = status;
        }
    }
}
