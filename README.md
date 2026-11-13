# Union Safety – Alerta de vencimento de CA (MVP)

Protótipo funcional desenvolvido na Experiência Prática 1 de Projeto de Software (Análise e Desenvolvimento de Sistemas).

## O problema

A Union Safety Equipamentos de Segurança vende EPIs. Cada EPI precisa de um Certificado de Aprovação (CA) válido, e hoje a conferência da validade é feita manualmente, um CA por vez. O MVP automatiza essa conferência.

## O que o sistema faz

Importa a planilha de produtos exportada do Bling, extrai o número do CA que aparece no final da descrição de cada produto, consulta a validade na base oficial de CAs do Ministério do Trabalho e Emprego (CAEPI) e mostra um painel com a situação de cada produto:

- Vencido
- Vence em até 30 dias
- Vence em até 90 dias
- Regular
- Sem CA (inclui CA não localizado na base carregada)

O painel tem busca, filtro por situação e ordenação por urgência.

## Segurança e acessibilidade

- Login obrigatório em todas as telas, com bloqueio temporário após 5 tentativas erradas
- Sessão expira após 30 minutos sem uso
- Senhas guardadas com hash, proteção CSRF em todos os formulários, cabeçalhos de segurança e CSP
- Validação do arquivo enviado no servidor e mensagens de erro genéricas
- Cada situação é indicada por texto, símbolo e cor (nunca só pela cor), campos com rótulo visível e área de clique mínima de 44 px

## Tecnologias

Python, Flask, SQLAlchemy, SQLite, Waitress.

## Como rodar (Windows, PowerShell)

1. Instale o Python (python.org), marcando "Add python.exe to PATH".
2. Na pasta do projeto, crie e ative o ambiente virtual:

       python -m venv venv
       .\venv\Scripts\Activate.ps1

   Se o PowerShell bloquear a ativação:

       Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

3. Instale as dependências:

       pip install -r requirements.txt

4. Crie um usuário de teste (use dados fictícios):

       python criar_usuario.py

5. Gere as planilhas fictícias de demonstração (pasta demo/):

       python gerar_demo.py

6. Inicie o sistema:

       python run.py

7. Abra http://127.0.0.1:5000 no navegador e entre com o usuário criado.

Defina uma chave fixa para a sessão antes de iniciar, para as sessões não caírem a cada reinício:

    $env:SECRET_KEY = "uma-frase-longa-e-secreta"

## Como usar

1. Em Importar planilha, na etapa "Base de CAs", envie `demo/base_ca_demo.csv`.
2. Na etapa "Planilha de produtos", envie `demo/produtos_demo.csv`.
3. Abra o painel de CAs para ver os alertas.
4. Para testar a recusa de arquivo inválido, envie `demo/relatorio_falso.csv`.

## Dados

Os arquivos da pasta `demo/` são totalmente fictícios. As planilhas reais (exportação do Bling e base do CAEPI) e o banco de dados não são versionados, conforme o `.gitignore`.

## Limitações do protótipo

- Aviso por e-mail e correção manual da validade não foram implementados.
- A trava de login por tentativas fica em memória e zera quando o sistema reinicia.
- O contraste das cores foi calculado, mas ainda não medido com ferramenta no navegador.