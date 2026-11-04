# Chamados de laboratório

Aplicação Spring Boot para abrir, listar e resolver chamados de equipamentos pelo navegador. Os chamados são salvos no PostgreSQL.

## Execução local

Você precisa de um JDK 17 ou superior e do PostgreSQL em execução. Use o Maven se precisar gerar o JAR. Os comandos abaixo podem ser executados no Terminal do IntelliJ com PowerShell, na pasta que contém o `pom.xml`.

### Prepare o banco uma vez

Se o usuário e o banco `chamados` já estiverem configurados, siga para a próxima etapa. Caso contrário, conecte-se ao PostgreSQL como administrador. Exemplo para o PostgreSQL 18 no Windows:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h 127.0.0.1 -U postgres -d postgres -W
```

No prompt do `psql`, execute os comandos abaixo. Escolha uma senha para o usuário `chamados` quando solicitado.

```sql
CREATE ROLE chamados LOGIN;
\password chamados
CREATE DATABASE chamados OWNER chamados;
\q
```

### Inicie a aplicação

Se precisar gerar o JAR a partir do código, execute `mvn clean package`. Se a aplicação já estiver rodando, encerre-a com `Ctrl+C` antes de gerar o pacote novamente.

No PowerShell, configure a conexão e rode o JAR na mesma aba.

```powershell
$env:DB_URL = 'jdbc:postgresql://127.0.0.1:5432/chamados'
$env:DB_USER = 'chamados'
$senha = Read-Host 'Senha do usuario chamados' -AsSecureString
$env:DB_PASSWORD = [System.Net.NetworkCredential]::new('', $senha).Password
Remove-Variable senha

java -jar .\target\chamados-laboratorio-0.1.0-SNAPSHOT.jar --server.port=18081
```

Se estiver usando o pacote com a interface já gerado em `target/chamados-laboratorio-ui.jar`, use esse nome no comando `java -jar`. A aplicação cria a tabela de chamados na inicialização.

## Uso pelo navegador

Quando o terminal mostrar `Started ChamadosApplication`, abra [Chamados do laboratório](http://127.0.0.1:18081/).

1. Preencha o equipamento e a descrição e clique em **Abrir chamado**.
2. Use o filtro para ver todos os chamados, apenas os abertos ou apenas os resolvidos.
3. Clique em **Resolver** em um chamado aberto. Ele aparecerá na lista de resolvidos.

## Testes

Execute `mvn test`. Os testes de integração usam JUnit, MockMvc e H2 em memória e podem rodar sem o PostgreSQL ativo. Os relatórios do Maven Surefire ficam em `target/surefire-reports/`.

## Uso de IA

### 1º Uso — Base da aplicação

#### Prompt 1

- **Modelo** — ChatGPT (Codex).
- **Objetivo** — Criar uma API base para aplicar os conceitos de DevOps.
- **Prompt utilizado**

 > Precisamos de uma API base para aplicar os conceitos de DevOps que estão no PDF anexado criar a base da API. Pensei em criar um sistema de chamadas de reparações de equipamentos usando Java, Spring Boot, Maven e PostgreSQL, poderia criar algo assim usando as tecnologias informadas e sem aplicar os conceitos ainda.

- **Conclusão** — Toda a lógica do processo ficou bem completa, mas não havia uma interface, oque obrigava o usuário a usar o Terminal para inserir os equipamentos no banco.

#### Prompt 2

- **Modelo** — ChatGPT (Codex).
- **Objetivo** — Mudança de escopo para facilitar os chamados.
- **Prompt utilizado**

  > Vale a pena manter essa API com PostgreSQL, mas gostaria que fosse feito uma interface simples para facilitar a entrada de dados, pra simplificar o processo utilizando a base já criada.

- **Conclusão** — A interface, apesar de simples, é completa e funcional o suficiente para inserir os dados na aplicação.
