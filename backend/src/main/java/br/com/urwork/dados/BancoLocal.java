package br.com.urwork.dados;

import java.io.IOException;
import java.nio.file.*;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.List;
import org.sqlite.SQLiteConnection;

public final class BancoLocal {
    public static Path preparar(Path local, String override) throws IOException, SQLException {
        Path raiz = local.endsWith("backend") && Files.isRegularFile(local.resolve("pom.xml"))
            ? local.getParent() : local;
        Path padrao = raiz.resolve("dtb/UrWork.db");
        Path destino = override == null ? padrao : local.resolve(override).normalize();
        Files.createDirectories(destino.getParent());
        if (!destino.equals(padrao) || Files.exists(destino)) return destino;

        Path primeiraCopia = null;
        try {
            for (String antigo : List.of("Planilhas/zin_leads.db", "DTB/zin_leads.db",
                    "dtb/zin_leads.db", "backend/Planilhas/zin_leads.db")) {
                Path origem = raiz.resolve(antigo);
                if (Files.notExists(origem)) continue;
                Path copia = Files.createTempFile(destino.getParent(), ".migracao-", ".db");
                try {
                    copiarBanco(origem, copia);
                    if (primeiraCopia == null) {
                        primeiraCopia = copia;
                    } else if (Files.mismatch(primeiraCopia, copia) != -1) {
                        throw new IOException("Os bancos antigos divergem. Selecione o banco correto com "
                            + "URWORK_DB_PATH antes de iniciar o UrWork.");
                    }
                } finally {
                    if (!copia.equals(primeiraCopia)) Files.deleteIfExists(copia);
                }
            }
            if (primeiraCopia != null) Files.move(primeiraCopia, destino);
        } finally {
            if (primeiraCopia != null) Files.deleteIfExists(primeiraCopia);
        }
        return destino;
    }

    private static void copiarBanco(Path origem, Path copia) throws IOException, SQLException {
        // A API de backup inclui transações confirmadas que ainda estão no WAL.
        String url = "jdbc:sqlite:" + origem.toUri().toASCIIString() + "?mode=ro";
        try (var conexao = DriverManager.getConnection(url)) {
            int resultado = conexao.unwrap(SQLiteConnection.class).getDatabase()
                .backup("main", copia.toString(), null);
            if (resultado != 0) throw new IOException("Backup SQLite falhou para " + origem);
        }
    }
}
