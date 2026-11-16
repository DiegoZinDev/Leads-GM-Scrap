package br.com.urwork.prospeccao;

import br.com.urwork.dados.Municipios;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.sql.SQLException;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.springframework.context.annotation.DependsOn;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.*;

@Service
@DependsOn("migracaoContas")
class Prospeccoes {
    record Entrada(UUID chave, String nicho, String regiao, JsonNode meta, String tituloPdf, JsonNode filtrosSociais) {}
    record Estado(long id, String nicho, String regiao, int meta, int total, String estado, String criadaEm, String tituloPdf, String estadoPdf, Filtros filtrosSociais) {}
    record Inicio(Estado estado, boolean nova) {}
    record Lead(long execucao, String coletadoEm, JsonNode dados) {}

    private static final String CONSULTA = """
        SELECT p.*,fs.instagram,fs.whatsapp,fs.seguidores,rpdf.titulo AS titulo_pdf,COALESCE(rpdf.estado,'SEM_PDF') AS estado_pdf, (SELECT COUNT(*) FROM resultado_prospeccao r WHERE r.execucao=p.id) AS total
        FROM prospeccao p JOIN usuario u ON u.id_usuario=p.dono LEFT JOIN relatorio rpdf ON rpdf.execucao=p.id LEFT JOIN filtro_social fs ON fs.execucao=p.id WHERE u.email=?
        """;
    private static final RowMapper<Estado> MAPA = (rs, n) -> new Estado(rs.getLong("id"),rs.getString("nicho"),
        rs.getString("regiao"),rs.getInt("meta"),rs.getInt("total"),rs.getString("estado"),rs.getString("criada_em"),
        rs.getString("titulo_pdf"),rs.getString("estado_pdf"),new Filtros(rs.getBoolean("instagram"),rs.getBoolean("whatsapp"),(Integer)rs.getObject("seguidores")));

    private final JdbcTemplate db;
    private final MotorPython motor;
    private final Relatorios relatorios;
    private final Conexoes conexoes;
    private final org.springframework.transaction.support.TransactionTemplate tx;
    private final ObjectMapper json;
    private final ExecutorService executor = Executors.newSingleThreadExecutor(Thread.ofVirtual().factory());

    Prospeccoes(JdbcTemplate db, MotorPython motor, ObjectMapper json, Relatorios relatorios, Conexoes conexoes,
                org.springframework.transaction.support.TransactionTemplate tx) {
        this.tx = tx;
        this.conexoes = conexoes;
        this.relatorios = relatorios;
        this.db = db;
        this.motor = motor;
        this.json = json;
    }

    @PostConstruct void iniciar() {
        new ResourceDatabasePopulator(new ClassPathResource("prospeccoes.sql")).execute(db.getDataSource());
        tx.executeWithoutResult(s -> {
            db.update("UPDATE relatorio SET estado='FALHOU' WHERE estado='PENDENTE'");
            db.update("UPDATE prospeccao SET estado='INTERROMPIDA' WHERE estado='EM_ANDAMENTO'");
        });
    }

