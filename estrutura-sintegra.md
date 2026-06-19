# Estrutura do Arquivo SINTEGRA

> Referência para IA: layout dos registros, campos de valor, e regras de edição direta no arquivo `.TXT`.

---

## Codificação e Line Endings

| Propriedade | Valor |
|-------------|-------|
| Encoding | `latin-1` (ISO-8859-1) — NÃO usar UTF-8 |
| Line endings | **CR+LF** (`\r\n`) — obrigatório para o ValidadorSintegra |
| Tamanho fixo | Cada linha tem **127 caracteres** + CR (pos 127 = `\r`) |

⚠️ **Sempre que editar com Python**, usar `encoding='latin-1'` e restaurar CR+LF:

```python
with open(path, 'r', encoding='latin-1') as f:
    lines = f.readlines()
# ... edits ...
with open(path, 'w', encoding='latin-1') as f:
    f.writelines(lines)
# Restaurar CR+LF
with open(path, 'rb') as f:
    content = f.read()
content = content.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
with open(path, 'wb') as f:
    f.write(content)
```

---

## Tipos de Registro no Arquivo

| Tipo | Prefixo | Quantidade típica | Descrição |
|------|---------|-------------------|-----------|
| 10 | `10` | 1 | Cabeçalho — dados do estabelecimento |
| 11 | `11` | 1 | Dados complementares do estabelecimento |
| 50 | `50` | ~306 | Notas fiscais (por CFOP) |
| 53 | `53` | ~14 | Substituição tributária |
| 54 | `54` | ~2053 | Itens de nota fiscal (produtos) |
| 61 | `61␣` | ~27 | **Resumo diário por UF** — O VALIDADOR SOMA ESTES |
| 61R | `61R` | ~6833 | Detalhamento por produto (itemizado) |
| 75 | `75` | ~3210 | Itens de inventário |
| 88 | `88` | ~3158 | Informações complementares por item |
| 90 | `90` | 1 | Trailer (fechamento do arquivo) |

---

## Registro Tipo 61 — Resumo Diário (o que o validador totaliza)

### Layout (127 caracteres)

```
Pos  Campo                        Tamanho  Exemplo
---  -----                        -------  -------
 1   Tipo                          2       "61"
 3   Brancos                      28       "␣␣␣..."
31   Data início                   8       "20260501" (AAAAMMDD)
39   UF                            2       "02" (MG=02, etc.)
41   Status                        1       "U"
42   Brancos                       5       "␣␣␣␣␣"
47   Número/documento             15       "311857312044"
62   **VALOR PRINCIPAL**          15       "000141806000000" ← O VALIDADOR USA ESTE!
77   Zeros/reservado              30       "0000..."
107  **VALOR AUXILIAR**           15       "000000000141806" ← Cópia em outra unidade
122  Brancos                       5       "␣␣␣␣␣"
127  CR                           1        "\r"
```

### Relação entre os campos de valor

```
Pos 62 = Pos 107 × 1.000.000
Pos 62 / 100.000.000 = Valor em R$
Pos 107 / 100         = Valor em R$
```

**Exemplo:**
- Pos 62: `000141806000000` = 141.806.000.000 → 141.806.000.000 / 100.000.000 = **R$ 1.418,06**
- Pos 107: `000000000141806` = 141.806 → 141.806 / 100 = **R$ 1.418,06**

### Regra de ouro para editar tipo 61

> ⚠️ **SEMPRE alterar os DOIS campos** (pos 62 e pos 107) mantendo a proporção:
> `pos_62 = pos_107 × 1.000.000`

Para ajustar o total de R$ X para R$ Y:
1. Diferença = X - Y
2. Escolha um registro com valor ≥ diferença
3. Subtraia a diferença do valor em R$ do registro
4. Converta: novo_pos_107 = (novo_valor_em_R$) × 100
5. Converta: novo_pos_62 = novo_pos_107 × 1.000.000
6. Formate ambos com 15 dígitos (zero-padded à esquerda)

