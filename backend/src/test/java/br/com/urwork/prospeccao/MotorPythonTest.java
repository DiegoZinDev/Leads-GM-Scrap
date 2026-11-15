package br.com.urwork.prospeccao;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class MotorPythonTest {
    private MotorPython motor(String... argumentos) {
        var cmd = new ArrayList<>(List.of("-m", "engine.tests.worker_controlado"));
        cmd.addAll(List.of(argumentos));
        return new MotorPython(new ObjectMapper(), MotorPython.raizProjeto(), cmd);
    }

    @Test void processoRealRespeitaMetaComFonteControlada() throws Exception {
        var motor = motor();
        var eventos = new ArrayList<JsonNode>();
        var pedido = new MotorPython.Pedido("Saúde", "Campinas - SP", 36);
        assertEquals(36, motor.executar(pedido, eventos::add));
        assertEquals(38, eventos.size());
        assertEquals("inicio", eventos.getFirst().path("tipo").asText());
        assertEquals("Clínica", eventos.get(36).path("lead").path("nome").asText());
        assertEquals("fim", eventos.getLast().path("tipo").asText());
    }

    @Test void esgotamentoConcluiAbaixoDaMetaERecusaColetaSobreposta() throws Exception {
        var motor = motor();
        var pedido = new MotorPython.Pedido("Sem resultados", "Vitória - ES", 3);
        var tipos = new ArrayList<String>();
        assertEquals(0, motor.executar(pedido, evento -> {
            tipos.add(evento.path("tipo").asText());
            if (tipos.size() == 1)
                assertThrows(IllegalStateException.class, () -> motor.executar(pedido, ignorado -> {}));
        }));
        assertEquals(List.of("inicio", "fim"), tipos);
    }

    @Test void falhaAposFimNaoConfirmaConclusaoELiberaMotor() {
        var motor = motor("--falhar");
        for (int tentativa = 0; tentativa < 2; tentativa++) {
            var tipos = new ArrayList<String>();
            assertThrows(IOException.class, () -> motor.executar(new MotorPython.Pedido("Sem resultados", "Vitória - ES", 1),
                    evento -> tipos.add(evento.path("tipo").asText())));
            assertEquals(List.of("inicio"), tipos);
        }
    }
}
