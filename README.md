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

## Notificação do pipeline por e-mail/SMTP

O Jenkins chama `scripts/notify_email.py` no bloco `post/always` global do `Jenkinsfile`, inclusive quando os testes ou o build falham. A mensagem informa resultado, job, número da build, branch, commit e links da execução e do console. O script usa somente a biblioteca padrão do Python 3.10 ou superior; Python e a ferramenta de cobertura são instalados pelo `jenkins/Dockerfile`.

O destinatário vem exclusivamente de `NOTIFY_EMAIL`. O script retorna `0` quando o servidor aceita a mensagem, `1` em falha de transporte e `2` em configuração inválida. A entrega de uma notificação sobre um pipeline `FAILURE` retorna `0`: o resultado do pipeline e o resultado do envio são informações diferentes.

Se o SMTP falhar, o Jenkins registra o erro e marca uma execução até então bem-sucedida como `UNSTABLE`. Uma execução que já estava `FAILURE` continua `FAILURE`. Senhas e respostas potencialmente sensíveis do servidor não são impressas pelo script.

### Jenkins + MailHog com Docker Compose

O arquivo `compose.smtp.yml` sobe o Jenkins e o MailHog na mesma rede, com um volume para os dados do Jenkins. Ele é um ambiente específico para validar a frente de SMTP. O Compose final do grupo deve incorporar esses serviços e incluir os demais containers exigidos pelo projeto.

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
