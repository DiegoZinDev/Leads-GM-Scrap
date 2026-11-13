package br.com.zin;

import java.util.Locale;
import org.springframework.context.annotation.*;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.*;
import org.springframework.security.crypto.password.*;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
class Seguranca {
    static String normalizarEmail(String email) { return email.strip().toLowerCase(Locale.ROOT); }

    @Bean PasswordEncoder passwordEncoder() {
        return Pbkdf2PasswordEncoder.defaultsForSpringSecurity_v5_8();
    }

    @Bean UserDetailsService userDetailsService(Usuarios usuarios) {
        return email -> usuarios.findByEmail(normalizarEmail(email))
            .map(u -> User.withUsername(u.email()).password(u.senha()).roles("USER").build())
            .orElseThrow(() -> new UsernameNotFoundException("Credenciais inválidas"));
    }

    @Bean SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http.authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/csrf", "/api/auth/cadastro", "/api/auth/login").permitAll()
                .requestMatchers("/api/**").authenticated().anyRequest().permitAll())
            .requestCache(cache -> cache.disable())
            .exceptionHandling(errors -> errors.authenticationEntryPoint((req,res,ex) -> res.setStatus(401)))
            .formLogin(login -> login.loginProcessingUrl("/api/auth/login").usernameParameter("email")
                .successHandler((req,res,auth) -> res.setStatus(204))
                .failureHandler((req,res,ex) -> res.setStatus(401)))
            .logout(logout -> logout.logoutUrl("/api/auth/logout").deleteCookies("JSESSIONID")
                .logoutSuccessHandler((req,res,auth) -> res.setStatus(204)))
            .build();
    }
}
