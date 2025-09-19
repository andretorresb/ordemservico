# Ordem de Serviço (Django + Firebird)

Aplicação Django minimalista para abrir, listar, editar e cancelar Ordens de Serviço (OS) usando um banco Firebird.
O projeto faz acesso direto ao Firebird (sem ORM) via helpers em `os_app/firebird_ops_simple.py`.

---

## Conteúdo

- Sobre
- Requisitos
- Instalação (dev)
- Configuração (Firebird / settings)
- Executando
- Rotas principais / APIs
- Estrutura relevante
- Static (CSS / JS)
- Troubleshooting comum
- Contribuição
- Licença

---

## Sobre
Esta aplicação permite:
- Abrir OS (com possibilidade de vincular um objeto/veículo já cadastrado)
- Listar OS
- Editar OS (pré-preenchendo dados do objeto)
- Cancelar OS (soft-cancel — atualiza `SITUACAO`)
- Endpoints AJAX para popular select de objetos por proprietário e obter detalhe do objeto

O modelo de dados esperado (nomes de tabela/colunas) está alinhado com:
- `TORDEMSERVICO` (ordens)
- `TORDEMOBJETO` (objetos/veículos)
- opcional: `TORDECLIENTE` (clientes/proprietários)

---

## Requisitos
- Python 3.10+ (testado com 3.11)
- Django 5.x (ex.: 5.2.6)
- Driver Firebird (ex.: `fdb` ou `firebird-driver`) compatível com sua plataforma
- pip, virtualenv/venv

---

## Instalação (desenvolvimento)
```bash
git clone <seu-repo>
cd <seu-repo>

python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
