package br.com.urwork.dados;

import java.io.IOException;
import java.util.HashSet;
import java.util.Set;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;

public final class Municipios {
    private Municipios() {}
    public static boolean contem(String local) { return MUNICIPIOS.contains(local); }

    private static final Set<String> MUNICIPIOS = carregarMunicipios();

    private static Set<String> carregarMunicipios() {
        var locais = new HashSet<String>();
        try (var arquivo = new ClassPathResource("localidades.json").getInputStream()) {
            for (var estado : new ObjectMapper().readTree(arquivo)) {
                for (var cidade : estado.required("cidades")) {
                    locais.add(cidade.asText() + " - " + estado.required("uf").asText());
                }
            }
            return Set.copyOf(locais);
        } catch (IOException ex) {
            throw new IllegalStateException("Catálogo de municípios indisponível", ex);
        }
    }

}
