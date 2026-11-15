package br.com.urwork.dados;

import java.io.IOException;
import java.nio.file.*;
import java.sql.DriverManager;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class BancoLocalTest {
    @TempDir Path raiz;

    @Test void usaOMesmoDestinoNaRaizOuNoBackendEAceitaCaminhoExplicito() throws Exception {
        Path backend = Files.createDirectory(raiz.resolve("backend"));
        Files.createFile(backend.resolve("pom.xml"));
        Path destino = raiz.resolve("dtb/UrWork.db");
        assertEquals(destino, BancoLocal.preparar(raiz, null));
        assertEquals(destino, BancoLocal.preparar(backend, null));
        Path alternativo = raiz.resolve("outra-pasta/contas.db");
        assertEquals(alternativo, BancoLocal.preparar(backend, alternativo.toString()));
        assertTrue(Files.isDirectory(alternativo.getParent()));
    }

    @Test void copiaDadosConfirmadosNoWalESegundaInicializacaoPreservaODestino() throws Exception {
        Path antigo = Files.createDirectories(raiz.resolve("Planilhas")).resolve("zin_leads.db");
        try (var banco = DriverManager.getConnection("jdbc:sqlite:" + antigo);
             var sql = banco.createStatement()) {
            sql.execute("pragma journal_mode=WAL");
            sql.execute("create table exemplo(id integer primary key)");
            sql.execute("insert into exemplo values(1)");
            Path destino = BancoLocal.preparar(raiz, null);
            try (var novo = DriverManager.getConnection("jdbc:sqlite:" + destino);
                 var consulta = novo.createStatement();
                 var linhas = consulta.executeQuery("select id from exemplo")) {
                assertTrue(linhas.next());
                assertEquals(1, linhas.getInt(1));
                assertFalse(linhas.next());
            }
            sql.execute("insert into exemplo values(2)");
            byte[] anterior = Files.readAllBytes(destino);
            assertEquals(destino, BancoLocal.preparar(raiz, null));
            assertArrayEquals(anterior, Files.readAllBytes(destino));
        }
    }

    @Test void aceitaCopiasIguaisEInterrompeQuandoDivergem() throws Exception {
        Path primeiro = Files.createDirectories(raiz.resolve("Planilhas")).resolve("zin_leads.db");
        Path segundo = Files.createDirectories(raiz.resolve("DTB")).resolve("zin_leads.db");
        try (var banco = DriverManager.getConnection("jdbc:sqlite:" + primeiro);
             var sql = banco.createStatement()) {
            sql.execute("create table exemplo(id integer primary key)");
        }
        Files.copy(primeiro, segundo);
        Path destino = BancoLocal.preparar(raiz, null);
        assertTrue(Files.exists(destino));
        Files.delete(destino);
        try (var banco = DriverManager.getConnection("jdbc:sqlite:" + segundo);
             var sql = banco.createStatement()) {
            sql.execute("insert into exemplo values(1)");
        }
        assertThrows(IOException.class, () -> BancoLocal.preparar(raiz, null));
        assertFalse(Files.exists(destino));
        assertTrue(Files.exists(primeiro));
        assertTrue(Files.exists(segundo));
    }
}
