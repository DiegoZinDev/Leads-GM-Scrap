package br.com.urwork.prospeccao;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class MotorPython {
    public record Pedido(String nicho, String regiao, int meta, Filtros filtrosSociais, JsonNode vagas) {
        public Pedido(String nicho, String regiao, int meta) { this(nicho,regiao,meta,Filtros.NENHUM,null); }
        public Pedido {
            if (meta < 1 || nicho == null || regiao == null || (vagas == null && (nicho.isBlank() || regiao.isBlank())))
                throw new IllegalArgumentException("Informe nicho, região e uma meta positiva.");
        }
    }

    private final ObjectMapper json;
    private final Path raiz;
    private final List<String> comando;
    private final AtomicBoolean ocupado = new AtomicBoolean();
    private Process processoAtual;
    private boolean encerrando;

    synchronized void parar() {
        encerrando = true;
        if (processoAtual != null) encerrar(processoAtual);
    }

    @Autowired
    public MotorPython(ObjectMapper json) {
        this(json, raizProjeto(), List.of("-m", "engine.worker"));
    }

    MotorPython(ObjectMapper json, Path raiz, List<String> argumentos) {
        this.json = json;
        this.raiz = raiz;
        var cmd = new java.util.ArrayList<String>();
        cmd.add(interpretador(raiz));
        cmd.addAll(argumentos);
        this.comando = List.copyOf(cmd);
    }

    static Path raizProjeto() {
        var cwd = Path.of("").toAbsolutePath().normalize();
        return cwd.endsWith("backend") ? cwd.getParent() : cwd;
    }

    static String interpretador(Path raiz) {
        var windows = raiz.resolve(".venv/Scripts/python.exe");
        var python = Files.isRegularFile(windows) ? windows : raiz.resolve(".venv/bin/python");
        return System.getenv().getOrDefault("URWORK_PYTHON", python.toString());
    }

    public int executar(Pedido pedido, Consumer<JsonNode> receber) throws IOException, InterruptedException {
        if (!ocupado.compareAndSet(false, true)) throw new IllegalStateException("Motor ocupado.");
        try {
            var builder = new ProcessBuilder(comando).directory(raiz.toFile());
            builder.environment().keySet().removeIf(k -> k.regionMatches(true,0,"URWORK_META_",0,12));
            builder.environment().put("PYTHONIOENCODING", "utf-8");
            builder.redirectError(ProcessBuilder.Redirect.DISCARD);
            final Process processo;
            synchronized (this) {
                if (encerrando) throw new IOException("Instalação em encerramento.");
                processo = builder.start();
                processoAtual = processo;
            }
            // Fecha também o Chromium se o consumidor falhar ou o motor ficar bloqueado.
            var limite = Thread.startVirtualThread(() -> {
                try {
                    Thread.sleep(java.time.Duration.ofHours(2));
                    encerrar(processo);
                } catch (InterruptedException terminado) { Thread.currentThread().interrupt(); }
            });
            try {
                json.writeValue(processo.getOutputStream(), pedido);
                int total = 0;
                boolean iniciou = false, terminou = false;
                try (var reader = processo.inputReader(java.nio.charset.StandardCharsets.UTF_8)) {
                    for (String linha; (linha = reader.readLine()) != null;) {
                        var evento = json.readTree(linha);
                        if (evento == null || terminou) throw new IOException("Evento inesperado.");
                        switch (evento.path("tipo").asText()) {
                            case "inicio" -> {
                                if (iniciou || evento.path("meta").asInt(-1) != pedido.meta())
                                    throw new IOException("Início inválido.");
                                iniciou = true;
                            }
                            case "lead","vaga" -> {
                                String tipo = pedido.vagas() == null ? "lead" : "vaga";
                                if (!iniciou || total >= pedido.meta() || !tipo.equals(evento.path("tipo").asText()) || !evento.path(tipo).isObject()
                                        || evento.path("total").asInt(-1) != total + 1)
                                    throw new IOException("Contagem de leads inválida.");
                                total++;
                            }
                            case "fim" -> {
                                if (!iniciou || evento.path("total").asInt(-1) != total)
                                    throw new IOException("Conclusão inválida.");
                                terminou = true;
                            }
                            default -> throw new IOException("Tipo de evento desconhecido.");
                        }
                        if (!terminou) receber.accept(evento);
                    }
                }
                if (processo.waitFor() != 0 || !terminou) throw new IOException("Motor interrompido.");
                receber.accept(json.createObjectNode().put("tipo", "fim").put("total", total));
                return total;
            } finally {
                limite.interrupt();
                encerrar(processo);
            }
        } finally {
            synchronized (this) { processoAtual = null; }
            ocupado.set(false);
        }
    }

    private static void encerrar(Process processo) {
        if (processo.isAlive()) {
            var filhos = processo.descendants().toList();
            processo.destroyForcibly();
            filhos.forEach(ProcessHandle::destroyForcibly);
        }
    }
}