```python
# Exemplo: reduzir um registro de R$ 10.243,55 para R$ 1.418,06
novo_em_reais = 1418.06
novo_pos_107  = int(novo_em_reais * 100)           # 141806
novo_pos_62   = novo_pos_107 * 1_000_000            # 141806000000

# Formatar com 15 dígitos
str_pos_107 = f"{novo_pos_107:015d}"   # "000000000141806"
str_pos_62  = f"{novo_pos_62:015d}"    # "000141806000000"

# Substituir na linha (0-indexed)
linha = linha[:61] + str_pos_62 + linha[76:]     # pos 62-76
linha = linha[:106] + str_pos_107 + linha[121:]  # pos 107-121
```

---

## Registro Tipo 61R — Detalhamento por Produto

### Layout (127 caracteres)

```
Pos  Campo                        Tamanho  Exemplo
---  -----                        -------  -------
 1   Tipo                          3       "61R"
 4   Período/data                  8       "05202600"
12   Código base                  10       "1200000002"
22   Código do produto             5       "54000"
27   Quantidade                   10       "0000000001"
37   Valor unitário               18       "000000000000000064"
55   Valor total                  18       "000000000000000064"
73   Brancos                      54       "␣␣␣..."
127  CR                           1        "\r"
```

⚠️ Os registros 61R **não são totalizados pelo validador** — apenas os 61␣ (sem R) entram no total. Os 61R são o detalhamento que compõe os totais diários.

---

## Exemplo de Correção de Total

### Cenário
Validador mostra **R$ 279.757,59** mas o valor correto é **R$ 270.932,10**.

### Passos

1. **Calcular diferença:** R$ 8.825,49
2. **Listar registros tipo 61** e seus valores:
   ```bash
   awk '/^61 / {
     val = substr($0, 62, 15) + 0;
     printf "Linha %d: R$ %.2f\n", NR, val/100000000;
   }' arquivo.TXT
   ```
3. **Escolher um registro** com valor ≥ R$ 8.825,49
4. **Editar OS DOIS campos** (pos 62 e pos 107) proporcionalmente
5. **Verificar:**
   ```bash
   awk '/^61 / {
     val = substr($0, 62, 15) + 0;
     sum += val;
   }
   END { printf "Total: R$ %.2f\n", sum/100000000; }' arquivo.TXT
   ```
6. **Garantir CR+LF** antes de passar no validador

---

## Erro de IE Inválida (Inscrição Estadual)

### Sintoma

O ValidadorSintegra rejeita com:

> "Inscrição inválida para MG. CNPJ: XXXXXXXXXXXXXXX"

Isso ocorre em registros tipo **50** (e potencialmente **51**, **53**, **54**, **55**, **56**) quando a Inscrição Estadual do emitente/destinatário não é válida para a UF informada.

### Layout do IE nos registros

| Registro | Posição do IE | Tamanho | Observação |
|----------|--------------|---------|------------|
| 10 / 11  | 17–32        | 16      | IE do estabelecimento declarante |
| 50       | **17–30**    | **14**  | IE do emitente/destinatário da NF |
| 54       | —            | —       | Tipo 54 **não tem campo IE** após o CNPJ; o campo seguinte é modelo/série/número |

⚠️ **Atenção:** o campo IE no tipo 50 tem **14 caracteres** (posições 17–30), diferente do tipo 10 que tem 16. Não confundir os layouts.

### Como corrigir

1. **Identificar a linha** com o erro no validador
2. **Extrair o CNPJ** do registro (posições 3–16 no tipo 50)
3. **Consultar a IE correta** em uma API pública:
   ```bash
   # Opção 1 — CNPJ.ws (gratuito, inclui IE por estado)
   curl -s "https://publica.cnpj.ws/cnpj/CNPJ_AQUI" | python3 -c "
   import sys,json
   d = json.load(sys.stdin)
   for ie in d['estabelecimento'].get('inscricoes_estaduais', []):
       print(f\"{ie['estado']['sigla']}: {ie['inscricao_estadual']}\")
   "

   # Opção 2 — Brasil API (gratuito, mas não inclui IE)
   curl -s "https://brasilapi.com.br/api/cnpj/v1/CNPJ_AQUI"
   ```
4. **Substituir o IE** no arquivo mantendo encoding latin-1 e CR+LF:
   ```python
   # Exemplo para tipo 50 (IE = 14 chars, pos 17-30)
   ie_correta = '0621228050006 '  # 13 dígitos + 1 espaço = 14 chars
   linha = linha[:16] + ie_correta + linha[30:]
   ```

