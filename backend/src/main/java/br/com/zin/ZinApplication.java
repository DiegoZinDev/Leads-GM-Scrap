package br.com.zin;

import java.nio.file.Files;
import java.nio.file.Path;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class ZinApplication {
    public static void main(String[] args) throws Exception {
        Path database = Path.of(System.getenv().getOrDefault("ZIN_DB_PATH", "Planilhas/zin_leads.db"));
        Files.createDirectories(database.toAbsolutePath().getParent());
        SpringApplication.run(ZinApplication.class, args);
    }
}
