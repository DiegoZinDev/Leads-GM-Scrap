package br.com.zin;

import java.security.Principal;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.dao.DataAccessException;
import org.sqlite.SQLiteException;
import org.sqlite.SQLiteErrorCode;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/auth")
class ContaController {
    private final Usuarios usuarios;
    private final PasswordEncoder encoder;
    ContaController(Usuarios usuarios, PasswordEncoder encoder) {
        this.usuarios = usuarios;
        this.encoder = encoder;
    }

    record Cadastro(@NotBlank @Size(max=80) String username, @NotBlank @Email @Size(max=254) String email,
                    @NotBlank @Size(min=8,max=128) String password) {}
    record Perfil(String username, String email) {}
    record Protecao(String headerName, String token) {}

    @GetMapping("/csrf")
    Protecao csrf(CsrfToken csrf) { return new Protecao(csrf.getHeaderName(), csrf.getToken()); }

    @PostMapping("/cadastro")
    @ResponseStatus(HttpStatus.CREATED)
    void cadastrar(@Valid @RequestBody Cadastro dados) {
        Usuario usuario = new Usuario(dados.username().strip(), Seguranca.normalizarEmail(dados.email()),
                                      encoder.encode(dados.password()));
        try {
            usuarios.saveAndFlush(usuario);
        } catch (DataAccessException ex) {
            if (!(ex.getMostSpecificCause() instanceof SQLiteException sqlite)
                    || sqlite.getResultCode() != SQLiteErrorCode.SQLITE_CONSTRAINT_UNIQUE) {
                throw ex;
            }
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Nome de usuário ou e-mail indisponível", ex);
        }
    }

    @GetMapping("/sessao")
    Perfil sessao(Principal principal) {
        return usuarios.findByEmail(principal.getName()).map(u -> new Perfil(u.username(), u.email()))
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED));
    }
}
