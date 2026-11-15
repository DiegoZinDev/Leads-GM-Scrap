package br.com.urwork.contas;

import java.io.IOException;
import java.util.HashSet;
import java.util.Set;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;

import jakarta.persistence.Embeddable;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

@Embeddable
record DadosPerfil(@NotBlank String cpf, @NotBlank String finalidade,
                   @Size(max=120) String empresa, @Size(max=120) String ramo,
                   @Size(max=120) String servico, @Size(max=300000) String localidade,
                   @Size(max=120) String cargo, String modalidade) {
    DadosPerfil validado() {
        String documento = validarCpf(cpf);
        return switch (finalidade) {
            case "EMPRESA" -> new DadosPerfil(documento, finalidade, exigir(empresa), exigir(ramo),
                    null, null, null, null);
            case "FREELANCER" -> new DadosPerfil(documento, finalidade, null, null,
                    exigir(servico), validarLocais(localidade), null, null);
            case "EMPREGO" -> {
                if (!"PRESENCIAL".equals(modalidade) && !"HIBRIDO".equals(modalidade) && !"REMOTO".equals(modalidade)) {
                    throw invalido();
                }
                yield new DadosPerfil(documento, finalidade, null, exigir(ramo), null,
                        validarLocais(localidade), exigir(cargo), modalidade);
            }
            default -> throw invalido();
        };
    }

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

    private static String validarLocais(String valor) {
        String locais = exigir(valor);
        var selecionados = new HashSet<String>();
        if (!locais.lines().allMatch(l -> MUNICIPIOS.contains(l) && selecionados.add(l))) throw invalido();
        return locais;
    }

    private static String exigir(String valor) {
        if (valor == null || valor.isBlank()) throw invalido();
        return valor.strip();
    }

    private static String validarCpf(String entrada) {
        if (!entrada.matches("[0-9]{11}|[0-9]{3}\\.[0-9]{3}\\.[0-9]{3}-[0-9]{2}")) throw invalido();
        String cpf = entrada.replace(".", "").replace("-", "");
        if (cpf.chars().distinct().count() == 1) throw invalido();
        for (int pos = 9; pos <= 10; pos++) {
            int soma = 0;
            for (int i = 0; i < pos; i++) soma += (cpf.charAt(i) - '0') * (pos + 1 - i);
            int digito = soma * 10 % 11 % 10;
            if (cpf.charAt(pos) - '0' != digito) throw invalido();
        }
        return cpf;
    }

    private static ResponseStatusException invalido() {
        return new ResponseStatusException(HttpStatus.BAD_REQUEST, "CPF ou dados do perfil inválidos.");
    }
}
