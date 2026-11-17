# Estoque Fácil — Sistema de Controle de Estoque

Aplicação web em Python + Flask + SQLite para autenticação, cadastro de produtos e controle de entradas e saídas.

## Funcionalidades
- Login e logout com senha armazenada em hash.
- Cadastro de produtos com código único.
- Registro de entradas e saídas com observação e usuário responsável.
- Atualização automática do saldo.
- Bloqueio de saída quando não há saldo suficiente.
- Painel com indicadores e histórico de movimentações.

## Requisitos
- Python 3.10 ou superior.

## Como executar
```bash
# 1. Crie e ative um ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Inicie a aplicação
python app.py
```
Acesse http://127.0.0.1:5000

## Primeiro acesso
- Usuário: `admin`
- Senha: `admin123`

Altere a senha inicial e defina uma `SECRET_KEY` forte antes de publicar em produção. Exemplo no PowerShell:
```powershell
$env:SECRET_KEY="uma-chave-aleatoria-e-segura"
python app.py
```

## Banco de dados
O SQLite cria automaticamente o arquivo `estoque.db` na primeira execução. As tabelas são `users`, `products` e `movements`.

## Observação de segurança
Este projeto é uma base acadêmica/educacional. Antes de uso real, implemente proteção CSRF, fluxo de troca de senha, política de sessão e configuração de produção (debug desativado, HTTPS e segredo fora do código).