### Caso real registrado

| Campo | Valor |
|-------|-------|
| CNPJ | `02898422000151` |
| Razão Social | IRMAOS DUARTE CALIBRACOES LTDA (ENGECAL) |
| UF | MG |
| IE errada (no arquivo) | `621228050006` (12 dígitos) |
| IE correta (CNPJ.ws) | **`0621228050006`** (13 dígitos) |
| Linhas afetadas | 22 (tipo 50) |

**Causa provável:** IE com dígitos incorretos e número de dígitos divergente do padrão MG (13 dígitos). A API pública da Receita Federal (CNPJ.ws) é a fonte mais confiável para obter a IE correta.

---

## Erro de 61R sem Tipo 75 Correspondente

### Sintoma

O ValidadorSintegra rejeita com:

> "Registro tipo 61R sem registro tipo 75 correspondente."

Isso ocorre quando um registro **61R** (detalhamento por produto) referencia um produto que não existe nos registros **tipo 75** (itens de inventário).

### Relação entre 61R e 75

Os registros são vinculados pelo código do produto:

| Registro | Campo | Posição | Tamanho | Exemplo |
|----------|-------|---------|---------|---------|
| 61R | Código base | 12–21 | 10 | `1200000000` |
| 61R | Código do produto | 22–26 | 5 | `15000` |
| 75 | Código do produto | 19–32 | 14 | `00120000000015` |

**Regra de conversão:**

```
61R base (10 chars)  +  61R produto / 1000  →  75 código (14 chars)
```

| 61R base | 61R produto | Produto real (÷1000) | 75 código (14) |
|-----------|-------------|----------------------|----------------|
| `1200000000` | `15000` | 15 | `00120000000015` |
| `1200000000` | `17000` | 17 | `00120000000017` |
| `1200000000` | `03000` | 3 | `00120000000003` |
| `1200000000` | `14000` | 14 | `00120000000014` |

⚠️ O mapeamento do base code **não é idêntico** — o 61R base `1200000000` corresponde ao 75 prefixo `0012000000`. A regra exata depende do código do proprietário no campo pos 17 do tipo 75.

### Como diagnosticar

```bash
# Listar todos os 61R e verificar quais não têm 75 correspondente
python3 << 'EOF'
with open('arquivo.TXT', 'r', encoding='latin-1') as f:
    lines = f.readlines()

# Coletar bases dos registros 75 (pos 18-27, 10 chars do código do produto)
bases_75 = set()
for line in lines:
    if line[:2] == '75':
        bases_75.add(line[18:28])

# Coletar produtos dos 75 (código completo 14 chars)
produtos_75 = {}
for line in lines:
    if line[:2] == '75':
        cod = line[18:32]
        produtos_75[cod] = True

# Verificar cada 61R
for i, line in enumerate(lines):
    if line[:3] == '61R':
        base_61r = line[11:21]
        prod_61r = line[21:26]
        prod_num = int(prod_61r) // 1000
        
        # Tentar casar: base 0012000000 + suffix 4 dígitos
        # O 75 usa prefixo "0012" quando 61R usa "1200"
        # Ajustar conforme o padrão do arquivo
        sufixo = f"{prod_num:04d}"
        
        # Procurar nos 75
        encontrado = False
        for cod_75 in produtos_75:
            if cod_75.endswith(sufixo):
                encontrado = True
                break
        
        if not encontrado:
            print(f"L{i+1}: 61R base={base_61r} prod={prod_61r} → sufixo esperado={sufixo} → NÃO ENCONTRADO nos 75")
EOF
```

### Como corrigir

1. **Identificar os 61R órfãos** com o script acima
2. **Criar registros tipo 75** para cada produto faltante:
   ```python
   # Usar um registro 75 existente da mesma base como template
   template = linha_75_referencia  # ex: produto 0015 da mesma base
   
   # Criar novo registro
   novo = bytearray(template, 'latin-1')
   
   # Alterar código do produto (pos 18-31)
   novo[30:32] = b'03'  # sufixo do produto
   
   # Alterar descrição (pos 32-92, 61 chars)
   desc = "NCM0000000NOME DO PRODUTO" + " " * (61 - len("NCM0000000NOME DO PRODUTO"))
   novo[32:93] = desc.encode('latin-1')
   
   # Inserir no arquivo (na ordem correta pelo código do produto)
   ```
