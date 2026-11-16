package br.com.urwork.prospeccao;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.Locale;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.*;

@RestController
class CurriculoController {
    private final ObjectMapper json;
    private final Semaphore leitor = new Semaphore(1);
    CurriculoController(ObjectMapper json) { this.json = json; }

    @PostMapping("/api/vagas/curriculo")
    JsonNode sugerir(@RequestParam MultipartFile arquivo) throws IOException {
        var nome = arquivo.getOriginalFilename();
        if (arquivo.getSize()>1024*1024) throw new ResponseStatusException(PAYLOAD_TOO_LARGE);
        if (arquivo.isEmpty() || nome==null) throw new ResponseStatusException(BAD_REQUEST);
        String tipo = nome.substring(nome.lastIndexOf('.')+1).toLowerCase(Locale.ROOT);
        if (!tipo.equals("pdf") && !tipo.equals("docx")) throw new ResponseStatusException(UNSUPPORTED_MEDIA_TYPE);
        if (!leitor.tryAcquire()) throw new ResponseStatusException(TOO_MANY_REQUESTS);
        try {
            var raiz = MotorPython.raizProjeto();
            var comando = new ProcessBuilder(MotorPython.interpretador(raiz),"-m","engine.curriculo",tipo)
                .directory(raiz.toFile()).redirectError(ProcessBuilder.Redirect.DISCARD);
            comando.environment().keySet().removeIf(k -> k.regionMatches(true,0,"URWORK_META_",0,12));
            Process processo = comando.start();
            try {
                // O leitor consome toda a entrada antes de abrir o documento.
                try (var entrada=processo.getOutputStream(); var dados=arquivo.getInputStream()) { dados.transferTo(entrada); }
                if (!processo.waitFor(15,TimeUnit.SECONDS)) throw new ResponseStatusException(UNPROCESSABLE_ENTITY);
                if (processo.exitValue()!=0) throw new ResponseStatusException(UNPROCESSABLE_ENTITY);
                try (var saida=processo.getInputStream()) { return json.readTree(saida); }
            } finally { processo.destroyForcibly(); }
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(SERVICE_UNAVAILABLE);
        } finally { leitor.release(); }
    }
}
