package br.com.urwork.prospeccao;

import jakarta.servlet.http.HttpSession;
import java.net.URI;
import java.security.Principal;
import java.time.Instant;
import java.util.*;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.encrypt.Encryptors;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.*;

@RestController
@RequestMapping("/api/conexoes")
class Conexoes {
    enum Filtro { INSTAGRAM_VERIFICADO, SEGUIDORES_MINIMOS, WHATSAPP_LINK_PUBLICADO }
    record Estado(Meta.Rede rede, String estado, List<Filtro> capacidades) {}
    private record Tentativa(String dono, Meta.Rede rede, String state, Instant expira) {}
    private final JdbcTemplate db;
    private final Meta meta;
    Conexoes(JdbcTemplate db, Meta meta) { this.db = db; this.meta = meta; }

    @GetMapping List<Estado> listar(Principal usuario) {
        return Arrays.stream(Meta.Rede.values()).map(r -> consultar(usuario.getName(),r)).toList();
    }
    private Estado consultar(String email, Meta.Rede rede) {
        if (!meta.configurada(rede)) return new Estado(rede,"NAO_CONFIGURADA",List.of());
        var salvo = db.queryForList("SELECT token FROM conexao_social WHERE dono=(SELECT id_usuario FROM usuario WHERE email=?) AND rede=?",String.class,email,rede.name());
        if (salvo.isEmpty()) return new Estado(rede,"DESCONECTADA",List.of());
        try {
            if (meta.valida(rede,cifra().decrypt(salvo.getFirst())))
                return new Estado(rede,"CONECTADA",rede == Meta.Rede.INSTAGRAM ? List.of(Filtro.INSTAGRAM_VERIFICADO,Filtro.SEGUIDORES_MINIMOS) : List.of(Filtro.WHATSAPP_LINK_PUBLICADO));
            return new Estado(rede,"EXPIRADA",List.of());
        } catch (ResponseStatusException | IllegalStateException ex) { return new Estado(rede,"INDISPONIVEL",List.of()); }
    }
    void exigir(String email, Filtros filtros) {
        if (filtros.instagramVerificado() || filtros.seguidoresMinimos() != null)
            exigirConectada(email,Meta.Rede.INSTAGRAM);
        if (filtros.whatsappLinkPublicado())
            exigirConectada(email,Meta.Rede.WHATSAPP);
    }
    static final class FalhaSocial extends ResponseStatusException {
        private final org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
        FalhaSocial(String motivo) {
            super(motivo.equals("INDISPONIVEL") ? SERVICE_UNAVAILABLE : CONFLICT);
            headers.set("UrWork-Conexao-Social",motivo);
        }
        @Override public org.springframework.http.HttpHeaders getHeaders() { return headers; }
    }
    private void exigirConectada(String email, Meta.Rede rede) {
        var estado = consultar(email,rede);
        if (!estado.estado.equals("CONECTADA"))
            throw new FalhaSocial(estado.estado);
    }
    private org.springframework.security.crypto.encrypt.TextEncryptor cifra() {
        return Encryptors.delux(meta.valor("CHAVE"),"5572576f726b4d657461");
    }
    @PostMapping("/{rede}/autorizar") Map<String,URI> autorizar(Principal usuario,@PathVariable Meta.Rede rede,HttpSession sessao) {
        if (!meta.configurada(rede)) throw new ResponseStatusException(SERVICE_UNAVAILABLE);
        String state = UUID.randomUUID().toString();
        sessao.setAttribute("meta.oauth",new Tentativa(usuario.getName(),rede,state,Instant.now().plusSeconds(600)));
        return Map.of("url",meta.autorizar(rede,state));
    }
    @GetMapping("/retorno") ResponseEntity<Void> retorno(Principal usuario,HttpSession sessao,@RequestParam String state,
                                                          @RequestParam(required=false) String code) {
        Tentativa t;
        synchronized (sessao) {
            t = (Tentativa)sessao.getAttribute("meta.oauth");
            if (t == null || !t.dono.equals(usuario.getName()) || !t.state.equals(state) || !Instant.now().isBefore(t.expira))
                throw new ResponseStatusException(BAD_REQUEST);
            sessao.removeAttribute("meta.oauth");
        }
        if (code != null && !code.isBlank()) {
            String token = meta.trocar(code);
            if (!meta.valida(t.rede,token)) throw new ResponseStatusException(FORBIDDEN);
            db.update("""
                INSERT INTO conexao_social(dono,rede,token) SELECT id_usuario,?,? FROM usuario WHERE email=?
                ON CONFLICT(dono,rede) DO UPDATE SET token=excluded.token
                """,t.rede.name(),cifra().encrypt(token),t.dono);
        }
        return ResponseEntity.status(SEE_OTHER).location(URI.create("/#nova-prospeccao")).header("Referrer-Policy","no-referrer").build();
    }
    @DeleteMapping("/{rede}") @ResponseStatus(NO_CONTENT)
    void remover(Principal usuario,@PathVariable Meta.Rede rede) {
        db.update("DELETE FROM conexao_social WHERE dono=(SELECT id_usuario FROM usuario WHERE email=?) AND rede=?",usuario.getName(),rede.name());
    }
}