    @PreDestroy void parar() {
        motor.parar();
        executor.shutdown();
        try {
            if (!executor.awaitTermination(5, java.util.concurrent.TimeUnit.SECONDS)) executor.shutdownNow();
        } catch (InterruptedException ex) {
            executor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    List<Estado> historico(String email) {
        return db.query(CONSULTA + " ORDER BY p.id DESC", MAPA, email);
    }

    Estado consultar(String email, long id) {
        return db.query(CONSULTA + " AND p.id=?", MAPA, email,id).stream().findFirst()
            .orElseThrow(() -> new ResponseStatusException(NOT_FOUND));
    }

    synchronized Inicio agendar(String email, Entrada entrada) {
        if (entrada.chave() == null || entrada.nicho() == null || entrada.nicho().isBlank()
                || entrada.nicho().length() > 120 || entrada.regiao() == null || !Municipios.contem(entrada.regiao())
                || entrada.meta() == null || !entrada.meta().isIntegralNumber()
                || !entrada.meta().canConvertToInt() || entrada.meta().intValue() < 1)
            throw new ResponseStatusException(BAD_REQUEST);
        String tituloPdf = Relatorios.tituloValido(entrada.tituloPdf());
        var ids = db.queryForList("SELECT id_usuario FROM usuario WHERE email=? AND cpf IS NOT NULL", Long.class,email);
        if (ids.isEmpty()) throw new ResponseStatusException(FORBIDDEN);
        var filtros = Filtros.ler(entrada.filtrosSociais());
        var pedido = new MotorPython.Pedido(entrada.nicho().strip(), entrada.regiao(), entrada.meta().intValue(),filtros);
        var chave = entrada.chave().toString();
        var anterior = db.query(CONSULTA + " AND p.chave=?", MAPA,email,chave);
        if (!anterior.isEmpty()) {
            var estado = anterior.getFirst();
            if (!estado.nicho().equals(pedido.nicho()) || !estado.regiao().equals(pedido.regiao()) || estado.meta()!=pedido.meta()
                    || !estado.filtrosSociais().equals(filtros) || !java.util.Objects.equals(estado.tituloPdf(), tituloPdf))
                throw new ResponseStatusException(CONFLICT);
            return new Inicio(estado, false);
        }
        conexoes.exigir(email,filtros);
        long id = tx.execute(status -> {
            var inseridos = db.queryForList("""
                INSERT INTO prospeccao(dono,chave,nicho,regiao,meta,estado,criada_em)
                VALUES(?,?,?,?,?,'EM_ANDAMENTO',?) ON CONFLICT DO NOTHING RETURNING id
                """, Long.class, ids.getFirst(),chave,pedido.nicho(),pedido.regiao(),pedido.meta(),Instant.now().toString());
            if (inseridos.isEmpty()) throw new ResponseStatusException(CONFLICT);
            long nova = inseridos.getFirst();
            if (!filtros.equals(Filtros.NENHUM)) db.update("INSERT INTO filtro_social VALUES(?,?,?,?)",nova,filtros.instagramVerificado(),filtros.whatsappLinkPublicado(),filtros.seguidoresMinimos());
            if (tituloPdf != null) db.update("INSERT INTO relatorio(execucao,titulo) VALUES(?,?)", nova,tituloPdf);
            return nova;
        });
        var inicial = consultar(email,id);
        try { executor.execute(() -> executar(id,pedido)); }
        catch (java.util.concurrent.RejectedExecutionException ex) {
            relatorios.finalizar(id,"INTERROMPIDA");
            throw new ResponseStatusException(SERVICE_UNAVAILABLE);
        }
        return new Inicio(inicial,true);
    }

    private void executar(long id, MotorPython.Pedido pedido) {
        String fim = "INTERROMPIDA";
        try {
            motor.executar(pedido, evento -> {
                if (!"lead".equals(evento.path("tipo").asText())) return;
                var lead = evento.required("lead");
                String identidade = lead.path("url_maps").asText("").split("[?]",2)[0].strip();
                if (identidade.isEmpty())
                    identidade = (lead.path("nome").asText() + "|" + lead.path("cidade").asText(pedido.regiao())).toLowerCase(Locale.ROOT);
                db.update("INSERT INTO resultado_prospeccao(execucao,ordem,identidade,coletado_em,dados) VALUES(?,?,?,?,?)",
                    id,evento.required("total").intValue(),identidade,Instant.now().toString(),lead.toString());
            });
            fim = "CONCLUIDA";
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
        } catch (java.io.IOException | RuntimeException ex) {
            org.slf4j.LoggerFactory.getLogger(Prospeccoes.class).warn("Execução {} interrompida ({})", id,ex.getClass().getSimpleName());
        } finally { relatorios.finalizar(id,fim); }
    }

    List<Lead> leads(String email, Long id) {
        if (id != null) consultar(email,id);
        var filtro = id == null ? "" : " AND p.id=?";
        var args = id == null ? new Object[]{email} : new Object[]{email,id};
        return db.query("""
            SELECT * FROM (
                SELECT r.*, ROW_NUMBER() OVER(PARTITION BY identidade ORDER BY execucao DESC,ordem DESC) AS pos
                FROM resultado_prospeccao r JOIN prospeccao p ON p.id=r.execucao
                JOIN usuario u ON u.id_usuario=p.dono WHERE u.email=?
            """ + filtro + ") WHERE pos=1 ORDER BY execucao DESC,ordem", (rs,n) -> {
                try { return new Lead(rs.getLong("execucao"),rs.getString("coletado_em"),json.readTree(rs.getString("dados"))); }
                catch (java.io.IOException ex) { throw new SQLException("Resultado inválido",ex); }
            }, args);
    }
}
