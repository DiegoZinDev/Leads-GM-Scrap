package br.com.zin;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

interface Usuarios extends JpaRepository<Usuario, Long> {
    Optional<Usuario> findByEmail(String email);
}
