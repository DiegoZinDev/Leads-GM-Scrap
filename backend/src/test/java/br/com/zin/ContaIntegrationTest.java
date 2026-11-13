package br.com.zin;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class ContaIntegrationTest {
    @DynamicPropertySource
    static void database(DynamicPropertyRegistry config) throws Exception {
        Path file = Files.createTempFile("zin-contas-", ".db");
        file.toFile().deleteOnExit();
        config.add("spring.datasource.url", () -> "jdbc:sqlite:" + file);
    }

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;

    @Test void cicloDaConta() throws Exception {
        MockHttpSession session = new MockHttpSession();
        var token = csrf(session);
        String cadastro = """
            {"username":"Ana","email":"Ana@example.com","password":"senha-de-teste"}
            """;
        mvc.perform(get("/api/auth/sessao")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/auth/cadastro").contentType("application/json").content(cadastro))
            .andExpect(status().isForbidden());
        for (int expected : new int[]{201,409}) {
            mvc.perform(post("/api/auth/cadastro").session(session).header("X-CSRF-TOKEN",token)
                .contentType("application/json").content(cadastro)).andExpect(status().is(expected));
        }
        mvc.perform(post("/api/auth/login").session(session).header("X-CSRF-TOKEN",token)
            .param("email","ana@example.com").param("password","incorreta")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/auth/login").session(session).header("X-CSRF-TOKEN",token)
            .param("email","ANA@example.com").param("password","senha-de-teste")).andExpect(status().isNoContent());
        mvc.perform(get("/api/auth/sessao").session(session)).andExpect(status().isOk())
            .andExpect(jsonPath("$.username").value("Ana")).andExpect(jsonPath("$.senha").doesNotExist());
        mvc.perform(post("/api/auth/logout").session(session).header("X-CSRF-TOKEN",csrf(session)))
            .andExpect(status().isNoContent());
        org.junit.jupiter.api.Assertions.assertTrue(session.isInvalid());
    }

    private String csrf(MockHttpSession session) throws Exception {
        String result = mvc.perform(get("/api/auth/csrf").session(session)).andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();
        return json.readTree(result).get("token").asText();
    }
}
