package br.com.urwork.prospeccao;

import jakarta.servlet.http.HttpSession;
import java.io.IOException;
import java.security.Principal;
import java.util.List;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api")
class ProspeccaoController {
    private final Prospeccoes buscas;
    ProspeccaoController(Prospeccoes buscas) { this.buscas = buscas; }

    @PostMapping("/prospeccoes")
    ResponseEntity<Prospeccoes.Estado> iniciar(Principal usuario, @RequestBody Prospeccoes.Entrada entrada) {
        var inicio = buscas.agendar(usuario.getName(),entrada);
        return ResponseEntity.status(inicio.nova() ? 202 : 200).body(inicio.estado());
    }

    @GetMapping("/prospeccoes")
    List<Prospeccoes.Estado> historico(Principal usuario) { return buscas.historico(usuario.getName()); }

    @GetMapping("/prospeccoes/{id}")
    Prospeccoes.Estado consultar(Principal usuario, @PathVariable long id) { return buscas.consultar(usuario.getName(),id); }

    @GetMapping("/leads")
    List<Prospeccoes.Lead> leads(Principal usuario, @RequestParam(required=false) Long execucao) {
        return buscas.leads(usuario.getName(),execucao);
    }

    @GetMapping(value="/prospeccoes/{id}/eventos", produces=MediaType.TEXT_EVENT_STREAM_VALUE)
    ResponseEntity<SseEmitter> eventos(Principal usuario, @PathVariable long id, HttpSession sessao) {
        var email = usuario.getName();
        var inicial = buscas.consultar(email,id);
        var emitter = new SseEmitter(0L);
        var envio = Thread.startVirtualThread(() -> {
            try {
                var atual = inicial;
                Prospeccoes.Estado anterior = null;
                int segundos = 0;
                while (!Thread.currentThread().isInterrupted()) {
                    sessao.getCreationTime(); // Uma sessão invalidada interrompe o stream já aberto.
                    if (!atual.equals(anterior)) emitter.send(SseEmitter.event().name("estado").data(atual));
                    else if (++segundos % 15 == 0) emitter.send(SseEmitter.event().comment("ativo"));
                    if (!"EM_ANDAMENTO".equals(atual.estado())) break;
                    anterior = atual;
                    Thread.sleep(1000);
                    atual = buscas.consultar(email,id);
                }
                emitter.complete();
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                emitter.complete();
            } catch (IOException | RuntimeException ex) { emitter.completeWithError(ex); }
        });
        emitter.onCompletion(envio::interrupt);
        emitter.onTimeout(envio::interrupt);
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(emitter);
    }
}
