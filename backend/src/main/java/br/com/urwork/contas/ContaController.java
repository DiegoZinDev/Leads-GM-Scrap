package br.com.urwork.contas;

import java.security.Principal;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.dao.DataAccessException;
import org.sqlite.SQLiteException;
import org.sqlite.SQLiteErrorCode;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
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

    record Cadastro(@NotBlank @Size(max=80) String username, @NotBlank @Email @Pattern(regexp="(?i)[^@]+@(?:gmail\\.com|(?:outlook|hotmail|yahoo)\\.com(?:\\.br)?|live\\.com|icloud\\.com|(?:uol|bol|terra)\\.com\\.br)") @Size(max=254) String email,
                    @NotBlank @Size(max=8) @Pattern(regexp="(?=.*\\p{Lu})(?=.*[\\p{P}\\p{S}])(?=(?:[^0-9]*[0-9]){2}).*") String password, @Valid @NotNull DadosPerfil perfil) {}
    record Perfil(String username, String email, boolean perfilCompleto) {}
    record Protecao(String headerName, String token) {}

    @GetMapping("/csrf")
    Protecao csrf(CsrfToken csrf) { return new Protecao(csrf.getHeaderName(), csrf.getToken()); }

    @PostMapping("/cadastro")
    @ResponseStatus(HttpStatus.CREATED)
    void cadastrar(@Valid @RequestBody Cadastro dados) {
        DadosPerfil perfil = dados.perfil().validado();
        usuarios.saveAndFlush(new Usuario(dados.username().strip(), Seguranca.normalizarEmail(dados.email()),
                encoder.encode(dados.password()), perfil));
    }

    @PostMapping("/perfil")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void completarPerfil(Principal principal, @Valid @RequestBody DadosPerfil dados) {
        if (usuarios.completarPerfil(principal.getName(), dados.validado()) == 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Perfil já preenchido.");
        }
    }

    @ExceptionHandler(DataAccessException.class)
    @ResponseStatus(HttpStatus.CONFLICT)
    void conflito(DataAccessException ex) {
        if (!(ex.getMostSpecificCause() instanceof SQLiteException sqlite)
                || sqlite.getResultCode() != SQLiteErrorCode.SQLITE_CONSTRAINT_UNIQUE) throw ex;
    }

    // Erros padrão de validação podem registrar o valor rejeitado, inclusive senha e CPF.
    @ExceptionHandler({MethodArgumentNotValidException.class, HttpMessageNotReadableException.class})
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    void entradaInvalida() {}

    @GetMapping("/sessao")
    Perfil sessao(Principal principal) {
        return usuarios.findByEmail(principal.getName()).map(u -> new Perfil(u.username(), u.email(), u.perfilCompleto()))
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED));
    }
}
