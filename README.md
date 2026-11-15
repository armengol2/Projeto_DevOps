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

## Testes e cobertura (JaCoCo)
Execute `mvn test` para rodar os testes de integração ou `mvn verify` para rodar os testes e validar a meta mínima de cobertura. Os testes usam JUnit 5, MockMvc e H2 em memória e podem rodar sem o PostgreSQL ativo.
- **Relatórios de execução (Surefire):** `target/surefire-reports/`
- **Relatórios de cobertura (JaCoCo):** `target/site/jacoco/index.html` (HTML), `target/site/jacoco/jacoco.xml` (XML) e `target/site/jacoco/jacoco.csv` (CSV).
### Métrica de cobertura definida
A verificação de cobertura foi configurada no `pom.xml` com o `jacoco-maven-plugin` (`0.8.12`), avaliando o pacote completo da aplicação (`element = BUNDLE`) com duas métricas (`value = COVEREDRATIO`):
1. **Cobertura de Linhas (`counter = LINE`) — mínimo de 90% (`0.90`):** proporção de linhas executáveis do código-fonte percorridas pelos testes.
2. **Cobertura de Ramificações (`counter = BRANCH`) — mínimo de 90% (`0.90`):** proporção de desvios condicionais (`if`/`else` e expressões booleanas) avaliados tanto no caminho verdadeiro quanto no falso.
Na fase `verify` (`mvn verify`), o goal `jacoco:check` valida essas métricas e faz o build falhar (`BUILD FAILURE`) caso qualquer uma fique abaixo de **90%**. Com os 8 testes de `ChamadoApiTest`, a aplicação atinge **93,9% de cobertura de linhas** (100% em `Chamado`, `ChamadoController` e `ChamadoRepository`) e **100% de cobertura de ramificações (`BRANCH`)**.
## Imagem Docker (Docker Hub)

Imagem da API: https://hub.docker.com/r/otaviosilva389/chamados-api

```bash
# Gerar a imagem localmente
docker build -t otaviosilva389/chamados-api:0.1.0 -t otaviosilva389/chamados-api:latest .

# Publicar no Docker Hub
docker login
docker push otaviosilva389/chamados-api:0.1.0
docker push otaviosilva389/chamados-api:latest
```

A imagem usa build em dois estágios (Maven + JDK para compilar, JRE Alpine para executar) e roda com usuário não-root.
A conexão com o banco é configurada pelas variáveis `DB_URL`, `DB_USER` e `DB_PASSWORD`.

Exemplo de execução (precisa de um PostgreSQL acessível):

```bash
docker run -p 8080:8080 \
  -e DB_URL=jdbc:postgresql://host:5432/chamados \
  -e DB_USER=chamados -e DB_PASSWORD=sua_senha \
  otaviosilva389/chamados-api:0.1.0
```

## Notificação do pipeline por e-mail/SMTP

O Jenkins chama `scripts/notify_email.py` no bloco `post/always` global do `Jenkinsfile`, inclusive quando os testes ou o build falham. A mensagem informa resultado, job, número da build, branch, commit e links da execução e do console. O script usa somente a biblioteca padrão do Python 3.10 ou superior; Python e a ferramenta de cobertura são instalados pelo `jenkins/Dockerfile`.

O destinatário vem exclusivamente de `NOTIFY_EMAIL`. O script retorna `0` quando o servidor aceita a mensagem, `1` em falha de transporte e `2` em configuração inválida. A entrega de uma notificação sobre um pipeline `FAILURE` retorna `0`: o resultado do pipeline e o resultado do envio são informações diferentes.

Se o SMTP falhar, o Jenkins registra o erro e marca uma execução até então bem-sucedida como `UNSTABLE`. Uma execução que já estava `FAILURE` continua `FAILURE`. Senhas e respostas potencialmente sensíveis do servidor não são impressas pelo script.

### Jenkins + MailHog com Docker Compose

O arquivo `compose.smtp.yml` sobe o Jenkins e o MailHog na mesma rede, com um volume para os dados do Jenkins. Ele é um ambiente específico para validar a frente de SMTP. O `compose.yaml` da raiz incorpora esses serviços e inclui API e PostgreSQL; o `compose.smtp.yml` permanece como ambiente isolado só para validar a notificação por e-mail. Os dois usam as mesmas portas (18080, 8025 e 1025), então não suba os dois ao mesmo tempo.

No PowerShell, na raiz do repositório:

