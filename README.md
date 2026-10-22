# pdf4umvc

Pdf4Um is a Java Swing desktop application for working with PDF files. Its code
is organized using an MVC structure:

- `view`: the Swing interface in `com.mycompany.pdf4um.Main`
- `controller`: user-action coordination in `Pdf4UmController`
- `model`: PDF, file, and encryption operations in `Pdf4UmModel` and its helpers

## Build

Requires Java 11 or later and Maven.

```sh
mvn test
mvn package
```

The application entry point is `com.mycompany.pdf4um.Main`.
