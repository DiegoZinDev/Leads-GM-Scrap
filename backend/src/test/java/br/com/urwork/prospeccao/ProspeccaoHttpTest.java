package br.com.urwork.prospeccao;

import com.fasterxml.jackson.databind.*;
import java.net.*;
import java.net.http.*;
import java.nio.file.*;
import java.io.*;
import java.sql.DriverManager;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Consumer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class ProspeccaoHttpTest {
    @DynamicPropertySource static void configurar(DynamicPropertyRegistry cfg) throws Exception {
        var arquivo = Files.createTempFile("urwork-api-", ".db");
        arquivo.toFile().deleteOnExit();
        String url = "jdbc:sqlite:" + arquivo;
        try (var c = DriverManager.getConnection(url); var s = c.createStatement()) {
            for (String recurso : List.of("schema.sql","prospeccoes.sql"))
                try (var in = ProspeccaoHttpTest.class.getResourceAsStream("/"+recurso)) {
                    for (String sql : new String(in.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8).split(";"))
                        if (!sql.isBlank()) s.execute(sql);
                }
            s.execute("INSERT INTO usuario VALUES(1,'A','a@gmail.com','antiga',NULL,'teste','EMPRESA',NULL,NULL,NULL,NULL,NULL,NULL)");
            s.execute("INSERT INTO prospeccao VALUES(1,1,'anterior','TI','Campinas - SP',3,'EM_ANDAMENTO','2026-01-01')");
            s.execute("""
                INSERT INTO resultado_prospeccao VALUES(1,1,'maps-x','2026-01-01','{"nome":"Parcial"}')
                """);
        }
        cfg.add("spring.datasource.url", () -> url);
    }

    @LocalServerPort int porta;
    @Autowired JdbcTemplate db;
    @Autowired PasswordEncoder encoder;
    @Autowired ObjectMapper json;
    @MockitoBean MotorPython motor;
    @org.springframework.test.context.bean.override.mockito.MockitoSpyBean Relatorios relatorios;
    private URI uri(String caminho) { return URI.create("http://127.0.0.1:"+porta+"/api/"+caminho); }
    private HttpClient cliente() {
        return HttpClient.newBuilder().cookieHandler(new CookieManager(null,CookiePolicy.ACCEPT_ALL)).build();
    }
    private HttpResponse<String> get(HttpClient c,String caminho) throws Exception {
        return c.send(HttpRequest.newBuilder(uri(caminho)).GET().build(),HttpResponse.BodyHandlers.ofString());
    }
    private HttpResponse<String> post(HttpClient c,String caminho,String corpo,String tipo) throws Exception {
        var csrf = json.readTree(get(c,"auth/csrf").body());
        return c.send(HttpRequest.newBuilder(uri(caminho)).header("Content-Type",tipo)
            .header(csrf.get("headerName").asText(),csrf.get("token").asText())
            .POST(HttpRequest.BodyPublishers.ofString(corpo)).build(),HttpResponse.BodyHandlers.ofString());
    }
    private HttpClient login(String email) throws Exception {
        var c = cliente();
        assertEquals(204,post(c,"auth/login","email="+email+"&password=Senha12!","application/x-www-form-urlencoded").statusCode());
        return c;
    }

    @Test void semanaDeGeracaoComecaNaSegundaEmBrasilia() {
        assertEquals(java.time.LocalDate.parse("2025-12-29"),Relatorios.semana(java.time.Instant.parse("2026-01-05T02:59:59Z")));
        assertEquals(java.time.LocalDate.parse("2026-01-05"),Relatorios.semana(java.time.Instant.parse("2026-01-05T03:00:00Z")));
    }

    @Test void pdfOpcionalPersisteSomenteParaODonoEIsolaFalhaDeRenderizacao() throws Exception {
        var hash=encoder.encode("Senha12!");
        db.update("INSERT INTO usuario(username,email,senha,cpf) VALUES('PDF','pdf@gmail.com',?,'teste-pdf')",hash);
        db.update("INSERT INTO usuario(username,email,senha,cpf) VALUES('Outro','outro@gmail.com',?,'teste-outro')",hash);
        var a=login("pdf@gmail.com"); var b=login("outro@gmail.com");
        doAnswer(inv -> {
            Consumer<JsonNode> receber=inv.getArgument(1);
            receber.accept(json.readTree("""
                {"tipo":"lead","total":1,"lead":{"nome":"Loja A","cidade":"Campinas","telefone":"1234"}}
                """));
            return 1;
        }).when(motor).executar(any(),any());
        var dados=json.createObjectNode().put("chave",UUID.randomUUID().toString()).put("meta",3)
            .put("nicho","Serviços").put("regiao","Campinas - SP").put("tituloPdf","Clientes de Campinas");
        assertEquals(400,post(a,"prospeccoes",dados.deepCopy().put("tituloPdf","../inválido").toString(),"application/json").statusCode());
        var inicio=post(a,"prospeccoes",dados.toString(),"application/json");
        assertEquals(202,inicio.statusCode());
        var exec=json.readTree(inicio.body()).get("id").asLong();
        assertTrue(get(a,"prospeccoes/"+exec+"/eventos").body().contains("DISPONIVEL"));
        assertEquals(200,post(a,"prospeccoes",dados.toString(),"application/json").statusCode());
        dados.put("tituloPdf","Diferente");
        assertEquals(409,post(a,"prospeccoes",dados.toString(),"application/json").statusCode());
        var lista=json.readTree(get(a,"relatorios").body());
        assertEquals(1,lista.size());
        var item=lista.get(0);
        assertEquals(exec,item.get("execucao").asLong());
        assertEquals("Clientes de Campinas",item.get("titulo").asText());
        var id=item.get("id").asLong();
        assertTrue(item.get("nomeArquivo").asText().endsWith(" - "+id+".pdf"));
        assertEquals(lista,json.readTree(get(a,"relatorios?semana="+item.get("semana").asText()).body()));
        assertEquals(0,json.readTree(get(a,"relatorios?semana=2000-01-03").body()).size());
        assertEquals(400,get(a,"relatorios?semana=2000-01-04").statusCode());
        String rota="relatorios/"+id+"/pdf";
        var anexo=a.send(HttpRequest.newBuilder(uri(rota)).GET().build(),HttpResponse.BodyHandlers.ofByteArray());
        assertEquals(200,anexo.statusCode());
        assertEquals("application/pdf",anexo.headers().firstValue("Content-Type").orElseThrow());
        assertTrue(anexo.headers().firstValue("Content-Disposition").orElseThrow().startsWith("attachment;"));
        assertArrayEquals(db.queryForObject("SELECT pdf FROM relatorio WHERE id=?",byte[].class,id),anexo.body());
        assertTrue(new String(anexo.body(),0,5,java.nio.charset.StandardCharsets.US_ASCII).equals("%PDF-"));
        assertEquals(404,get(b,rota).statusCode());
        assertEquals(401,get(cliente(),rota).statusCode());
        assertEquals(0,json.readTree(get(b,"relatorios").body()).size());
        verify(relatorios).renderizar(argThat(doc -> doc.path("leads").size()==1
            && doc.path("leads").get(0).path("nome").asText().equals("Loja A") && doc.path("execucao").asLong()==exec));

        doThrow(new IOException("simulada")).when(relatorios).renderizar(any());
        dados.put("chave",UUID.randomUUID().toString());
        var falha=json.readTree(post(a,"prospeccoes",dados.toString(),"application/json").body()).get("id").asLong();
        String eventos=get(a,"prospeccoes/"+falha+"/eventos").body();
        assertTrue(eventos.contains("FALHOU"));
        assertTrue(eventos.contains("CONCLUIDA"));
        assertEquals(1,json.readTree(get(a,"leads?execucao="+falha).body()).size());
        assertEquals(1,json.readTree(get(a,"relatorios").body()).size());
    }

    @Test void cicloHttpMantemParciaisDeduplicaEIsolaContas() throws Exception {
        String hash = encoder.encode("Senha12!");
        db.update("UPDATE usuario SET senha=? WHERE id_usuario=1",hash);
        db.update("INSERT INTO usuario(username,email,senha,cpf) VALUES('B','b@gmail.com',?,'teste2')",hash);
        var a = login("a@gmail.com");
        var b = login("b@gmail.com");
        assertEquals(401,get(cliente(),"prospeccoes").statusCode());
        assertEquals("INTERROMPIDA",json.readTree(get(a,"prospeccoes/1").body()).get("estado").asText());
        assertEquals(1,json.readTree(get(a,"leads?execucao=1").body()).size());

        var liberar = new CountDownLatch(1);
        var salvo = new CountDownLatch(1);
        doAnswer(inv -> {
            Consumer<JsonNode> receber = inv.getArgument(1);
            receber.accept(json.readTree("""
                {"tipo":"lead","total":1,"lead":{"nome":"Atual","url_maps":"maps-x"}}
                """));
            salvo.countDown();
            if (!liberar.await(10,TimeUnit.SECONDS)) throw new IOException("timeout de teste");
            return 1;
        }).doAnswer(inv -> {
            Consumer<JsonNode> receber = inv.getArgument(1);
            receber.accept(json.readTree("""
                {"tipo":"lead","total":1,"lead":{"nome":"Outro","url_maps":"maps-y"}}
                """));
            throw new IOException("fonte indisponível");
        }).when(motor).executar(any(),any());

        String pedido = json.writeValueAsString(Map.of("chave",UUID.randomUUID(),"nicho","TI","regiao","Campinas - SP","meta",3));
        assertEquals(403,a.send(HttpRequest.newBuilder(uri("prospeccoes")).header("Content-Type","application/json")
                .POST(HttpRequest.BodyPublishers.ofString(pedido)).build(), HttpResponse.BodyHandlers.ofString()).statusCode());
        db.update("INSERT INTO usuario(username,email,senha) VALUES('Legado','c@gmail.com',?)",hash);
        assertEquals(403,post(login("c@gmail.com"),"prospeccoes",pedido,"application/json").statusCode());
        assertEquals(400,post(a,"prospeccoes",pedido.replace("\"meta\":3","\"meta\":1.5"),"application/json").statusCode());
        assertEquals(400,post(a,"prospeccoes",pedido.replace("Campinas - SP","Campinas - MG"),"application/json").statusCode());
        var inicio = post(a,"prospeccoes",pedido,"application/json");
        assertEquals(202,inicio.statusCode(),inicio.body());
        long id = json.readTree(inicio.body()).get("id").asLong();
        String caminho = "prospeccoes/"+id;
        try {
            assertTrue(salvo.await(5,TimeUnit.SECONDS));
            assertEquals(200,post(a,"prospeccoes",pedido,"application/json").statusCode());
            assertEquals(409,post(a,"prospeccoes",pedido.replace("TI","Saúde"),"application/json").statusCode());
            assertEquals(409,post(b,"prospeccoes",pedido,"application/json").statusCode());
            assertEquals(404,get(b,caminho).statusCode());
            assertEquals(404,get(b,caminho+"/eventos").statusCode());
            assertEquals(404,get(b,"leads?execucao="+id).statusCode());
            assertEquals(0,json.readTree(get(b,"leads").body()).size());
            assertEquals(1,json.readTree(get(a,caminho).body()).get("total").asInt());
            var sse = a.send(HttpRequest.newBuilder(uri(caminho+"/eventos")).GET().build(),HttpResponse.BodyHandlers.ofLines());
            try (var linhas = sse.body()) {
                var snapshots = linhas.filter(l -> l.startsWith("data:")).iterator();
                assertTrue(snapshots.next().contains("EM_ANDAMENTO"));
                liberar.countDown();
                assertTrue(snapshots.next().contains("CONCLUIDA"));
            }
        } finally { liberar.countDown(); }
        var finalizada = json.readTree(get(a,caminho).body());
        assertEquals("SEM_PDF", finalizada.path("estadoPdf").asText());
        assertEquals(0,json.readTree(get(a,"relatorios").body()).size());
        assertEquals(1,finalizada.get("total").asInt());
        assertEquals(3,finalizada.get("meta").asInt());
        assertTrue(get(a,caminho+"/eventos").body().contains("CONCLUIDA"));
        assertEquals("Atual",json.readTree(get(a,"leads").body()).get(0).get("dados").get("nome").asText());
        assertEquals(1,json.readTree(get(a,"leads").body()).size());

        var segunda = post(b,"prospeccoes",pedido,"application/json");
        assertEquals(202,segunda.statusCode());
        long outro = json.readTree(segunda.body()).get("id").asLong();
        assertTrue(get(b,"prospeccoes/"+outro+"/eventos").body().contains("INTERROMPIDA"));
        assertEquals(1,json.readTree(get(b,"leads").body()).size());
        assertEquals(2,json.readTree(get(a,"prospeccoes").body()).size());
        verify(motor,times(2)).executar(any(),any());
    }
}
