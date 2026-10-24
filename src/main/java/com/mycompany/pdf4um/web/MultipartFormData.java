package com.mycompany.pdf4um.web;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

final class MultipartFormData {
    private static final int MAX_PARTS = 40;
    private static final int MAX_HEADER_BYTES = 16 * 1024;

    private final Map<String, List<Part>> parts;

    private MultipartFormData(Map<String, List<Part>> parts) {
        this.parts = parts;
    }

    static MultipartFormData parse(InputStream input, String contentType, long contentLength,
            int maxBytes) throws IOException {
        if (contentLength > maxBytes) {
            throw new PayloadTooLargeException();
        }
        String boundary = boundaryFrom(contentType);
        byte[] body = readBounded(input, maxBytes);
        byte[] delimiter = ("--" + boundary).getBytes(StandardCharsets.ISO_8859_1);
        byte[] partDelimiter = ("\r\n--" + boundary).getBytes(StandardCharsets.ISO_8859_1);
        byte[] headerSeparator = "\r\n\r\n".getBytes(StandardCharsets.ISO_8859_1);

        if (!startsWith(body, delimiter, 0)) {
            throw new IllegalArgumentException("Malformed multipart body.");
        }
        int cursor = delimiter.length;
        Map<String, List<Part>> parsed = new LinkedHashMap<>();
        int count = 0;
        while (true) {
            if (startsWith(body, new byte[] {'-', '-'}, cursor)) {
                return new MultipartFormData(parsed);
            }
            if (!startsWith(body, new byte[] {'\r', '\n'}, cursor)) {
                throw new IllegalArgumentException("Malformed multipart boundary.");
            }
            cursor += 2;
            int headerEnd = indexOf(body, headerSeparator, cursor);
            if (headerEnd < 0 || headerEnd - cursor > MAX_HEADER_BYTES) {
                throw new IllegalArgumentException("Malformed multipart headers.");
            }

            Map<String, String> headers = parseHeaders(body, cursor, headerEnd);
            Disposition disposition = parseDisposition(headers.get("content-disposition"));
            int contentStart = headerEnd + headerSeparator.length;
            int contentEnd = findPartEnd(body, partDelimiter, contentStart);
            if (contentEnd < 0) {
                throw new IllegalArgumentException("Multipart boundary is missing.");
            }
            if (++count > MAX_PARTS) {
                throw new IllegalArgumentException("Too many form fields.");
            }

            Part part = new Part(disposition.name, disposition.filename,
                    headers.get("content-type"), Arrays.copyOfRange(body, contentStart, contentEnd));
            parsed.computeIfAbsent(part.name, ignored -> new ArrayList<>()).add(part);
            // The delimiter starts with CRLF; resume at the two hyphens.
            cursor = contentEnd + 2;
            if (!startsWith(body, delimiter, cursor)) {
                throw new IllegalArgumentException("Malformed multipart boundary.");
            }
            cursor += delimiter.length;
            if (startsWith(body, new byte[] {'-', '-'}, cursor)) {
                return new MultipartFormData(parsed);
            }
            if (!startsWith(body, new byte[] {'\r', '\n'}, cursor)) {
                throw new IllegalArgumentException("Malformed multipart boundary.");
            }
        }
    }

    List<Part> get(String name) {
        List<Part> values = parts.get(name);
        return values == null ? new ArrayList<>() : new ArrayList<>(values);
    }

    String text(String name, String defaultValue) {
        List<Part> values = get(name);
        if (values.isEmpty()) {
            return defaultValue;
        }
        if (values.size() != 1 || values.get(0).isFile()) {
            throw new IllegalArgumentException("Invalid field: " + name);
        }
        return new String(values.get(0).data, StandardCharsets.UTF_8);
    }

    private static String boundaryFrom(String contentType) {
        if (contentType == null || !contentType.toLowerCase(Locale.ROOT)
                .startsWith("multipart/form-data")) {
            throw new IllegalArgumentException("Expected multipart/form-data.");
        }
        for (String parameter : splitParameters(contentType)) {
            int equals = parameter.indexOf('=');
            if (equals > 0 && "boundary".equalsIgnoreCase(parameter.substring(0, equals).trim())) {
                String value = unquote(parameter.substring(equals + 1).trim());
                if (!value.isEmpty() && value.length() <= 200
                        && value.chars().allMatch(ch -> ch >= 0x20 && ch <= 0x7e)) {
                    return value;
                }
            }
        }
        throw new IllegalArgumentException("Multipart boundary is missing.");
    }

