#!/usr/bin/env python3
"""
SINTEGRA Auto-Fix - Web App
Upload de arquivo SINTEGRA → validação → correção automática via DeepSeek API
"""

import os
import re
import json
import shutil
import tempfile
import traceback
from pathlib import Path
from datetime import datetime
from io import BytesIO

from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from openai import OpenAI

# Import our validator
from validar_sintegra import SintegraValidator

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
DEEPSEEK_MODEL = 'deepseek-chat'  # or deepseek-reasoner for complex fixes

# Load MD documentation at startup
MD_PATH = Path(__file__).parent / 'estrutura-sintegra.md'
MD_DOCS = MD_PATH.read_text(encoding='utf-8') if MD_PATH.exists() else ''


def fix_file_with_deepseek(file_content: str, errors: list, filename: str) -> dict:
    """Send file + errors + docs to DeepSeek and get corrected file back."""
    if not DEEPSEEK_API_KEY:
        return {
            'success': False,
            'error': 'DEEPSEEK_API_KEY não configurada no .env'
        }

    # Format errors for the prompt
    errors_text = '\n'.join(
        f"Linha {e['linha']} [{e['codigo']}]: {e['msg']}"
        for e in errors
    )

    # Truncate file if too large (DeepSeek context window)
    max_file_chars = 80000
    file_preview = file_content
    if len(file_content) > max_file_chars:
        mid = max_file_chars // 2
        file_preview = (
            file_content[:mid] +
            f"\n\n... [TRUNCADO: {len(file_content) - max_file_chars} caracteres omitidos] ...\n\n" +
            file_content[-mid:]
        )

    prompt = f"""Você é um especialista em arquivos SINTEGRA (Sistema Integrado de Informações sobre Operações Interestaduais com Mercadorias e Serviços).

## Documentação de Referência

{MD_DOCS}

## Arquivo: {filename}

O arquivo abaixo foi validado e apresenta OS SEGUINTES ERROS:

{errors_text}

## Arquivo TXT original:

```
{file_preview}
```

## Tarefa

Corrija TODOS os erros listados acima. Siga exatamente a documentação de referência para cada tipo de erro.

Retorne APENAS um JSON válido neste formato exato, sem markdown, sem explicações:

{{"fixed_content": "conteúdo completo do arquivo corrigido, com todas as linhas, encoding latin-1, CR+LF"}}

IMPORTANTE:
1. O campo fixed_content deve conter o arquivo COMPLETO, não apenas as linhas alteradas
2. Mantenha encoding latin-1 (substitua caracteres não-latin1 por equivalentes)
3. Todas as linhas devem ter CR+LF (\\r\\n)
4. Atualize o trailer (tipo 90) com as contagens corretas
5. Se houver registros 61R sem tipo 75, CRIE os registros 75 necessários
6. Se houver IE inválida, corrija consultando os algoritmos da documentação
7. Se houver valores inconsistentes no tipo 61, corrija ambos os campos (pos 62 e 107)
"""

    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "Você é um especialista em SINTEGRA. Retorne APENAS JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=32000,
        )

        reply = response.choices[0].message.content.strip()

        # Extract JSON from reply (handle markdown code blocks)
        json_match = re.search(r'\{.*\}', reply, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
            fixed = result.get('fixed_content', '')

            if not fixed or len(fixed) < 100:
                return {
                    'success': False,
                    'error': 'DeepSeek retornou conteúdo muito curto ou vazio',
                    'raw': reply[:500]
                }

            return {
                'success': True,
                'fixed_content': fixed,
                'raw_response': reply[:300]
            }

        return {
            'success': False,
            'error': 'Não foi possível extrair JSON da resposta',
            'raw': reply[:500]
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Erro na API DeepSeek: {str(e)}',
            'traceback': traceback.format_exc()[:500]
        }


def apply_basic_fixes(file_content: str, errors: list) -> str:
    """Apply basic fixes that don't require AI (CRLF, encoding, etc.)."""
    lines = file_content.split('\n')

    for err in errors:
        if err['codigo'] == 'CRLF':
            # Fix CRLF
            file_content = file_content.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')

    return file_content


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/validate', methods=['POST'])
def validate():
    """Validate uploaded file and return errors."""
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo vazio'}), 400

    # Save to temp file
    suffix = Path(file.filename).suffix or '.TXT'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # Read content
        with open(tmp_path, 'rb') as f:
            raw = f.read()

        # Try latin-1 decode
        try:
            content = raw.decode('latin-1')
        except:
            content = raw.decode('utf-8', errors='replace')

        # Run validator
        validator = SintegraValidator(tmp_path)
        is_valid = validator.validate()

        result = {
            'valid': is_valid,
            'filename': file.filename,
            'total_lines': validator.total_lines,
            'record_types': {t: len(v) for t, v in validator.records.items()},
            'has_crlf': getattr(validator, 'has_crlf', False),
            'errors': validator.errors,
            'warnings': validator.warnings,
            'content': content,
            'temp_path': tmp_path,
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'Erro ao validar: {str(e)}'}), 500


