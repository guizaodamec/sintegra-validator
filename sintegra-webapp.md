# SINTEGRA Auto-Fix — Web App

> Plataforma web para validação e correção automática de arquivos SINTEGRA via IA (DeepSeek API).

---

## Links

| Recurso | URL |
|---------|-----|
| **Site** | https://sintegra-auto-fix-production.up.railway.app |
| **GitHub** | https://github.com/guizaodamec/sintegra-validator |
| **Railway** | https://railway.com/project/d38f3eb0-2fd9-4b25-ad60-123664c1c8ff |

---

## Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.12, Flask, Gunicorn |
| IA | DeepSeek API (`deepseek-chat`) |
| Frontend | HTML5, CSS3 puro, JavaScript vanilla (sem frameworks) |
| Deploy | Railway + GitHub Actions (auto-deploy on push) |
| Validador | `validar_sintegra.py` (implementação própria das regras SINTEGRA) |

---

## Estrutura do Projeto

```
/home/guilherme/Área de trabalho/sintegra/
├── app.py                      # Flask web app (endpoints: /validate, /fix-stream, /confirm-fix, /download)
├── validar_sintegra.py         # Validador CLI + biblioteca (importável)
├── estrutura-sintegra.md       # Documentação de referência (auto-atualizável via feedback)
├── docs/
│   └── estrutura-sintegra.md   # Cópia dos docs (lida primeiro pelo app)
├── templates/
│   └── index.html              # Frontend completo (upload, validação, streaming, download)
├── requirements.txt            # flask, gunicorn, openai, python-dotenv
├── runtime.txt                 # python-3.12 (para detecção no Railway)
├── Procfile                    # web: gunicorn app:app --bind 0.0.0.0:$PORT
├── .gitignore                  # *.TXT, *.bak, *.exe, *.dll, *.png
└── README.md                   # Documentação do repositório
```

---

## Fluxo da Aplicação

```
1. Upload do arquivo .TXT
         │
         ▼
2. Validação (validar_sintegra.py)
   ├── encoding latin-1
   ├── CR+LF line endings
   ├── 126 caracteres por linha
   ├── IE por UF (MG, SP, SC)
   ├── CFOP
   ├── Consistência tipo 61 (pos 62 = pos 107 × 1.000.000)
   ├── Cross-check 61R ↔ 75
   └── Trailer tipo 90 (contagens)
         │
         ▼
3. Erros? ──Não──▶ ✅ "Arquivo Válido!"
         │
        Sim
         │
         ▼
4. Auto-Fix com DeepSeek (streaming SSE)
   ├── 🔍 Analisando erros...
   ├── 📖 Lendo documentação...
   ├── 🤖 Enviando para DeepSeek...
   ├── 💭 Raciocínio da IA (streaming ao vivo)
   ├── ⚡ Executando script de correção...
   └── 🔍 Revalidando...
         │
         ▼
5. Download do arquivo corrigido
         │
         ▼
6. Analista revisa → "✅ Confirmar & Atualizar MD"
   └── Caso adicionado ao estrutura-sintegra.md
```

---

## Endpoints da API

### `POST /validate`
Recebe arquivo via `multipart/form-data`, retorna JSON com erros.

```json
{
  "valid": false,
  "filename": "arquivo.TXT",
  "total_lines": 364,
  "record_types": {"10": 1, "11": 1, "50": 19, ...},
  "has_crlf": true,
  "errors": [
    {"linha": 200, "codigo": "61R-NO75", "msg": "Registro 61R sem tipo 75..."}
  ],
  "temp_path": "/tmp/tmpXXXXXX.TXT",
  "content": "..."
}
```

### `POST /fix-stream`
Recebe `{errors, filename, temp_path}`, retorna **Server-Sent Events** (streaming).

