package br.edu.inatel.chamados;

public record Chamado(long id, String equipamento, String descricao, Status status) {
    public enum Status {
        ABERTO, RESOLVIDO
    }
}