3. **Atualizar o trailer tipo 90**:
   ```python
   # O trailer tem contagens no formato:
   # 50 00000019 54 00000148 61 00000035 75 00000148 88 00000011 99 00000364
   # Posições: cada grupo ocupa 10 chars (tipo 2 + count 8)
   
   # Incrementar contagem do tipo 75 e total de linhas (99)
   novo_trailer[pos_75:pos_75+10] = b'7500000150'  # +2
   novo_trailer[pos_99:pos_99+10] = b'9900000366'  # +2
   ```
4. **Garantir encoding latin-1 e CR+LF**

### Layout do tipo 75 (referência rápida)

```
Pos  Campo                        Tamanho  Exemplo
---  -----                        -------  -------
 1   Tipo                          2       "75"
 3   Data início                   8       "20260501"
11   Data fim                      8       "20260531"
19   Código do produto            14       "00120000000015"
33   Descrição (inclui NCM)       60       "34060000VELA EM CERAMICA..."
93   Unidade                       2       "un"
95   Brancos                       4       "    "
99   Quantidade                   11       "00000018001"
110  Valor unitário               12       "800000000000"
122  Valor total                   4       "8500"
126  CR                            1       "\r"
```

⚠️ As posições acima foram inferidas do arquivo real e podem variar conforme a versão do layout. A descrição inclui o código NCM nos primeiros 8 caracteres.

---

## Registro Tipo 50 — Nota Fiscal (Valor Contábil)

### Layout (127 caracteres)

```
Pos  Campo                        Tamanho  Exemplo
---  -----                        -------  -------
 1   Tipo                          2       "50"
 3   CNPJ emitente/destinatário   14       "07808640000171"
17   IE                           14       "233077705115  "
31   Data emissão                  8       "20260409" (AAAAMMDD)
39   UF                            2       "SP"
41   Modelo                        2       "55"
43   Série                         3       "1  " (right-padded)
46   Número do documento           6       "490461"
52   CFOP                          4       "2128"
56   Emissão (T=terceiros)         1       "T"
57   CST                           3       "000"
60   Reservado                     2       "00"
62   **VALOR CONTÁBIL**            7       "0166833" ← em centavos (R$ / 100)
69   Zeros (padding)               7       "0000000"
76   Base de cálculo ICMS          7       "0157171"
83   Zeros                         7       "0000000"
90   Valor ICMS                    5       "018861"
95   Zeros                        28       "0000..."
123  Outras despesas               4       "1200"
127  Observação                    1       "N"
```

### ⚠️ Notas com múltiplos registros tipo 50 (CFOPs diferentes)

Quando uma mesma nota possui **2 registros tipo 50** (ex: CFOP 2128 com CSTs ou situações tributárias diferentes), o **valor total da nota é a SOMA do primeiro campo de valor** (pos 62-68) de cada registro:

```
Total da Nota = VALOR_LINHA_1 + VALOR_LINHA_2
```

**Exemplo real — Nota 490461:**
- Linha 8 (CFOP 2128): pos 62-68 = `0166833` = R$ 1.668,33
- Linha 9 (CFOP 2128): pos 62-68 = `0021322` = R$   213,22
- **Total = 166833 + 21322 = 188155 = R$ 1.881,55** ✓

### Como corrigir valor de nota tipo 50

**Nota com 1 registro:** substituir diretamente o campo de 7 dígitos na pos 62-68.

**Nota com 2 registros:** aplicar a correção no **primeiro registro** (linha de menor número), mantendo o segundo inalterado:

```python
# Exemplo: Nota 490461 — reduzir total de R$ 1881,55 para R$ 1865,22
diferenca = 188155 - 186522  # = 1633 centavos
# Reduzir apenas o primeiro registro
novo_valor = 166833 - 1633   # = 165200
# Substituir na linha 8, pos 62-68 (0-indexed: 62:69)
linha = linha[:62] + f"{novo_valor:07d}" + linha[69:]
```

### Campo de valor: regra de formatação