```powershell
Copy-Item .env.smtp.example .env.smtp
# Edite .env.smtp para definir NOTIFY_EMAIL e SMTP_FROM.
docker compose --env-file .env.smtp -f compose.smtp.yml up -d --build
docker compose --env-file .env.smtp -f compose.smtp.yml logs -f jenkins
```

O Jenkins fica em [localhost:18080](http://localhost:18080/) e a caixa de entrada do MailHog em [localhost:8025](http://localhost:8025/). No primeiro acesso, conclua o desbloqueio do Jenkins com a senha inicial:

```powershell
docker compose --env-file .env.smtp -f compose.smtp.yml exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Crie um job **Pipeline from SCM**, aponte para este repositório e para a branch que contém esta implementação e use `Jenkinsfile` como script. As etapas são todas versionadas no arquivo. Esta contribuição parte da branch `feature/jenkins-pipeline`; enquanto estiver apenas local, o checkout remoto ainda não consegue lê-la. Após a integração na `main`, use a `main` no job.

O estágio `Testes SMTP` executa os testes Python e exige cobertura de pelo menos 90%, incluindo ramificações, para o código em `scripts/`. No Compose de SMTP, o estágio também executa os testes reais contra o MailHog e confere as mensagens recebidas via API. Os relatórios `reports/smtp-tests.log` e `reports/smtp-coverage.xml` são arquivados no Jenkins mesmo quando os testes falham, junto aos relatórios Java e ao JAR das etapas seguintes quando disponíveis. Essa medição cobre o script SMTP; a cobertura da aplicação Java deve ser tratada pela frente de testes do grupo.

Dentro da rede Docker, o Jenkins usa `mailhog:1025`. Para um script executado diretamente no Windows, use `127.0.0.1:1025`. O MailHog captura as mensagens localmente: ver uma mensagem nele comprova o envio SMTP para o servidor de teste, e não a entrega à caixa de entrada de um provedor externo.

Para encerrar os serviços sem apagar o volume do Jenkins:

```powershell
docker compose --env-file .env.smtp -f compose.smtp.yml down
```

### Variáveis de ambiente do script

| Variável | Uso |
| --- | --- |
| `NOTIFY_EMAIL` | Obrigatória. Um único destinatário, sem nome de exibição. |
| `SMTP_FROM` | Obrigatória. Endereço do remetente, sem nome de exibição. |
| `SMTP_HOST` | Obrigatória. Nome do servidor SMTP. |
| `SMTP_PORT` | Porta do servidor; padrão `1025`. |
| `SMTP_SECURITY` | `none` (padrão para MailHog), `starttls` ou `ssl`. |
| `SMTP_TIMEOUT` | Tempo limite em segundos, positivo; padrão `10`. |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Opcionais. Se usados, ambos devem ser definidos. |
| `BUILD_STATUS` | Resultado informado pelo Jenkins; fora dele, padrão `UNKNOWN`. |
| `JOB_NAME`, `BUILD_NUMBER`, `BUILD_URL` | Identificação da execução; fornecida automaticamente pelo Jenkins. |
| `BRANCH_NAME` / `GIT_BRANCH`, `GIT_COMMIT` | Dados do código usado na execução, quando disponíveis. |

Para um servidor SMTP externo, configure o host, a porta e a segurança exigidos por esse servidor e mantenha as credenciais fora do Git. O arquivo `.env.smtp` é ignorado pelo repositório; apenas o exemplo com endereços fictícios é versionado.

### Testar sem Jenkins

Os testes unitários não precisam de Docker nem de um servidor SMTP:

```powershell
python -m unittest discover -s tests -v
```

Para ativar os testes reais de integração, inicie somente o MailHog e execute:

```powershell
docker compose --env-file .env.smtp.example -f compose.smtp.yml up -d mailhog
$env:RUN_MAILHOG_TESTS = '1'
$env:MAILHOG_SMTP_HOST = '127.0.0.1'
$env:MAILHOG_API_URL = 'http://127.0.0.1:8025'
python -m unittest discover -s tests -v
Remove-Item Env:RUN_MAILHOG_TESTS
```

Os testes de integração enviam mensagens identificadas por um nome de job aleatório e verificam notificações `SUCCESS` e `FAILURE`. Não removem outras mensagens do MailHog. As variáveis `MAILHOG_SMTP_HOST`, `MAILHOG_SMTP_PORT` e `MAILHOG_API_URL` permitem mudar os endereços do servidor de teste.

Exemplo de envio manual para o MailHog já ativo:

```powershell
$env:NOTIFY_EMAIL = 'destinatario@example.test'
$env:SMTP_FROM = 'jenkins@example.test'
$env:SMTP_HOST = '127.0.0.1'
$env:SMTP_PORT = '1025'
$env:BUILD_STATUS = 'SUCCESS'
$env:JOB_NAME = 'chamados-ci-local'
$env:BUILD_NUMBER = '1'
python scripts/notify_email.py
```

### Validação realizada em 11/11/2026

- 27 testes SMTP aprovados, incluindo o envio e a leitura de mensagens reais no MailHog.
- Cobertura do script: 98,2% das linhas e 94,6% das ramificações (97% no relatório combinado).
- 4 testes Java aprovados e JAR gerado na execução bem-sucedida do Jenkins.
- Execução real com Jenkins 2.580.2, Java 21, Python 3.13 e MailHog 1.0.1 em containers; testes também executados com Python 3.12 no Windows.

| Cenário no Jenkins | Resultado verificado |
| --- | --- |
| Testes e build aprovados | `SUCCESS`; mensagem recebida, com branch e commit, JAR e relatórios arquivados. |
| Teste Java falhando | `FAILURE`; mensagem de falha recebida e relatórios arquivados. |
| Build aprovado e SMTP indisponível | `UNSTABLE`; falha de envio registrada no console. |
| Teste Java falhando e SMTP indisponível | `FAILURE` preservado; falha de envio registrada no console. |
| Teste SMTP falhando | `FAILURE`; mensagem de falha recebida e logs dos testes SMTP arquivados. |

As falhas foram provocadas em cópias temporárias para validar o tratamento de erros; não fazem parte dos testes entregues. O ambiente temporário de validação foi separado da configuração normal do Compose.

## Ambiente completo com Docker Compose

O `compose.yaml` sobe a API, o PostgreSQL, o Jenkins e o MailHog. A API usa a imagem publicada no Docker Hub (`otaviosilva389/chamados-api:0.1.0`) e o Jenkins é construído pelo `jenkins/Dockerfile` local. Não é necessário criar `.env`: todos os valores têm padrão no próprio arquivo.

```powershell
docker compose up -d --build
docker compose ps
```

| Serviço | Endereço | Observação |
| --- | --- | --- |
| API | [localhost:18081](http://localhost:18081/) | Conecta ao PostgreSQL pelas variáveis `DB_URL`, `DB_USER` e `DB_PASSWORD`. |
| Jenkins | [localhost:18080](http://localhost:18080/) | SMTP configurado para `mailhog:1025`. |
| MailHog | [localhost:8025](http://localhost:8025/) | Interface web; SMTP na porta 1025. |
| PostgreSQL | rede interna | Não exposto ao host. |

Os dados ficam nos volumes `postgres_data` e `jenkins_home`. Para encerrar sem apagá-los, use `docker compose down`; para apagá-los, `docker compose down -v`. Os valores podem ser sobrescritos por variáveis de ambiente ou por um `.env` opcional (`POSTGRES_PASSWORD`, `API_IMAGE`, `NOTIFY_EMAIL`, entre outras).

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

### 2º Uso — Notificação SMTP e integração com Jenkins/MailHog

#### Prompt 3

- **Modelo/ferramenta** — ChatGPT (Codex; versão do modelo não registrada).
- **Objetivo** — Implementar a frente de notificação por e-mail atribuída a Vinícius.
- **Prompt utilizado**

  > ok, implemente minha parte de notificação por e-mail/SMTP, com os testes e a integração com Jenkins e MailHog

- **Resposta aceita** — Script Python com configuração por ambiente, testes unitários e de integração, chamada no encerramento do Jenkinsfile e ambiente Docker Compose de SMTP.
- **Ajustes durante a validação** — Tratamento dos erros de formato de endereço, proteção contra injeção de cabeçalhos, uso do domínio do remetente no Message-ID para aceitar máquinas com hostname acentuado e captura explícita da branch e do commit retornados pelo checkout do Jenkins. O arquivo Compose foi mantido específico para a frente de SMTP para permitir integração com o trabalho dos demais membros.
- **Dinâmica de uso** — Assistência nesta conversa para analisar o repositório, gerar código, revisar configurações, executar testes e documentar a contribuição. Não foi registrado pair programming entre integrantes nessa etapa.
- **Autoria e entendimento** — O escopo e a divisão de responsabilidades foram fornecidos pelo integrante. O código desta contribuição foi produzido com assistência de IA; não há registro de trechos escritos manualmente pelo integrante nesta etapa. Cada integrante deve revisar e compreender os arquivos antes da defesa. A aplicação base e a contribuição inicial de Jenkins mantêm suas autorias registradas no histórico do Git.

### 3º Uso — Dockerfile da API e publicação no Docker Hub

#### Prompt 4

- **Modelo** — Claude (Anthropic), pelo claude.ai.
- **Objetivo** — Criar o Dockerfile da API, gerar a imagem, publicar no Docker Hub e documentar o link no README.
- **Prompt utilizado**

  > Criar o Dockerfile da API, gerar a imagem a partir dele, publicar uma versão identificada por tag no Docker Hub e registrar o link no README.

  O prompt foi enviado junto com o PDF do projeto e o zip do repositório.

- **Resposta recebida** — Dockerfile multi-stage (Maven + JDK 17 para compilar, JRE 17 Alpine para executar, usuário não-root), `.dockerignore` e um rascunho da seção do README.
- **Aceito, ajustado ou descartado** — O Dockerfile e o `.dockerignore` foram aceitos como gerados. O rascunho do README foi ajustado com o usuário real do Docker Hub (`otaviosilva389`) e a tag publicada.
- **Validação** — Build local da imagem, push das tags `0.1.0` e `latest` e teste manual com um container PostgreSQL na mesma rede Docker. A API subiu, conectou ao banco e a interface funcionou.

#### Dinâmica de uso e autoria

- A IA foi usada individualmente, em conversa passo a passo, também para orientar o fluxo de Git (branch, commits e PR).
- Feito pelo integrante, sem IA: criar a conta e o repositório no Docker Hub, executar o build, o login e o push, e testar a imagem com PostgreSQL.
- Gerado pela IA: o conteúdo do Dockerfile, do `.dockerignore` e o texto-base da seção do README.

### 4º Uso — Docker Compose

#### Prompt 5

- **Modelo** — Claude (Anthropic), pelo claude.ai.
- **Objetivo** — Criar o `compose.yaml` com API, PostgreSQL, Jenkins e MailHog, com as conexões e os volumes.
- **Prompt utilizado**

  > Preciso de ajuda para criar o `compose.yaml` com API, PostgreSQL, Jenkins e MailHog. Segue o zip do repositório.

  O prompt foi enviado junto com o zip do repositório.

- **Resposta recebida** — `compose.yaml` com healthchecks, volumes e variáveis de conexão da API ao PostgreSQL e do Jenkins ao MailHog, além de instruções de teste.
- **Aceito, ajustado ou descartado** — Ajustado a pedido do integrante: valores padrão dentro do `compose.yaml`, para o ambiente subir sem `.env`; imagem da API trocada pela tag publicada pelo Otavio.
- **Validação** — Feita pelo integrante: subida dos 4 containers, chamado criado pela API e mantido após `docker compose down` e `up`, e execução do pipeline no Jenkins do Compose, a partir de um repositório de teste, com o e-mail recebido no MailHog.

### 5º Uso — Testes e cobertura com JaCoCo
#### Prompt 6
- **Modelo** — Gemini (Google).
- **Objetivo** — Revisar a configuração das execuções do plugin `jacoco-maven-plugin` no `pom.xml` para falhar abaixo de 90% no `mvn verify` e verificar cenários de borda nos testes de integração da API.
- **Prompt utilizado**
  > Analise a classe `ChamadoController` e o `ChamadoApiTest` atual. Quais cenários de validação das anotações `@NotBlank` e `@Size` ainda não estão cobertos pelos quatro testes existentes e como configurar os goals `prepare-agent`, `report` e `check` do JaCoCo no `pom.xml` para exigir mínimo de 90% no `mvn verify`?
- **Resposta recebida** — Sugestão de casos de teste para as validações de `equipamento` e limites de tamanho (`@Size`), além da estrutura XML das execuções do `jacoco-maven-plugin` com `element = BUNDLE`.
- **Aceito, ajustado ou descartado** — A configuração base do plugin JaCoCo foi aceita e ajustada para validar simultaneamente as métricas `LINE` e `BRANCH` com mínimo de `0.90`, garantindo a geração do relatório tanto em `mvn test` quanto em `mvn verify`. Os testes foram implementados mantendo os quatro testes originais do repositório e adicionando os casos de rejeição para `equipamento` em branco, limites de 120 e 1000 caracteres e payload vazio.
- **Validação** — Feita pelo integrante: execução de `mvn clean verify` confirmando a aprovação dos 8 testes de integração com H2 em memória, inspeção do relatório em `target/site/jacoco/index.html` (93,9% de linhas e 100% de branches) e simulação de cobertura insuficiente para confirmar o `BUILD FAILURE` no `verify`.