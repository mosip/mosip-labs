package io.mosip.testrig.roottrace;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;

/** Zero-dependency client for the roottrace HTTP API. Base URL from -DrootTraceUrl or ROOTTRACE_URL. */
public final class RootTraceClient {
    private final String baseUrl;
    // Sent as Authorization: Bearer when ROOTTRACE_API_TOKEN or -DrootTraceToken is set.
    private final String token = first(
            System.getProperty("rootTraceToken"), System.getenv("ROOTTRACE_API_TOKEN"));
    // Short connect timeout: a missing roottrace must not stall the test thread for long.
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();

    public RootTraceClient(String baseUrl) {
        this.baseUrl = baseUrl.replaceAll("/+$", "");   // callers may or may not include the trailing slash
    }

    /** null when neither the system property nor the env var is set, so the listener can no-op. */
    public static RootTraceClient fromEnv() {
        String url = System.getProperty("rootTraceUrl", System.getenv("ROOTTRACE_URL"));
        return (url == null || url.isBlank()) ? null : new RootTraceClient(url);
    }

    /** Full health scan of a time window (e.g. the test run). Returns raw JSON. */
    public String scan(Instant from, Instant to, String namespacesCsv) throws Exception {
        // Instant.toString() is ISO-8601, which engine.ts_ns accepts. Namespaces are optional.
        String q = "from=" + from + "&to=" + to + (namespacesCsv == null ? "" : "&namespace=" + enc(namespacesCsv));
        return get("/scan?" + q, Duration.ofMinutes(10));   // a cluster scan can take a few minutes
    }

    /** Every backend log line for a transaction/trace id, across services, in time order. */
    public String trace(String id, Instant from, Instant to) throws Exception {
        return get("/trace/" + enc(id) + "?from=" + from + "&to=" + to, Duration.ofMinutes(2));
    }

    public String reportUrl() { return baseUrl + "/report"; }

    private String get(String path, Duration timeout) throws Exception {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(baseUrl + path)).timeout(timeout).GET();
        if (token != null && !token.isBlank()) b.header("Authorization", "Bearer " + token);
        HttpRequest req = b.build();
        HttpResponse<String> r = http.send(req, HttpResponse.BodyHandlers.ofString());
        // 4xx is a bad window or unknown path; 5xx is roottrace itself. Either way the caller logs and continues.
        if (r.statusCode() >= 400) throw new IllegalStateException("roottrace " + r.statusCode() + ": " + r.body());
        return r.body();
    }

    /**
     * Pull one string field out of a JSON object without a JSON library.
     * Nested objects are not walked; the first "name": "value" pair in the text wins,
     * which is what we want for verdict (top level) and for the first_error's service/message.
     */
    public static String field(String json, String name) {
        var m = java.util.regex.Pattern.compile("\"" + name + "\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"").matcher(json);
        return m.find() ? m.group(1) : null;
    }

    private static String enc(String s) { return URLEncoder.encode(s, StandardCharsets.UTF_8); }

    private static String first(String a, String b) {
        if (a != null && !a.isBlank()) return a;
        return (b == null || b.isBlank()) ? null : b;
    }
}