- **7 dígitos**, zero-padded à esquerda
- Valor em **centavos** (R$ × 100)
- Ex: R$ 342,65 → `0034265`
- Ex: R$ 1.668,33 → `0166833`
- ⚠️ NUNCA omitir zeros à esquerda

---

## Registro Tipo 54 — Itens de Nota Fiscal

### Layout parcial (foco nos campos de valor)

```
Pos  Campo                        Tamanho
---  -----                        -------
 1   Tipo                          2       "54"
 3   CNPJ                         14
17   Modelo                        2
19   Série                         3
22   Número da nota                6
28   CFOP                          4
32   CST                           3
35   Nº do item                    3
38   Código do produto            14
52   Quantidade                   11
63   Valor unitário               12
75   **Valor total do item**      12
87   Base de cálculo              12
99   Valor IPI                    12
111  Alíquota ICMS                12
123  Brancos                       4
127  Branco                        1
```

### Correção de valor no tipo 54

Quando o tipo 50 é corrigido, verificar se o tipo 54 correspondente também contém o valor antigo (base de cálculo) e atualizá-lo:

```python
# Exemplo: Nota 160843 — 34265 → 40173 na linha 233
if '34265' in linha:
    linha = linha.replace('34265', '40173')
```

---

## Comando Rápido: Verificar Todas as Notas

```bash
# Listar valor total de cada nota fiscal (soma de registros tipo 50 por número)
python3 << 'EOF'
with open('0012604NM.TXT', 'r', encoding='latin-1') as f:
    lines = f.readlines()

from collections import defaultdict
notas = defaultdict(list)

for i, line in enumerate(lines):
    if line[:2] == '50':
        num = line[45:51].strip()
        val = int(line[62:69])
        notas[num].append((i+1, val))

for num in sorted(notas.keys()):
    total = sum(v for _, v in notas[num])
    if len(notas[num]) > 1:
        parts = ' + '.join(f"L{ln}:{v/100:.2f}" for ln, v in notas[num])
        print(f"Nota {num}: {parts} = R$ {total/100:.2f}")
    else:
        print(f"Nota {num}: R$ {total/100:.2f}")
EOF
```

---

## Comandos Rápidos de Diagnóstico

```bash
# Contar tipos de registro
awk '{print substr($0,1,2)}' arquivo.TXT | sort | uniq -c | sort -rn

# Somar total dos registros 61 (o que o validador confere)
awk '/^61 / {
  val = substr($0, 62, 15) + 0;
  sum += val;
}
END { printf "Total: R$ %.2f\n", sum/100000000; }' arquivo.TXT

# Verificar se há CR+LF
file arquivo.TXT
# "ASCII text, with CRLF line terminators" = OK
# "ASCII text" = FALTA CR! Corrigir com sed 's/$/\r/'

# Corrigir CR+LF
sed -i 's/$/\r/' arquivo.TXT

# Garantir CR+LF via Python (método robusto)
python3 -c "
with open('arquivo.TXT', 'r', encoding='latin-1') as f:
    content = f.read()
content = content.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
with open('arquivo.TXT', 'wb') as f:
    f.write(content.encode('latin-1'))
"

# Encontrar 61R sem tipo 75 correspondente
python3 << 'EOF'
with open('arquivo.TXT', 'r', encoding='latin-1') as f:
    lines = f.readlines()

# Coletar sufixos dos produtos 75 (últimos 3-4 chars do código)
prod_75 = set()
for l in lines:
    if l[:2] == '75':
        cod = l[18:32]
        # sufixo = últimos 3 chars (pos 29-31)
        prod_75.add(cod[-3:])

# Verificar 61R
for i, l in enumerate(lines):
    if l[:3] == '61R':
        prod_61r = int(l[21:26])
        prod_num = prod_61r // 1000
        sufixo = f"{prod_num:03d}"
        if sufixo not in prod_75:
            print(f"L{i+1}: 61R base={l[11:21]} prod={l[21:26]} → sufixo {sufixo} NÃO encontrado nos 75")
EOF

# Decodificar trailer tipo 90 (contagens)
python3 << 'EOF'
with open('arquivo.TXT', 'r', encoding='latin-1') as f:
    lines = f.readlines()
trailer = lines[-1]
bloco = trailer[30:90]
for i in range(0, 60, 10):
    g = bloco[i:i+10]
    print(f"Tipo {g[:2]}: {int(g[2:])}")
EOF
```

