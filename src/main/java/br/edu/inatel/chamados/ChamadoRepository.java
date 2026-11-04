package br.edu.inatel.chamados;

import java.util.List;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.stereotype.Repository;

@Repository
class ChamadoRepository {
    private final JdbcClient jdbc;

    ChamadoRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    Chamado abrir(String equipamento, String descricao) {
        var chave = new GeneratedKeyHolder();
        jdbc.sql("""
                INSERT INTO chamados (equipamento, descricao, status)
                VALUES (:equipamento, :descricao, 'ABERTO')
                """)
                .param("equipamento", equipamento)
                .param("descricao", descricao)
                .update(chave, "id");
        return new Chamado(chave.getKey().longValue(), equipamento, descricao, Chamado.Status.ABERTO);
    }

    List<Chamado> listar(Chamado.Status status) {
        if (status == null) {
            return jdbc.sql("SELECT id, equipamento, descricao, status FROM chamados ORDER BY id")
                    .query(Chamado.class).list();
        }

        return jdbc.sql("""
                SELECT id, equipamento, descricao, status FROM chamados
                WHERE status = :status ORDER BY id
                """)
                .param("status", status.name())
                .query(Chamado.class).list();
    }

    boolean resolver(long id) {
        return jdbc.sql("UPDATE chamados SET status = 'RESOLVIDO' WHERE id = :id")
                .param("id", id)
                .update() > 0;
    }
}