    private static Map<String, String> parseHeaders(byte[] body, int start, int end) {
        String raw = new String(body, start, end - start, StandardCharsets.ISO_8859_1);
        Map<String, String> headers = new LinkedHashMap<>();
        for (String line : raw.split("\r\n")) {
            int colon = line.indexOf(':');
            if (colon <= 0) {
                throw new IllegalArgumentException("Malformed multipart header.");
            }
            headers.put(line.substring(0, colon).trim().toLowerCase(Locale.ROOT),
                    line.substring(colon + 1).trim());
        }
        return headers;
    }

    private static Disposition parseDisposition(String header) {
        if (header == null) {
            throw new IllegalArgumentException("Multipart content disposition is missing.");
        }
        String name = null;
        String filename = null;
        List<String> parameters = splitParameters(header);
        if (parameters.isEmpty() || !"form-data".equalsIgnoreCase(parameters.get(0).trim())) {
            throw new IllegalArgumentException("Unsupported multipart disposition.");
        }
        for (int i = 1; i < parameters.size(); i++) {
            String parameter = parameters.get(i);
            int equals = parameter.indexOf('=');
            if (equals <= 0) {
                continue;
            }
            String key = parameter.substring(0, equals).trim();
            String value = unquote(parameter.substring(equals + 1).trim());
            if ("name".equalsIgnoreCase(key)) {
                name = value;
            } else if ("filename".equalsIgnoreCase(key)) {
                filename = new String(value.getBytes(StandardCharsets.ISO_8859_1),
                        StandardCharsets.UTF_8);
            }
        }
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("Multipart field name is missing.");
        }
        return new Disposition(name, filename);
    }

    private static List<String> splitParameters(String value) {
        List<String> result = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        boolean escaped = false;
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            if (escaped) {
                current.append(ch);
                escaped = false;
            } else if (ch == '\\' && quoted) {
                escaped = true;
            } else if (ch == '"') {
                quoted = !quoted;
                current.append(ch);
            } else if (ch == ';' && !quoted) {
                result.add(current.toString().trim());
                current.setLength(0);
            } else {
                current.append(ch);
            }
        }
        result.add(current.toString().trim());
        return result;
    }

    private static String unquote(String value) {
        if (value.length() >= 2 && value.charAt(0) == '"' && value.charAt(value.length() - 1) == '"') {
            return value.substring(1, value.length() - 1).replace("\\\"", "\"").replace("\\\\", "\\");
        }
        return value;
    }

    private static int findPartEnd(byte[] body, byte[] delimiter, int from) {
        int position = from;
        while ((position = indexOf(body, delimiter, position)) >= 0) {
            int suffix = position + delimiter.length;
            if (startsWith(body, new byte[] {'-', '-'}, suffix)
                    || startsWith(body, new byte[] {'\r', '\n'}, suffix)) {
                return position;
            }
            position++;
        }
        return -1;
    }

    private static byte[] readBounded(InputStream input, int maxBytes) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int total = 0;
        int count;
        while ((count = input.read(buffer)) != -1) {
            total += count;
            if (total > maxBytes) {
                throw new PayloadTooLargeException();
            }
            output.write(buffer, 0, count);
        }
        return output.toByteArray();
    }

    private static int indexOf(byte[] source, byte[] target, int from) {
        outer:
        for (int i = Math.max(from, 0); i <= source.length - target.length; i++) {
            for (int j = 0; j < target.length; j++) {
                if (source[i + j] != target[j]) {
                    continue outer;
                }
            }
            return i;
        }
        return -1;
    }

    private static boolean startsWith(byte[] source, byte[] target, int offset) {
        if (offset < 0 || offset + target.length > source.length) {
            return false;
        }
        for (int i = 0; i < target.length; i++) {
            if (source[offset + i] != target[i]) {
                return false;
            }
        }
        return true;
    }

    static final class Part {
        final String name;
        final String filename;
        final String contentType;
        final byte[] data;

        private Part(String name, String filename, String contentType, byte[] data) {
            this.name = name;
            this.filename = filename;
            this.contentType = contentType;
            this.data = data;
        }

        boolean isFile() {
            return filename != null;
        }

        String text() {
            return new String(data, StandardCharsets.UTF_8);
        }
    }

    private static final class Disposition {
        final String name;
        final String filename;

        private Disposition(String name, String filename) {
            this.name = name;
            this.filename = filename;
        }
    }

    static final class PayloadTooLargeException extends IOException {
        private static final long serialVersionUID = 1L;

        PayloadTooLargeException() {
            super("Request exceeds the upload limit.");
        }
    }
}