@app.route('/fix', methods=['POST'])
def fix():
    """Auto-fix errors using DeepSeek API."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400

    errors = data.get('errors', [])
    filename = data.get('filename', 'arquivo.TXT')
    temp_path = data.get('temp_path', '')
    content = data.get('content', '')

    if not errors:
        return jsonify({'error': 'Nenhum erro para corrigir'}), 400

    # Try to read content from temp_path if not provided
    if not content and temp_path:
        try:
            with open(temp_path, 'rb') as f:
                raw = f.read()
            content = raw.decode('latin-1')
        except Exception as e:
            return jsonify({'error': f'Não foi possível ler o arquivo temporário: {e}'}), 400

    if not content:
        return jsonify({'error': 'Conteúdo do arquivo vazio e sem temp_path válido'}), 400

    # Try DeepSeek first
    result = fix_file_with_deepseek(content, errors, filename)

    if result.get('success'):
        fixed_content = result['fixed_content']

        # Ensure CR+LF
        fixed_content = fixed_content.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')

        # Save fixed file
        output_dir = Path(tempfile.gettempdir()) / 'sintegra_fixes'
        output_dir.mkdir(exist_ok=True)
        fixed_name = f"corrigido_{filename}"
        fixed_path = output_dir / fixed_name

        with open(fixed_path, 'wb') as f:
            f.write(fixed_content.encode('latin-1', errors='replace'))

        # Re-validate
        validator = SintegraValidator(str(fixed_path))
        is_valid = validator.validate()

        return jsonify({
            'success': True,
            'fixed_content': fixed_content,
            'download_path': str(fixed_path),
            'download_name': fixed_name,
            're_valid': is_valid,
            'remaining_errors': validator.errors,
            'remaining_warnings': validator.warnings,
        })
    else:
        # DeepSeek failed, fall back to basic fixes
        fixed_content = apply_basic_fixes(content, errors)

        return jsonify({
            'success': False,
            'error': result.get('error', 'Falha desconhecida'),
            'partial_fix': fixed_content != content,
            'fixed_content': fixed_content if fixed_content != content else None,
        })


@app.route('/confirm-fix', methods=['POST'])
def confirm_fix():
    """Analyst confirms the fix is correct → update MD documentation."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400

    errors_fixed = data.get('errors', [])
    fix_description = data.get('description', '')
    filename = data.get('filename', '')

    if not errors_fixed:
        return jsonify({'error': 'Nenhum erro para registrar'}), 400

    try:
        updated_md = update_md_with_case(errors_fixed, fix_description, filename)
        # Reload MD docs in memory
        global MD_DOCS
        MD_DOCS = updated_md

        return jsonify({
            'success': True,
            'message': f'MD atualizado com {len(errors_fixed)} caso(s)',
            'md_size': len(updated_md),
        })
    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar MD: {str(e)}'}), 500


def update_md_with_case(errors: list, description: str, filename: str) -> str:
    """Append a new confirmed case to estrutura-sintegra.md."""
    md_path = Path(__file__).parent / 'estrutura-sintegra.md'

    if not md_path.exists():
        return MD_DOCS

    md_content = md_path.read_text(encoding='utf-8')

    # Build case entry
    today = datetime.now().strftime('%Y-%m-%d')
    case_num = md_content.count('### Caso ') + 1

    # Detect error types
    error_types = set(e['codigo'] for e in errors)
    error_lines = [e['linha'] for e in errors]
    error_msgs = [e['msg'] for e in errors]

    # Determine section to insert based on error type
    section_keywords = {
        '61R-NO75': ('61R sem Tipo 75 Correspondente', 'Erro de 61R sem Tipo 75'),
        'T50-IE': ('IE Inválida', 'Erro de IE Inválida'),
        'T61-VALOR': ('Tipo 61', 'Registro Tipo 61'),
        'T90-COUNT': ('Trailer', 'Erro de trailer'),
        'CRLF': ('Line Endings', 'Codificação e Line Endings'),
    }

    case_entry = f"""
### Caso {case_num} — {description or 'Correção automática confirmada'}

| Data | {today} |
|------|------|
| Arquivo | `{filename}` |
| Erro(s) | {', '.join(f'{et}' for et in error_types)} |
| Linhas afetadas | {', '.join(str(l) for l in error_lines)} |
| Confirmado por | Analista (via web app) |

**Erros corrigidos:**
{chr(10).join(f'- [{e["codigo"]}] L{e["linha"]}: {e["msg"]}' for e in errors)}

**Método:**
- Correção via DeepSeek API com base na documentação
- Confirmado por analista humano
- Caso adicionado automaticamente à base de conhecimento
"""

    # Insert before "Notas para Edição Automatizada" section
    insertion_point = md_content.find('## Notas para Edição Automatizada')
    if insertion_point > 0:
        md_content = md_content[:insertion_point] + case_entry + '\n---\n\n' + md_content[insertion_point:]

    # Write back
    md_path.write_text(md_content, encoding='utf-8')

    # Try to commit to git if available
    try:
        import subprocess
        repo_dir = md_path.parent
        subprocess.run(['git', '-C', str(repo_dir), 'add', 'estrutura-sintegra.md'],
                       capture_output=True, timeout=10)
        subprocess.run(['git', '-C', str(repo_dir), 'commit', '-m',
                        f'aprendizado: caso {case_num} - {", ".join(error_types)} - {filename}'],
                       capture_output=True, timeout=10)
    except:
        pass  # Git push is optional

    return md_content


@app.route('/download/<path:filename>')
def download(filename):
    """Download corrected file."""
    output_dir = Path(tempfile.gettempdir()) / 'sintegra_fixes'
    filepath = output_dir / filename
    if filepath.exists():
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
    return jsonify({'error': 'Arquivo não encontrado'}), 404


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"Starting SINTEGRA Auto-Fix on port {port}...")
    # Try to pre-load the validator
    try:
        from validar_sintegra import SintegraValidator
        print("Validator loaded OK")
    except Exception as e:
        print(f"Validator load warning: {e}")
    app.run(host='0.0.0.0', port=port, debug=False)
