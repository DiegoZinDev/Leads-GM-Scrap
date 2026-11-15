package br.com.urwork;

import br.com.urwork.dados.BancoLocal;
import java.nio.file.Path;
import java.util.Map;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.core.env.MapPropertySource;

@SpringBootApplication
public class UrWorkApplication {
    public static void main(String[] args) {
        var app = new SpringApplication(UrWorkApplication.class);
        app.addInitializers(context -> {
            var environment = context.getEnvironment();
            if (environment.containsProperty("spring.datasource.url")) return;
            String override = environment.getProperty("URWORK_DB_PATH", environment.getProperty("ZIN_DB_PATH"));
            try {
                Path database = BancoLocal.preparar(Path.of("").toAbsolutePath(), override);
                String url = "jdbc:sqlite:" + database.toUri().toASCIIString() + "?busy_timeout=5000";
                environment.getPropertySources().addLast(new MapPropertySource("bancoLocal",
                    Map.of("spring.datasource.url", url)));
            } catch (java.io.IOException | java.sql.SQLException ex) {
                throw new IllegalStateException("Falha ao preparar o banco do UrWork.", ex);
            }
        });
        app.run(args);
    }
}
