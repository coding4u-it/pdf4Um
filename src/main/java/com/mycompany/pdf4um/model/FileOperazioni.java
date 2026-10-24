package com.mycompany.pdf4um.model;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;

/**
 * Explicit-path file operations used by the web workflow. Destinations are supplied by the
 * request workspace owner; this class never derives paths from the process working directory.
 */
public class FileOperazioni {

    public File copyTo(File source, Path destination) throws IOException {
        Path target = destination.toAbsolutePath().normalize();
        Path parent = target.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        return Files.copy(source.toPath(), target, StandardCopyOption.COPY_ATTRIBUTES).toFile();
    }

    public void writeText(Path destination, String text) throws IOException {
        Path target = destination.toAbsolutePath().normalize();
        Path parent = target.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        Files.writeString(target, text, StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW,
                StandardOpenOption.WRITE);
    }
}
