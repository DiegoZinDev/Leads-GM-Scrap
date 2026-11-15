package br.com.urwork.contas;

import jakarta.persistence.*;

@Entity
@Table(name = "usuario")
class Usuario {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id_usuario")
    private Long id;

    private String username;
    private String email;
    private String senha;
    private String token;
    @Embedded private DadosPerfil perfil;

    protected Usuario() {}
    Usuario(String username, String email, String senha, DadosPerfil perfil) {
        this.username = username;
        this.email = email;
        this.senha = senha;
        this.perfil = perfil;
    }

    String username() { return username; }
    String email() { return email; }
    String senha() { return senha; }
    boolean perfilCompleto() { return perfil != null && perfil.cpf() != null; }
}
