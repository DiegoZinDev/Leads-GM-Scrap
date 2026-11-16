package br.com.urwork.prospeccao;

import com.fasterxml.jackson.databind.JsonNode;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;
import org.springframework.web.util.UriComponentsBuilder;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.*;

@Service
class Meta {
    enum Rede {
        INSTAGRAM("instagram_basic"), WHATSAPP("whatsapp_business_management");
        final String permissao;
        Rede(String permissao) { this.permissao = permissao; }
    }
    private final Environment env;
    private final com.fasterxml.jackson.databind.ObjectMapper json;
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    Meta(Environment env, com.fasterxml.jackson.databind.ObjectMapper json) { this.env = env; this.json = json; }
    String valor(String nome) { return env.getProperty("URWORK_META_" + nome, "").strip(); }
    boolean configurada(Rede rede) {
        return !valor("APP_ID").isEmpty() && !valor("APP_SECRET").isEmpty()
            && !valor("CALLBACK").isEmpty() && valor("CHAVE").length() >= 32
            && !valor("CONFIG_" + rede).isEmpty() && valor("VERSAO").matches("v[0-9]+[.]0");
    }
    URI autorizar(Rede rede, String state) {
        return UriComponentsBuilder.fromUriString("https://www.facebook.com/" + valor("VERSAO") + "/dialog/oauth")
            .queryParam("client_id",valor("APP_ID")).queryParam("config_id",valor("CONFIG_" + rede))
            .queryParam("response_type","code").queryParam("redirect_uri",valor("CALLBACK"))
            .queryParam("state",state).build().encode().toUri();
    }
    private String form(Map<String,String> campos) {
        return campos.entrySet().stream().map(e -> e.getKey()+"="+java.net.URLEncoder.encode(e.getValue(),java.nio.charset.StandardCharsets.UTF_8))
            .collect(java.util.stream.Collectors.joining("&"));
    }
    String trocar(String code) {
        var corpo = form(Map.of("client_id",valor("APP_ID"),"client_secret",valor("APP_SECRET"),
            "redirect_uri",valor("CALLBACK"),"code",code));
        var req = HttpRequest.newBuilder(graph("oauth/access_token")).header("Content-Type","application/x-www-form-urlencoded")
            .POST(HttpRequest.BodyPublishers.ofString(corpo));
        var token = enviar(req).path("access_token").asText("");
        if (token.isEmpty()) throw new ResponseStatusException(FORBIDDEN);
        return token;
    }
    boolean valida(Rede rede, String token) {
        var req = HttpRequest.newBuilder(graph("debug_token?" + form(Map.of("input_token",token))))
            .header("Authorization","Bearer "+valor("APP_ID")+"|"+valor("APP_SECRET"));
        return permite(enviar(req).path("data"),rede,valor("APP_ID"),Instant.now().getEpochSecond());
    }
    static boolean permite(JsonNode dados, Rede rede, String app, long agora) {
        if (!dados.path("is_valid").asBoolean(false) || !app.equals(dados.path("app_id").asText())) return false;
        for (var campo : java.util.List.of("expires_at","data_access_expires_at")) {
            long fim = dados.path(campo).asLong();
            if (fim != 0 && fim <= agora) return false;
        }
        for (var granular : dados.path("granular_scopes"))
            if (rede.permissao.equals(granular.path("scope").asText()) && granular.has("target_ids")
                    && granular.path("target_ids").isEmpty()) return false;
        for (var escopo : dados.path("scopes")) if (rede.permissao.equals(escopo.asText())) return true;
        return false;
    }
    private URI graph(String rota) { return URI.create("https://graph.facebook.com/"+valor("VERSAO")+"/"+rota); }
    private JsonNode enviar(HttpRequest.Builder req) {
        try {
            var r = http.send(req.timeout(Duration.ofSeconds(8)).build(),HttpResponse.BodyHandlers.ofString());
            if (r.statusCode() != 200) throw new ResponseStatusException(r.statusCode()==400 && req.build().method().equals("POST") ? FORBIDDEN : SERVICE_UNAVAILABLE);
            return json.readTree(r.body());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(SERVICE_UNAVAILABLE);
        } catch (java.io.IOException e) { throw new ResponseStatusException(SERVICE_UNAVAILABLE); }
    }
}
