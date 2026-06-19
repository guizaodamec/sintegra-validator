#!/usr/bin/env python3
"""
Validador SINTEGRA - réplica das validações do ValidadorSintegra2017 oficial.
Uso: python3 validar_sintegra.py <arquivo.TXT> [--auto-fix]
"""

import sys
import os
import re
import struct
from collections import Counter, defaultdict
from datetime import datetime

# ============================================================
# Validação de IE por UF (algoritmos oficiais)
# ============================================================

def ie_valid(ie: str, uf: str) -> bool:
    """Valida Inscrição Estadual conforme algoritmo de cada UF."""
    ie = ie.strip()
    if not ie.isdigit():
        return False

    uf = uf.upper()

    if uf == 'MG':
        # MG: 13 dígitos, valida apenas o último (D13)
        # Pesos: 3,2,11,10,9,8,7,6,5,4,3,2 sobre os 12 primeiros dígitos
        if len(ie) != 13:
            return False
        peso = [3, 2, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(ie[i]) * peso[i] for i in range(12))
        resto = soma % 11
        digito = 11 - resto
        if digito >= 10:
            digito = 0
        return digito == int(ie[12])

    elif uf == 'SP':
        # SP: 12 dígitos
        # D1 (índice 8): pesos [1,3,4,5,6,7,8,10] sobre 8 primeiros, mod 11
        # D2 (índice 11): pesos [3,2,10,9,8,7,6,5,4,3,2] sobre 11 primeiros, mod 11
        ie_clean = ie.strip()
        if len(ie_clean) < 12:
            return False
        ie_clean = ie_clean.zfill(12)

        peso1 = [1, 3, 4, 5, 6, 7, 8, 10]
        soma1 = sum(int(ie_clean[i]) * peso1[i] for i in range(8))
        d1 = soma1 % 11
        if d1 >= 10:
            d1 = 0
        if int(ie_clean[8]) != d1:
            return False

        peso2 = [3, 2, 10, 9, 8, 7, 6, 5, 4, 3, 2]
        soma2 = sum(int(ie_clean[i]) * peso2[i] for i in range(11))
        d2 = soma2 % 11
        if d2 >= 10:
            d2 = 0
        return int(ie_clean[11]) == d2

    elif uf == 'SC':
        # SC: 9 dígitos
        ie_clean = ie.strip().zfill(9)
        if len(ie_clean) < 9:
            return False
        peso = [9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(ie_clean[i]) * peso[i] for i in range(8))
        resto = soma % 11
        digito = 11 - resto
        if digito in (10, 11):
            digito = 0
        return digito == int(ie_clean[8])

    # Para outras UFs, verificar formato básico
    ie_clean = ie.strip()
    return ie_clean.isdigit() and len(ie_clean) >= 8


# ============================================================
# Validação de CFOP
# ============================================================

CFOPS_VALIDOS = {
    '1101', '1102', '1111', '1113', '1116', '1117', '1118', '1120', '1121',
    '1122', '1124', '1125', '1126', '1128', '1151', '1152', '1201', '1251',
    '1252', '1253', '1254', '1255', '1256', '1257', '1301', '1351', '1352',
    '1353', '1354', '1355', '1356', '1401', '1403', '1406', '1407', '1409',
    '1410', '1411', '1414', '1415', '1501', '1502', '1551', '1552', '1553',
    '1556', '1601', '1651', '1652', '1653', '1661', '1662', '1800', '1901',
    '1902', '1903', '1904', '1905', '1906', '1907', '1908', '1909', '1910',
    '1911', '1912', '1913', '1914', '1915', '1916', '1917', '1918', '1919',
    '1920', '1921', '1922', '1923', '1924', '1925', '1926', '1927', '1928',
    '1929', '1930', '1931', '1932', '1933', '1934', '1935', '1936', '1949',
    '2101', '2102', '2103', '2104', '2105', '2106', '2107', '2108', '2109',
    '2110', '2111', '2112', '2113', '2114', '2115', '2116', '2117', '2118',
    '2119', '2120', '2121', '2122', '2123', '2124', '2125', '2126', '2127',
    '2128', '2151', '2152', '2201', '2202', '2251', '2252', '2351', '2352',
    '2401', '2403', '2406', '2407', '2409', '2501', '2503', '2506', '2507',
    '2509', '2551', '2552', '2553', '2556', '2910', '2911', '2912', '2913',
    '2914', '2915', '2916', '2917', '2918', '2919', '2920', '2929', '2930',
    '2931', '2932', '2933',
    '5101', '5102', '5111', '5113', '5116', '5117', '5118', '5120', '5122',
    '5124', '5125', '5151', '5152', '5201', '5202', '5205', '5209', '5210',
    '5251', '5252', '5258', '5301', '5351', '5401', '5403', '5405', '5407',
    '5409', '5501', '5551', '5601', '5651', '5910', '5919', '5929', '5933',
    '6101', '6102', '6111', '6113', '6116', '6117', '6118', '6120', '6122',
    '6124', '6125', '6151', '6152', '6201', '6202', '6205', '6209', '6210',
    '6251', '6252', '6258', '6301', '6351', '6401', '6403', '6405', '6407',
    '6409', '6501', '6551', '6601', '6651', '6910', '6919', '6929', '6933',
    '7101', '7102', '7111', '7113', '7116', '7117', '7118', '7120', '7122',
    '7124', '7125', '7151', '7152', '7201', '7202', '7205', '7209', '7210',
    '7251', '7252', '7258', '7301', '7351', '7401', '7403', '7405', '7407',
    '7409', '7501', '7551', '7601', '7651', '7910', '7919', '7929', '7933',
}


