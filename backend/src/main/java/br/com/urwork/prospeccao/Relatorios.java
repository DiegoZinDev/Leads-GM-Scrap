package br.com.urwork.prospeccao;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.file.Files;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.temporal.TemporalAdjusters;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.*;

@Service
class Relatorios {
    record Item(long id,long execucao,String titulo,String geradoEm,String semana,String nomeArquivo) {}
    record Arquivo(String nome,byte[] pdf) {}
    static final ZoneId FUSO = ZoneId.of("America/Sao_Paulo");
    private static final DateTimeFormatter HORA = DateTimeFormatter.ofPattern("dd/MM/uuuu HH:mm").withZone(FUSO);
    private static final DateTimeFormatter NOME = DateTimeFormatter.ofPattern("uuuu-MM-dd - HH'h'mm").withZone(FUSO);
    private static final String DONO = """
        FROM relatorio r JOIN prospeccao p ON p.id=r.execucao JOIN usuario u ON u.id_usuario=p.dono
        WHERE r.estado='DISPONIVEL' AND u.email=?
        """;
    private final JdbcTemplate db;
    private final TransactionTemplate tx;
    private final ObjectMapper json;
    Relatorios(JdbcTemplate db, TransactionTemplate tx, ObjectMapper json) {
        this.db=db; this.tx=tx; this.json=json;
    }

    static String tituloValido(String titulo) {
        if (titulo == null) return null;
        if (titulo.isBlank() || titulo.length()>100 || titulo.matches("(?s).*[\\p{Cntrl}<>:\"/\\\\|?*].*"))
            throw new ResponseStatusException(BAD_REQUEST);
        return titulo.strip();
    }

    static LocalDate semana(Instant gerado) {
        return gerado.atZone(FUSO).toLocalDate().with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
    }

    List<Item> listar(String email,LocalDate semana) {
        if (semana != null && semana.getDayOfWeek()!=DayOfWeek.MONDAY) throw new ResponseStatusException(BAD_REQUEST);
        return db.query("SELECT r.id,r.execucao,r.titulo,r.gerado_em,r.semana,r.nome_arquivo " + DONO
            + (semana==null ? "" : " AND r.semana=?") + " ORDER BY r.gerado_em DESC,r.id DESC",
            (rs,i)->new Item(rs.getLong(1),rs.getLong(2),rs.getString(3),rs.getString(4),rs.getString(5),rs.getString(6)),
            semana==null ? new Object[]{email} : new Object[]{email,semana.toString()});
    }

    Arquivo baixar(String email,long id) {
        return db.query("SELECT r.nome_arquivo,r.pdf " + DONO + " AND r.id=?",
            (rs,i)->new Arquivo(rs.getString(1),rs.getBytes(2)),email,id).stream().findFirst()
            .orElseThrow(()->new ResponseStatusException(NOT_FOUND));
    }

    void finalizar(long execucao,String estado) {
        if ("CONCLUIDA".equals(estado)) {
            var pedidos=db.queryForList("""
                SELECT r.id,r.titulo,p.meta,p.nicho,p.regiao,p.criada_em FROM relatorio r JOIN prospeccao p
                ON p.id=r.execucao WHERE r.execucao=? AND r.estado='PENDENTE'
                """,execucao);
            if (!pedidos.isEmpty()) {
                try {
                    var pedido=pedidos.getFirst();
                    long id=((Number)pedido.get("id")).longValue();
                    var gerado=Instant.now();
                    String titulo=(String)pedido.get("titulo");
                    ObjectNode doc=json.valueToTree(pedido);
                    doc.put("execucao",execucao).put("inicio",HORA.format(Instant.parse((String)pedido.get("criada_em"))))
                        .put("geracao",HORA.format(gerado));
                    var leads=doc.putArray("leads");
                    for (String registro:db.queryForList("SELECT dados FROM resultado_prospeccao WHERE execucao=? ORDER BY ordem",String.class,execucao))
                        leads.add(json.readTree(registro));
                    byte[] pdf=renderizar(doc);
                    String nome=titulo+" - "+NOME.format(gerado)+" - "+id+".pdf";
                    tx.executeWithoutResult(s->{
                        db.update("UPDATE relatorio SET estado='DISPONIVEL',gerado_em=?,semana=?,nome_arquivo=?,pdf=? WHERE id=?",
                            gerado.toString(),semana(gerado).toString(),nome,pdf,id);
                        encerrar(execucao,estado);
                    });
                    return;
                } catch (InterruptedException ex) {
                    Thread.currentThread().interrupt();
                } catch (IOException | RuntimeException ex) {
                    org.slf4j.LoggerFactory.getLogger(Relatorios.class).warn("Falha ao gerar PDF da execução {} ({})",execucao,ex.getClass().getSimpleName());
                }
            }
        }
        tx.executeWithoutResult(s->{
            db.update("UPDATE relatorio SET estado='FALHOU' WHERE execucao=? AND estado='PENDENTE'",execucao);
            encerrar(execucao,estado);
        });
    }

    private void encerrar(long execucao,String estado) {
        db.update("UPDATE prospeccao SET estado=? WHERE id=? AND estado='EM_ANDAMENTO'",estado,execucao);
    }

    byte[] renderizar(JsonNode lote) throws IOException,InterruptedException {
        var raiz=MotorPython.raizProjeto();
        var entrada=Files.createTempFile("urwork-lote-", ".json");
        try {
            json.writeValue(entrada.toFile(),lote);
            var saida=Files.createTempFile("urwork-relatorio-", ".pdf");
            try {
                var builder=new ProcessBuilder(MotorPython.interpretador(raiz),"-m","engine.relatorio")
                    .directory(raiz.toFile()).redirectInput(entrada.toFile()).redirectOutput(saida.toFile())
                    .redirectError(ProcessBuilder.Redirect.DISCARD);
                builder.environment().put("PYTHONIOENCODING","utf-8");
                var processo=builder.start();
                try {
                    if (!processo.waitFor(2,java.util.concurrent.TimeUnit.MINUTES) || processo.exitValue()!=0)
                        throw new IOException("Renderização interrompida");
                    byte[] pdf = Files.readAllBytes(saida);
                    if (pdf.length < 5 || !new String(pdf,0,5,java.nio.charset.StandardCharsets.US_ASCII).equals("%PDF-"))
                        throw new IOException("O renderizador devolveu um arquivo inválido");
                    return pdf;
                } finally {
                    if (processo.isAlive()) {
                        var filhos=processo.descendants().toList();
                        processo.destroyForcibly();
                        filhos.forEach(ProcessHandle::destroyForcibly);
                        processo.waitFor();
                    }
                }
            } finally { Files.deleteIfExists(saida); }
        } finally { Files.deleteIfExists(entrada); }
    }
}
