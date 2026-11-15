package br.com.urwork.contas;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.sql.DriverManager;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@AutoConfigureMockMvc
class ContaIntegrationTest {
    @DynamicPropertySource
    static void database(DynamicPropertyRegistry config) throws Exception {
        Path file = Files.createTempFile("zin-contas-", ".db");
        file.toFile().deleteOnExit();
        try (var banco = DriverManager.getConnection("jdbc:sqlite:" + file); var sql = banco.createStatement()) {
            sql.execute("""
                CREATE TABLE usuario(id_usuario INTEGER PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    email TEXT NOT NULL COLLATE NOCASE UNIQUE, senha TEXT NOT NULL, token TEXT)
                """);
            try (var insert = banco.prepareStatement("INSERT INTO usuario VALUES (42,'Legado','legado@example.com',?,'existente')")) {
                insert.setString(1, new Seguranca().passwordEncoder().encode("senha-antiga"));
                insert.executeUpdate();
            }
        }
        config.add("spring.datasource.url", () -> "jdbc:sqlite:" + file);
    }

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;
    @Autowired JdbcTemplate db;
    @Autowired MigracaoContas migracao;

    @Test void cicloDaConta() throws Exception {
        MockHttpSession session = new MockHttpSession();
        var token = csrf(session);
        String cadastro = """
            {"username":"Ana Silva","email":"Ana@gmail.com","password":"Abcd!123",
             "perfil":{"cpf":"000.000.001-91","finalidade":"EMPRESA","empresa":"Loja","ramo":"Varejo"}}
            """;
        mvc.perform(get("/api/auth/sessao")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/auth/cadastro").contentType("application/json").content(cadastro))
            .andExpect(status().isForbidden());
        mvc.perform(post("/api/auth/cadastro").session(session).header("X-CSRF-TOKEN",token)
            .contentType("application/json").content(cadastro)).andExpect(status().isCreated());
        for (String invalida : new String[]{"Abcde!123","abcd!123","Abcde123","Abcdef!1"}) {
            cadastrar(session, cadastro.replace("Abcd!123", invalida)).andExpect(status().isBadRequest());
        }
        cadastrar(session, cadastro.replace("gmail.com", "gmail.com.invalido")).andExpect(status().isBadRequest());
        String homonimo = cadastro.replace("Ana@gmail.com","outra@OUTLOOK.COM").replace("Abcd!123","A!12").replace("000.000.001-91","00000000272");
        cadastrar(session, homonimo).andExpect(status().isCreated());
        cadastrar(session, cadastro.replace("000.000.001-91","00000000353")).andExpect(status().isConflict());
        cadastrar(session, cadastro.replace("Ana@gmail.com","terceira@gmail.com").replace("000.000.001-91","00000000191"))
            .andExpect(status().isConflict());
        mvc.perform(post("/api/auth/login").session(session).header("X-CSRF-TOKEN",token)
            .param("email","ana@gmail.com").param("password","incorreta")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/auth/login").session(session).header("X-CSRF-TOKEN",token)
            .param("email","ANA@gmail.com").param("password","Abcd!123")).andExpect(status().isNoContent());
        mvc.perform(get("/api/auth/sessao").session(session)).andExpect(status().isOk())
            .andExpect(jsonPath("$.username").value("Ana Silva")).andExpect(jsonPath("$.perfilCompleto").value(true))
            .andExpect(jsonPath("$.senha").doesNotExist()).andExpect(jsonPath("$.cpf").doesNotExist());
        mvc.perform(post("/api/auth/logout").session(session).header("X-CSRF-TOKEN",csrf(session)))
            .andExpect(status().isNoContent());
        org.junit.jupiter.api.Assertions.assertTrue(session.isInvalid());
    }

    @Test void contaAntigaMantemAcessoECompletaPerfilUmaVez() throws Exception {
        migracao.afterPropertiesSet();
        assertEquals("existente", db.queryForObject("SELECT token FROM usuario WHERE id_usuario = 42", String.class));
        MockHttpSession session = new MockHttpSession();
        mvc.perform(post("/api/auth/login").session(session).header("X-CSRF-TOKEN",csrf(session))
            .param("email","legado@example.com").param("password","senha-antiga")).andExpect(status().isNoContent());
        mvc.perform(get("/api/auth/sessao").session(session)).andExpect(jsonPath("$.perfilCompleto").value(false));
        String perfil = """
            {"cpf":"00000000434","finalidade":"FREELANCER","servico":"Design","localidade":"Campinas - SP"}
            """;
        for (int expected : new int[]{204,409}) {
            mvc.perform(post("/api/auth/perfil").session(session).header("X-CSRF-TOKEN",csrf(session))
                .contentType("application/json").content(perfil)).andExpect(status().is(expected));
        }
        mvc.perform(get("/api/auth/sessao").session(session)).andExpect(jsonPath("$.perfilCompleto").value(true));
        assertEquals("00000000434", db.queryForObject("SELECT cpf FROM usuario WHERE id_usuario=42", String.class));
    }

    @Test void camposDependemDaFinalidadeEDocumentoValido() throws Exception {
        MockHttpSession session = new MockHttpSession();
        String cadastro = """
            {"username":"A Pessoa","email":"perfil@gmail.com","password":"Abcd!123",
             "perfil":{"cpf":"00000000515","finalidade":"EMPREGO","cargo":"Dev","ramo":"TI","localidade":"Vitória - ES","modalidade":"HIBRIDO"}}
            """;
        for (var troca : Map.of("00000000515","11111111111", "HIBRIDO","OUTRO", "EMPREGO","EMPRESA",
                "Dev"," ", "TI","", "Vitória - ES"," ").entrySet()) {
            cadastrar(session, cadastro.replace(troca.getKey(),troca.getValue())).andExpect(status().isBadRequest());
        }
        cadastrar(session, cadastro.replace("00000000515", "00000000516")).andExpect(status().isBadRequest());
        cadastrar(session, cadastro.replace("Vitória - ES", "Campinas - MG")).andExpect(status().isBadRequest());
        cadastrar(session, cadastro.replace("Vitória - ES", "Brasil")).andExpect(status().isBadRequest());
        String locais = "Belo Horizonte - MG\nCampinas - SP";
        cadastrar(session, cadastro.replace("\"Vitória - ES\"", json.writeValueAsString(locais))).andExpect(status().isCreated());
        assertEquals(locais, db.queryForObject("select localidade from usuario where email = 'perfil@gmail.com'", String.class));
    }

    private ResultActions cadastrar(MockHttpSession session, String dados) throws Exception {
        return mvc.perform(post("/api/auth/cadastro").session(session).header("X-CSRF-TOKEN",csrf(session))
                .contentType("application/json").content(dados));
    }

    private String csrf(MockHttpSession session) throws Exception {
        String result = mvc.perform(get("/api/auth/csrf").session(session)).andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();
        return json.readTree(result).get("token").asText();
    }
}
