package br.edu.inatel.chamados;

import java.util.List;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/chamados")
class ChamadoController {
    private final ChamadoRepository chamados;

    ChamadoController(ChamadoRepository chamados) {
        this.chamados = chamados;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    Chamado abrir(@Valid @RequestBody Abertura pedido) {
        return chamados.abrir(pedido.equipamento(), pedido.descricao());
    }

    @GetMapping
    List<Chamado> listar(@RequestParam(required = false) Chamado.Status status) {
        return chamados.listar(status);
    }

    @PatchMapping("/{id}/resolver")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void resolver(@PathVariable long id) {
        if (!chamados.resolver(id)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Chamado inexistente");
        }
    }

    record Abertura(
            @NotBlank @Size(max = 120) String equipamento,
            @NotBlank @Size(max = 1000) String descricao
    ) {}
}
