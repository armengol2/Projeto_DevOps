package br.edu.inatel.chamados;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ChamadoApiTest {
    @Autowired
    MockMvc api;

    @Autowired
    ObjectMapper json;

    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void limparChamados() {
        jdbc.sql("DELETE FROM chamados").update();
    }

    @Test
    void abreListaEResolveChamado() throws Exception {
        var resposta = api.perform(post("/chamados")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"equipamento":"Osciloscopio","descricao":"Tela apagada"}
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value("ABERTO"))
                .andReturn();
        long id = json.readTree(resposta.getResponse().getContentAsString()).get("id").asLong();

        api.perform(get("/chamados"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(id))
                .andExpect(jsonPath("$[0].equipamento").value("Osciloscopio"))
                .andExpect(jsonPath("$[0].descricao").value("Tela apagada"));

        api.perform(get("/chamados").param("status", "ABERTO"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(id));

        api.perform(patch("/chamados/{id}/resolver", id))
                .andExpect(status().isNoContent());
        api.perform(patch("/chamados/{id}/resolver", id))
                .andExpect(status().isNoContent());

        api.perform(get("/chamados").param("status", "ABERTO"))
                .andExpect(status().isOk())
                .andExpect(content().json("[]"));
        api.perform(get("/chamados").param("status", "RESOLVIDO"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(id))
                .andExpect(jsonPath("$[0].status").value("RESOLVIDO"));
    }

    @Test
    void rejeitaChamadoComDescricaoEmBranco() throws Exception {
        api.perform(post("/chamados")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"equipamento":"Osciloscopio","descricao":" "}
                                """))
                .andExpect(status().isBadRequest());
        api.perform(get("/chamados"))
                .andExpect(content().json("[]"));
    }

    @Test
    void rejeitaFiltroInvalido() throws Exception {
        api.perform(get("/chamados").param("status", "PENDENTE"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void retorna404AoResolverChamadoInexistente() throws Exception {
        api.perform(patch("/chamados/{id}/resolver", 999))
                .andExpect(status().isNotFound());
    }
}
