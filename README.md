# SINTEGRA Auto-Fix

Validação e correção automática de arquivos SINTEGRA usando IA (DeepSeek API).

## Funcionalidades

- **🔍 Validação**: Detecta erros comuns em arquivos SINTEGRA (IE inválida, 61R sem 75, valores inconsistentes, trailer incorreto)
- **🤖 Auto-Fix com IA**: Envia erros + documentação para DeepSeek API que corrige automaticamente
- **📝 Aprendizado contínuo**: Cada correção confirmada por analista atualiza a documentação (MD), tornando o sistema mais inteligente
- **🌐 Web App**: Interface web para upload, validação e download do arquivo corrigido

## Stack

- **Backend**: Python 3, Flask, Gunicorn
- **IA**: DeepSeek API (deepseek-chat)
- **Frontend**: HTML5, Tailwind CSS, JavaScript vanilla
- **Deploy**: Railway

## Variáveis de Ambiente

```bash
DEEPSEEK_API_KEY=sk-...   # API key do DeepSeek
PORT=5000                  # Porta do servidor (opcional)
```

## Uso Local

```bash
pip install -r requirements.txt
echo "DEEPSEEK_API_KEY=sk-..." > .env
python app.py
# Acessar http://localhost:5000
```

## CLI

```bash
# Apenas validar
python3 validar_sintegra.py arquivo.TXT

# Validar com auto-fix básico
python3 validar_sintegra.py arquivo.TXT --auto-fix
```

## Estrutura

```
├── app.py                    # Flask web app
├── validar_sintegra.py       # Validador Python (CLI + import)
├── estrutura-sintegra.md     # Documentação de referência (auto-atualizável)
├── templates/index.html      # Frontend
├── requirements.txt          # Dependências
├── Procfile                  # Railway deploy
└── railway.toml              # Railway config
```

## Licença

MIT