# ============================================================
# Parser e Validador Principal
# ============================================================

class SintegraValidator:
    def __init__(self, filepath):
        self.filepath = filepath
        self.errors = []
        self.warnings = []
        self.lines = []
        self.records = defaultdict(list)  # tipo -> [(linha_num, parsed_data)]

    def add_error(self, linha, codigo, mensagem):
        self.errors.append({'linha': linha, 'codigo': codigo, 'msg': mensagem})

    def add_warning(self, linha, codigo, mensagem):
        self.warnings.append({'linha': linha, 'codigo': codigo, 'msg': mensagem})

    def validate(self):
        """Executa todas as validações."""
        # 1. Carregar arquivo
        if not self._load_file():
            return False

        # 2. Validar encoding e line endings
        self._check_file_format()

        # 3. Validar tamanho das linhas
        self._check_line_length()

        # 4. Parsear registros
        self._parse_records()

        # 5. Validar registro 10 (cabeçalho)
        self._validate_tipo_10()

        # 6. Validar registro 11 (complementar)
        self._validate_tipo_11()

        # 7. Validar IEs nos registros 50
        self._validate_ie_tipo_50()

        # 8. Validar CFOPs nos registros 50
        self._validate_cfop_tipo_50()

        # 9. Validar tipo 61 (valores pos 62 == pos 107 × 1.000.000)
        self._validate_tipo_61()

        # 10. Validar 61R vs 75 (cross-check)
        self._validate_61r_vs_75()

        # 11. Validar trailer (tipo 90)
        self._validate_tipo_90()

        return len(self.errors) == 0

    def _load_file(self):
        """Carrega o arquivo com encoding latin-1."""
        try:
            # Ler como bytes primeiro para verificar line endings
            with open(self.filepath, 'rb') as f:
                raw = f.read()

            # Verificar CR+LF
            if b'\r\n' in raw:
                self.has_crlf = True
                # Normalizar para leitura
                raw = raw.replace(b'\r\n', b'\n')

            # Tentar ler como latin-1
            try:
                content = raw.decode('latin-1')
            except:
                self.add_error(0, 'ENCODING', 'Arquivo não está em latin-1')
                return False

            self.lines = content.split('\n')
            # Remover linha vazia final se existir
            if self.lines and self.lines[-1] == '':
                self.lines.pop()

            self.total_lines = len(self.lines)
            return True
        except Exception as e:
            self.add_error(0, 'FILE', f'Erro ao ler arquivo: {e}')
            return False

    def _check_file_format(self):
        """Verifica encoding e line endings."""
        if not getattr(self, 'has_crlf', False):
            self.add_error(0, 'CRLF', 'Arquivo NÃO tem line endings CR+LF. Use: sed -i \'s/$/\\r/\' arquivo.TXT')

    def _check_line_length(self):
        """Verifica se todas as linhas têm o tamanho esperado para seu tipo."""
        # Tamanhos esperados por tipo
        # Tipo 88 com EAN pode ter 95 chars; demais tipos usam 126
        for i, line in enumerate(self.lines):
            expected = 126
            # Tipo 88 com EAN (formato "88EAN...") tem layout reduzido (~94 chars)
            if line[:5] == '88EAN':
                expected = 94
            if len(line) != expected:
                self.add_error(i+1, 'TAMANHO',
                    f'Linha tipo "{line[:2]}" tem {len(line)} caracteres (esperado {expected})')

    def _parse_records(self):
        """Parseia cada linha identificando o tipo de registro."""
        for i, line in enumerate(self.lines):
            tipo = line[:2]
            if tipo.isdigit():
                self.records[tipo].append((i+1, line))

            # 61R tem 3 chars
            if line[:3] == '61R':
                self.records['61R'].append((i+1, line))

    def _validate_tipo_10(self):
        """Valida registro tipo 10 (cabeçalho)."""
        for linha, line in self.records.get('10', []):
            if len(line) < 126:
                self.add_error(linha, 'T10-LEN', 'Registro 10 com tamanho incorreto')
                continue

            cnpj = line[2:16]
            ie = line[16:30]

            if not cnpj.isdigit():
                self.add_error(linha, 'T10-CNPJ', f'CNPJ inválido no cabeçalho: {cnpj}')

            # Verificar IE do declarante
            uf = line[38:40].strip()
            if uf and not ie_valid(ie, uf):
                self.add_error(linha, 'T10-IE', f'IE inválida para {uf} no cabeçalho: {ie.strip()}')

    def _validate_tipo_11(self):
        """Valida registro tipo 11 (dados complementares)."""
        for linha, line in self.records.get('11', []):
            if len(line) < 126:
                self.add_error(linha, 'T11-LEN', 'Registro 11 com tamanho incorreto')

    def _validate_ie_tipo_50(self):
        """Valida IEs nos registros tipo 50 (notas fiscais)."""
        for linha, line in self.records.get('50', []):
            if len(line) < 40:
                continue

            ie = line[16:30]
            uf = line[38:40].strip()

            if uf and ie.strip() and ie.strip().isdigit():
                if not ie_valid(ie, uf):
                    cnpj = line[2:16]
                    nf = line[45:51].strip()
                    self.add_error(linha, 'T50-IE',
                        f'IE inválida para {uf}: "{ie.strip()}" (CNPJ: {cnpj}, NF: {nf})')

    def _validate_cfop_tipo_50(self):
        """Valida CFOP nos registros tipo 50."""
        for linha, line in self.records.get('50', []):
            if len(line) < 56:
                continue
            cfop = line[51:55]
            if cfop not in CFOPS_VALIDOS:
                self.add_warning(linha, 'T50-CFOP', f'CFOP possivelmente inválido: {cfop}')

    def _validate_tipo_61(self):
        """Valida registros tipo 61 (resumo diário)."""
        for linha, line in self.records.get('61', []):
            if len(line) < 122:
                continue

            # Só validar 61␣ (com espaço), não 61R
            if line[2:3] != ' ':
                continue

            val_62 = int(line[61:76]) if line[61:76].strip() else 0
            val_107 = int(line[106:121]) if line[106:121].strip() else 0

            # Proporção: val_62 deve ser val_107 × 1.000.000
            if val_107 > 0:
                expected_62 = val_107 * 1_000_000
                if val_62 != expected_62:
                    self.add_error(linha, 'T61-VALOR',
                        f'Valores inconsistentes: pos62={val_62} pos107={val_107} '
                        f'(esperado pos62={expected_62}, diferença={val_62 - expected_62})')

    def _validate_61r_vs_75(self):
        """Valida que cada 61R tem um registro 75 correspondente.

        Lógica: Para cada base 61R, tenta encontrar a base 75 correspondente
        comparando os dígitos não-zero de ambas. Se encontrou correspondência,
        TODOS os produtos daquela base 61R precisam ter registro 75.
        """
        # Coletar produtos do tipo 75: base10 → set de sufixos 4 chars (pos 28-31)
        sufixos_75 = defaultdict(set)
        for linha, line in self.records.get('75', []):
            if len(line) < 32:
                continue
            base10 = line[18:28]
            sufixo4 = line[28:32]
            sufixos_75[base10].add(sufixo4)

        # Agrupar 61R por base
        r61r_por_base = defaultdict(list)
        for linha, line in self.records.get('61R', []):
            if len(line) < 26:
                continue
            base = line[11:21]
            prod = line[21:26]
            if prod.strip().isdigit():
                r61r_por_base[base].append((linha, prod))

        # Função para extrair dígitos não-zero (identificador da base)
        def base_key(b):
            return b.replace('0', '')

        # Mapear bases 75 por sua "key"
        base75_por_key = {}
        for b75 in sufixos_75:
            key = base_key(b75)
            base75_por_key[key] = b75

        # Para cada base 61R, encontrar base 75 correspondente
        for base_61r, items in r61r_por_base.items():
            key = base_key(base_61r)
            base_75_match = base75_por_key.get(key)

            # Se encontrou base 75 correspondente, validar TODOS os produtos
            if base_75_match:
                sufs_75_matched = sufixos_75[base_75_match]
                for linha, prod in items:
                    prod_num = int(prod) // 1000
                    sufixo = f"{prod_num:04d}"
                    if sufixo not in sufs_75_matched:
                        self.add_error(linha, '61R-NO75',
                            f'Registro 61R sem tipo 75 correspondente: '
                            f'base={base_61r} produto={prod} '
                            f'(esperado {base_75_match}{sufixo} nos 75)')

    def _validate_tipo_90(self):
        """Valida o trailer (tipo 90)."""
        for linha, line in self.records.get('90', []):
            if len(line) < 90:
                self.add_error(linha, 'T90-LEN', 'Trailer com tamanho incorreto')
                continue

            # Decodificar bloco de contagens (pos 30-89, 60 chars, 6 grupos de 10)
            bloco = line[30:90]
            counts = {}
            for i in range(0, 60, 10):
                g = bloco[i:i+10]
                tipo = g[:2]
                count = int(g[2:])
                counts[tipo] = count

            # Verificar contagens contra registros reais
            expected = {
                '50': len(self.records.get('50', [])),
                '54': len(self.records.get('54', [])),
                # Tipo 61 no trailer conta todos que começam com "61" (61␣ + 61R)
                '61': len(self.records.get('61', [])),
                '75': len(self.records.get('75', [])),
                '88': len(self.records.get('88', [])),
            }

            for tipo, esperado in expected.items():
                real = counts.get(tipo)
                if real is not None and real != esperado:
                    self.add_error(linha, 'T90-COUNT',
                        f'Trailer: tipo {tipo} declara {real} mas arquivo tem {esperado}')

            # Verificar total de linhas
            total_declarado = counts.get('99')
            if total_declarado is not None and total_declarado != self.total_lines:
                self.add_error(linha, 'T90-LINES',
                    f'Trailer declara {total_declarado} linhas mas arquivo tem {self.total_lines}')

    def print_report(self):
        """Imprime relatório de validação."""
        print(f"\n{'='*60}")
        print(f"VALIDAÇÃO SINTEGRA: {os.path.basename(self.filepath)}")
        print(f"{'='*60}")
        print(f"Linhas: {self.total_lines}")
        print(f"Tipos de registro: ", end="")
        tipos = []
        for t in sorted(self.records.keys()):
            tipos.append(f"{t}={len(self.records[t])}")
        print(", ".join(tipos))
        print(f"CR+LF: {'✅ Sim' if getattr(self, 'has_crlf', False) else '❌ Não'}")

        if self.errors:
            print(f"\n❌ {len(self.errors)} ERRO(S) encontrado(s):")
            for err in self.errors:
                print(f"  Linha {err['linha']:>4} [{err['codigo']}] {err['msg']}")

        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} AVISO(S):")
            for w in self.warnings:
                print(f"  Linha {w['linha']:>4} [{w['codigo']}] {w['msg']}")

        if not self.errors:
            print(f"\n✅ ARQUIVO VÁLIDO! Nenhum erro encontrado.")

        return len(self.errors)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 validar_sintegra.py <arquivo.TXT> [--auto-fix]")
        sys.exit(1)

    filepath = sys.argv[1]
    auto_fix = '--auto-fix' in sys.argv

    if not os.path.exists(filepath):
        print(f"Erro: arquivo não encontrado: {filepath}")
        sys.exit(1)

    validator = SintegraValidator(filepath)
    is_valid = validator.validate()
    validator.print_report()

    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
