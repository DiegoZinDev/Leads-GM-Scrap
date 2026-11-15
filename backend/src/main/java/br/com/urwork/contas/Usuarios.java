package br.com.urwork.contas;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.transaction.annotation.Transactional;

interface Usuarios extends JpaRepository<Usuario, Long> {
    Optional<Usuario> findByEmail(String email);

    @Transactional
    @Modifying
    @Query("update Usuario u set u.perfil = :perfil where u.email = :email and u.perfil.cpf is null")
    int completarPerfil(String email, DadosPerfil perfil);
}
