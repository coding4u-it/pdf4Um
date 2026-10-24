package com.mycompany.pdf4um;

import com.mycompany.pdf4um.web.Pdf4UmWebServer;
import java.io.IOException;

/**
 * Application entrypoint retained for existing Maven, NetBeans, and VS Code run actions.
 */
public final class Main {
    private Main() {
    }

    public static void main(String[] args) throws IOException {
        int port = Integer.getInteger("pdf4um.port", Pdf4UmWebServer.DEFAULT_PORT);
        Pdf4UmWebServer server = new Pdf4UmWebServer(port);
        Runtime.getRuntime().addShutdownHook(new Thread(server::close, "pdf4um-shutdown"));
        server.start();
        System.out.println("PDF4Um is listening on http://127.0.0.1:" + server.getPort());
    }
}
