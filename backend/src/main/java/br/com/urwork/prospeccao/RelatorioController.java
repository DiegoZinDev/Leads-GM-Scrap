package br.com.urwork.prospeccao;

import java.nio.charset.StandardCharsets;
import java.security.Principal;
import java.time.LocalDate;
import java.util.List;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/relatorios")
class RelatorioController {
    private final Relatorios relatorios;
    RelatorioController(Relatorios relatorios) { this.relatorios = relatorios; }

    @GetMapping
    List<Relatorios.Item> listar(Principal conta, @RequestParam(required=false) LocalDate semana) {
        return relatorios.listar(conta.getName(),semana);
    }

    @GetMapping("/{id}/pdf")
    ResponseEntity<byte[]> baixar(Principal conta,@PathVariable long id) {
        var arquivo = relatorios.baixar(conta.getName(),id);
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_PDF).cacheControl(CacheControl.noStore())
            .header(HttpHeaders.CONTENT_DISPOSITION,ContentDisposition.attachment()
                .filename(arquivo.nome(),StandardCharsets.UTF_8).build().toString())
            .body(arquivo.pdf());
    }
}
