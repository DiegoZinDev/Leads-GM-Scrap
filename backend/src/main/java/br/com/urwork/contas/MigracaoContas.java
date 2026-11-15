package br.com.urwork.contas;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.HashSet;
import java.util.Set;
import javax.sql.DataSource;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.boot.sql.init.dependency.DependsOnDatabaseInitialization;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.init.ScriptUtils;
import org.springframework.stereotype.Component;

@Component
@DependsOnDatabaseInitialization
class MigracaoContas implements InitializingBean {
    private final DataSource dataSource;

    MigracaoContas(DataSource dataSource) { this.dataSource = dataSource; }

    @Override
    public void afterPropertiesSet() throws SQLException {
        try (var connection = dataSource.getConnection(); var sql = connection.createStatement()) {
            sql.execute("BEGIN IMMEDIATE");
            try {
                migrar(connection, sql);
                sql.execute("COMMIT");
            } catch (SQLException | RuntimeException ex) {
                sql.execute("ROLLBACK");
                throw ex;
            }
        }
    }

    private static void migrar(Connection connection, Statement sql) throws SQLException {
        var colunas = new HashSet<String>();
        try (var result = sql.executeQuery("SELECT name FROM pragma_table_info('usuario')")) {
            while (result.next()) colunas.add(result.getString(1));
        }
        if (colunas.contains("cpf")) return;
        if (!colunas.equals(Set.of("id_usuario", "username", "email", "senha", "token"))) {
            throw new SQLException("Tabela usuario desconhecida. Revise o esquema antes de migrar.");
        }

        // Renomear a tabela alteraria referências em extensões que não existiam no esquema Zin.
        try (var ext = sql.executeQuery("""
                SELECT name FROM sqlite_schema
                WHERE (tbl_name='usuario' AND type IN ('index','trigger') AND sql IS NOT NULL)
                   OR (type IN ('view','trigger') AND lower(sql) LIKE '%usuario%')
                UNION ALL
                SELECT s.name FROM sqlite_schema s, pragma_foreign_key_list(s.name) fk
                WHERE s.type='table' AND lower(fk."table")='usuario'
                """)) {
            if (ext.next()) throw new SQLException("A tabela usuario tem dependências locais. Revise antes de migrar.");
        }
        sql.execute("ALTER TABLE usuario RENAME TO usuario_zin_anterior");
        ScriptUtils.executeSqlScript(connection, new ClassPathResource("schema.sql"));
        sql.execute("""
                INSERT INTO usuario (id_usuario, username, email, senha, token)
                SELECT id_usuario, username, email, senha, token FROM usuario_zin_anterior
                """);
        sql.execute("DROP TABLE usuario_zin_anterior");
    }
}
