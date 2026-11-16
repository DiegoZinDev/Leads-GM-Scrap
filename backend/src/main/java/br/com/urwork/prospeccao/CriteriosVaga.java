package br.com.urwork.prospeccao;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.*;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.BAD_REQUEST;

final class CriteriosVaga {
    private static final Map<String,Set<String>> OPCOES = Map.of(
        "modalidade", Set.of("REMOTO","HIBRIDO","PRESENCIAL"),
        "jornada", Set.of("INTEGRAL","PARCIAL"),
        "vinculo", Set.of("CLT","PJ","ESTAGIO","TEMPORARIO"),
        "nivel", Set.of("JUNIOR","PLENO","SENIOR","ESPECIALISTA"),
        "turno", Set.of("MANHA","TARDE","NOITE"),
        "periodo", Set.of("ANO","MES","HORA")
    );

    private static String texto(JsonNode valor, int limite) {
        if (!valor.isTextual()) throw new ResponseStatusException(BAD_REQUEST);
        String s = valor.textValue().strip();
        if (s.isEmpty() || s.length()>limite || s.chars().anyMatch(Character::isISOControl))
            throw new ResponseStatusException(BAD_REQUEST);
        return s;
    }

    static ObjectNode ler(JsonNode valores, ObjectMapper json) {
        var resultado = json.createObjectNode();
        if (valores==null || valores.isNull()) return resultado;
        if (!valores.isObject()) throw new ResponseStatusException(BAD_REQUEST);
        for (var entrada : valores.properties()) {
            String chave = entrada.getKey();
            var v = entrada.getValue();
            switch (chave) {
                case "cargo", "escolaridade" -> resultado.put(chave,texto(v,120));
                case "pais" -> {
                    var pais = texto(v,2);
                    if (!Locale.getISOCountries(Locale.IsoCountryCode.PART1_ALPHA2).contains(pais)) throw new ResponseStatusException(BAD_REQUEST);
                    resultado.put(chave,pais);
                }
                case "moeda" -> {
                    var moeda = texto(v,3);
                    try { Currency.getInstance(moeda); } catch (IllegalArgumentException ex) { throw new ResponseStatusException(BAD_REQUEST); }
                    resultado.put(chave,moeda);
                }
                case "habilidades" -> {
                    if (!v.isArray() || v.size()>20) throw new ResponseStatusException(BAD_REQUEST);
                    var lista = resultado.putArray(chave);
                    var vistos = new TreeSet<String>(String.CASE_INSENSITIVE_ORDER);
                    for (var item : v) {
                        String nome = texto(item,60);
                        if (vistos.add(nome)) lista.add(nome);
                    }
                }
                case "exterior" -> {
                    if (!v.isBoolean()) throw new ResponseStatusException(BAD_REQUEST);
                    resultado.put(chave,v.booleanValue());
                }
                case "experienciaAnos" -> {
                    if (!v.isIntegralNumber() || !v.canConvertToInt() || v.intValue()<0 || v.intValue()>80) throw new ResponseStatusException(BAD_REQUEST);
                    resultado.put(chave,v.intValue());
                }
                case "salarioMin","salarioMax" -> {
                    if (!v.isNumber() || !Double.isFinite(v.doubleValue()) || v.doubleValue()<0 || v.doubleValue()>1_000_000_000
                            || v.decimalValue().stripTrailingZeros().scale()>2) throw new ResponseStatusException(BAD_REQUEST);
                    resultado.put(chave,v.doubleValue());
                }
                default -> {
                    if (!OPCOES.getOrDefault(chave,Set.of()).contains(v.asText())) throw new ResponseStatusException(BAD_REQUEST);
                    resultado.put(chave,v.asText());
                }
            }
        }
        boolean faixa = resultado.has("salarioMin") || resultado.has("salarioMax");
        if (faixa != resultado.has("moeda") || faixa != resultado.has("periodo")
                || resultado.path("salarioMin").asDouble(0)>resultado.path("salarioMax").asDouble(1_000_000_000)
                || (!resultado.path("exterior").asBoolean(true) && resultado.has("pais") && !"BR".equals(resultado.path("pais").asText())))
            throw new ResponseStatusException(BAD_REQUEST);
        return resultado;
    }
}