Eventos SSE:
```javascript
{step: "start",    msg: "🔍 Iniciando análise..."}
{step: "reading",  msg: "📖 Lendo documentação..."}
{step: "calling",  msg: "🤖 Enviando para DeepSeek..."}
{step: "thinking", msg: "Explicação da correção..."}
{step: "executing", msg: "⚡ Executando script..."}
{step: "done",     success: true, download: "corrigido_arquivo.TXT", re_valid: true}
```

### `POST /confirm-fix`
Recebe `{errors, description, filename}`, atualiza `estrutura-sintegra.md`.

### `GET /download/<filename>`
Download do arquivo corrigido.

---

## Tipos de Erro Detectados

| Código | Descrição |
|--------|-----------|
| `61R-NO75` | Registro 61R sem tipo 75 correspondente |
| `T50-IE` | Inscrição Estadual inválida para a UF |
| `T61-VALOR` | Valores inconsistentes no tipo 61 (pos 62 ≠ pos 107 × 1M) |
| `T90-COUNT` | Contagem de registros no trailer divergente |
| `T90-LINES` | Total de linhas no trailer divergente |
| `TAMANHO` | Linha com tamanho incorreto |
| `CRLF` | Arquivo sem line endings CR+LF |
| `T50-CFOP` | CFOP possivelmente inválido |

---

## Regras de IE por UF (implementadas)

| UF | Dígitos | Algoritmo |
|----|---------|-----------|
| **MG** | 13 | Pesos [3,2,11,10,9,8,7,6,5,4,3,2], mod 11 |
| **SP** | 12 | D1: pesos [1,3,4,5,6,7,8,10] mod 11; D2: pesos [3,2,10,9,8,7,6,5,4,3,2] mod 11 |
| **SC** | 9 | Pesos [9,8,7,6,5,4,3,2], mod 11 |
| Outras | ≥8 | Apenas verificação de formato (dígitos + tamanho) |

---

## Mapeamento 61R ↔ 75

A correspondência entre registros é feita pelo **código base** (10 chars) com zeros removidos:

```python
def base_key(b):
    return b.replace('0', '')

# Ex: 61R base "1200000000" → key "12"
#     75  base "0012000000" → key "12"
#     → correspondem!
```

Produto: `61R produto / 1000` → sufixo 4 dígitos do 75.
Ex: `15000 / 1000 = 15` → sufixo `0015` → código 75 completo: `00120000000015`

---

## Variáveis de Ambiente (Railway)

```
DEEPSEEK_API_KEY=sk-...    # API key do DeepSeek
PORT=5000                   # Porta (definido pelo Railway)
```

---

## Deploy

```bash
# Push no GitHub → Railway auto-deploy
git push origin main

# Ou manual via CLI
railway up --service sintegra-auto-fix
```

---

## Aprendizado Contínuo

Cada correção confirmada pelo analista adiciona um **novo caso** ao `estrutura-sintegra.md`:

```markdown
### Caso N — Descrição

| Data | 2026-06-19 |
| Arquivo | `0012605NM (2).TXT` |
| Erro(s) | 61R-NO75 |
| Linhas afetadas | 200, 201 |

**Método:** ...
```

Isso enriquece o contexto da IA para correções futuras mais precisas.

---

## Fallback Manual

Quando o auto-fix do site não resolve 100%:

1. Usuário envia erro para o Claude Code local
2. Claude analisa, corrige, commita e pusha no GitHub
3. Correção fica disponível no site e no MD

---

## Histórico de Casos

### Caso 1 — Correção de valores de notas e total (2026-06-15)
- Arquivo: `0012604NM.TXT`
- 7 notas corrigidas (valores tipo 50 e 54)

### Caso 2 — 61R sem tipo 75 correspondente (2026-06-19)
- Arquivo: `0012605NM (1).TXT`
- Produtos 003 e 014 criados no tipo 75

### Caso 3 — 61R sem tipo 75 correspondente (2026-06-19)
- Arquivo: `0012605NM (2).TXT`
- Mesmo padrão, corrigido pelo web app