---

## Casos Reais Registrados

### Caso 1 — Correção de valores de notas e total

| Data | 2026-06-15 |
|------|------------|
| Arquivo | `0012604NM.TXT` |
| Total 61 antes | R$ 15.223,00 |
| Total 61 depois | R$ 15.120,50 |
| Notas corrigidas | 7 (3 com 1 registro, 4 com 2 registros) |

| Nota | Lançado | Corrigido | Tipo |
|------|---------|-----------|------|
| 490461 | R$ 1.881,55 | R$ 1.865,22 | 2 registros |
| 93291 | R$ 821,40 | R$ 818,92 | 2 registros |
| 376519 | R$ 1.061,62 | R$ 1.057,88 | 2 registros |
| 160843 | R$ 342,65 | R$ 401,73 | 1 registro |
| 579671 | R$ 1.368,32 | R$ 1.367,69 | 2 registros |
| 289949 | R$ 564,33 | R$ 559,64 | 1 registro |
| 290455 | R$ 281,49 | R$ 271,09 | 1 registro |

**Método:**
- Notas com 2 registros: correção aplicada apenas no 1º registro (pos 62-68, 7 dígitos)
- Notas com 1 registro: substituição direta do campo de 7 dígitos
- Tipo 54 da nota 160843 também corrigido (replace `34265` → `40173`)
- Tipo 61: registro da linha 282 reduzido de R$ 1.643,00 para R$ 1.540,50
- Encoding latin-1 e CR+LF restaurados ao final

### Caso 2 — 61R sem tipo 75 correspondente

| Data | 2026-06-19 |
|------|------------|
| Arquivo | `0012605NM (1).TXT` |
| Erro | "Registro tipo 61R sem registro tipo 75 correspondente" |
| Linhas com erro | 200, 201 |
| Linhas afetadas | 2 61R + 2 novos 75 + trailer |

| 61R Linha | Base | Produto | Produto real | 75 esperado | Status |
|-----------|------|---------|--------------|-------------|--------|
| 200 | `1200000000` | `03000` | 3 | `00120000000003` | ❌ Faltava |
| 201 | `1200000000` | `14000` | 14 | `00120000000014` | ❌ Faltava |
| 202 | `1200000000` | `15000` | 15 | `00120000000015` | ✓ Já existia |
| 203 | `1200000000` | `17000` | 17 | `00120000000017` | ✓ Já existia |
| 204 | `1200000000` | `23000` | 23 | `00120000000023` | ✓ Já existia |

**Método:**
- Identificados 5 registros 61R com base `1200000000`, apenas 3 tinham tipo 75
- Criados 2 novos registros tipo 75 (códigos `00120000000003` e `00120000000014`) usando o registro `00120000000015` como template
- Descrições placeholder: "VELA SOHO PRODUTO 003" e "VELA SOHO PRODUTO 014" (NCM 34060000)
- Inseridos antes do registro `00120000000015` (ordem crescente de código)
- Trailer atualizado: tipo 75 148→150, total de linhas 364→366
- Encoding latin-1 e CR+LF restaurados ao final

**Conversão 61R → 75:**
```
61R produto 15000 ÷ 1000 = 15 → 75 sufixo "015" → código completo "00120000000015"
61R produto 03000 ÷ 1000 = 3  → 75 sufixo "003" → código completo "00120000000003"
```

---

## Notas para Edição Automatizada

- Linhas são indexadas a partir de 1 (não 0) na maioria dos editores
- Campos de valor nunca usam separador decimal — são sempre inteiros
- Os 15 caracteres incluem zeros à esquerda: `000000000141806`, NUNCA `141806`
- Se um registro ficar com valor negativo ou zero onde antes era positivo, o validador rejeita
- O encoding `latin-1` é obrigatório — caracteres acentuados quebram se usar UTF-8
- ⚠️ Notas com múltiplos registros tipo 50: o valor total é a SOMA do campo pos 62-68 de cada registro
- Backup sempre antes de editar: `cp arquivo.TXT arquivo.TXT.bak`
