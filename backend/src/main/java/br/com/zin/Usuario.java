package br.com.zin;

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

    protected Usuario() {}
    Usuario(String username, String email, String senha) {
        this.username = username;
        this.email = email;
        this.senha = senha;
    }

    String username() { return username; }
    String email() { return email; }
    String senha() { return senha; }
}
