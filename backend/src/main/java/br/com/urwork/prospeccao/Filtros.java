package br.com.urwork.prospeccao;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Set;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.BAD_REQUEST;

public record Filtros(boolean instagramVerificado, boolean whatsappLinkPublicado, Integer seguidoresMinimos) {
    static final Filtros NENHUM = new Filtros(false,false,null);
    static Filtros ler(JsonNode node) {
        if (node == null || node.isNull()) return NENHUM;
        if (!node.isObject()) throw new ResponseStatusException(BAD_REQUEST);
        var nomes = Set.of("instagramVerificado","whatsappLinkPublicado","seguidoresMinimos");
        for (var campo : node.properties())
            if (!nomes.contains(campo.getKey()) || (!campo.getKey().equals("seguidoresMinimos") && !campo.getValue().isBoolean()))
                throw new ResponseStatusException(BAD_REQUEST);
        var minimo = node.get("seguidoresMinimos");
        if (minimo != null && !minimo.isNull() && (!minimo.isIntegralNumber() || !minimo.canConvertToInt() || minimo.intValue()<0))
            throw new ResponseStatusException(BAD_REQUEST);
        return new Filtros(node.path("instagramVerificado").asBoolean(),node.path("whatsappLinkPublicado").asBoolean(),
            minimo == null || minimo.isNull() ? null : minimo.intValue());
    }
}
