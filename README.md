# pdf4umvc

Pdf4Um is a localhost-only Java web application for working with PDF files.
The Java/PDFBox processing code runs in a local HTTP server, and the workbench
is opened in a browser at `http://127.0.0.1:8080`.

The server binds only to `127.0.0.1`; it is not exposed to other computers on
the network. Selected files are uploaded to the local process, processed in a
temporary workspace, and returned as downloads. The application does not
modify the selected originals. Each request is limited to 100 MiB and
multi-file operations accept up to 32 PDFs.

## Build

Requires Java 11 or later and Maven.

```sh
mvn test
mvn package
java -jar target/Pdf4Um-1.0-SNAPSHOT-jar-with-dependencies.jar
```

Then open `http://127.0.0.1:8080` in a browser. Stop the server with
`Ctrl+C`. To use another local port, pass a system property, for example:

```sh
java -Dpdf4um.port=8090 -jar target/Pdf4Um-1.0-SNAPSHOT-jar-with-dependencies.jar
```

Changing the port does not change the loopback-only binding. The application
entry point remains `com.mycompany.pdf4um.Main` for existing Java launch
configurations.
