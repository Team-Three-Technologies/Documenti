import re
import argparse
import sys
from pathlib import Path
from typing import Set, List, Dict
from pathlib import PurePosixPath

class GlossaryHighlighter:
    def __init__(self):
        self.excluded_commands = [
            'section', 'subsection', 'subsubsection',
            'chapter', 'paragraph', 'subparagraph',
            'title', 'author', 'date',
            'caption', 'label', 'ref', 'cite',
            'setTitle', 'setAuthors', 'setVerificators',
            'setApprovation', 'setVersion', 'setType', 'setDestination',
            'url', 'href', 'autoref', 'nameref', 'usepackage', 'documentclass'
        ]
        self.glossary_terms: Set[str] = set()
        self.acronyms: Dict[str, str] = {}

    def extract_glossary_terms(self, glossary_file: str) -> None:
        try:
            with open(glossary_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"ERRORE: File glossario non trovato: {glossary_file}")
            sys.exit(1)
        
        term_pattern = r'\\item\s+\\textbf\{([^}]+)\}'
        
        for match in re.finditer(term_pattern, content):
            term = match.group(1).strip()
            self.glossary_terms.add(term)
            
            context_start = match.end()
            context = content[context_start:context_start+200]
            acronym_pattern = r'Acronimo di ([^,\\.]+)'
            acronym_match = re.search(acronym_pattern, context)
            if acronym_match:
                full_term = acronym_match.group(1).strip()
                self.acronyms[term] = full_term
                self.glossary_terms.add(full_term)
        
        print(f"Trovati {len(self.glossary_terms)} termini nel glossario:")
        for term in sorted(self.glossary_terms):
            acronym_info = ""
            if term in self.acronyms:
                acronym_info = f" (acronimo di: {self.acronyms[term]})"
            print(f"  - {term}{acronym_info}")

    def is_in_excluded_context(self, text: str, pos: int, debug: bool = False) -> bool:
        line_start = text.rfind('\n', 0, pos) + 1
        line_text = text[line_start:pos]
        
        line_end = text.find('\n', pos)
        if line_end == -1:
            line_end = len(text)
        line_full = text[line_start:line_end]
        
        if line_full.lstrip().startswith('%'):
            if debug:
                print(f"      [DEBUG] Escluso: riga commento")
            return True
        
        comment_match = re.search(r'(?<!\\)%', line_text)
        if comment_match:
            if debug:
                print(f"      [DEBUG] Escluso: commento inline")
            return True
        
        open_brace_count = 0
        i = len(line_text) - 1
        while i >= 0:
            if line_text[i] == '}':
                open_brace_count += 1
            elif line_text[i] == '{':
                open_brace_count -= 1
                if open_brace_count < 0:
                    before_brace = line_text[:i].rstrip()
                    for cmd in self.excluded_commands:
                        if before_brace.endswith(f'\\{cmd}'):
                            if debug:
                                print(f"      [DEBUG] Escluso: dentro comando \\{cmd}")
                                print(f"      [DEBUG] line_text: {repr(line_text)}")
                            return True
                    break
            i -= 1
        
        before_text = text[:pos]
        
        table_environments = ['tabularx', 'longtable', 'xltabular', 'table']
        list_environments = ['itemize', 'enumerate', 'description']
        custom_environments = ['usecase']
        
        for env in table_environments:
            begins = list(re.finditer(rf'\\begin\{{{env}\}}', before_text))
            ends = list(re.finditer(rf'\\end\{{{env}\}}', before_text))
            
            nesting_level = len(begins) - len(ends)
            
            if nesting_level > 0:
                if debug:
                    print(f"      [DEBUG] Escluso: dentro ambiente {env}")
                    print(f"      [DEBUG] Nesting level: {nesting_level}")
                return True
        
        for env in list_environments:
            begins = list(re.finditer(rf'\\begin\{{{env}\}}', before_text))
            ends = list(re.finditer(rf'\\end\{{{env}\}}', before_text))
            
            nesting_level = len(begins) - len(ends)
            
            if nesting_level > 0:
                if debug:
                    print(f"      [DEBUG] Escluso: dentro ambiente {env}")
                    print(f"      [DEBUG] Nesting level: {nesting_level}")
                return True
        
        for env in custom_environments:
            begins = list(re.finditer(rf'\\begin\{{{env}\}}', before_text))
            ends = list(re.finditer(rf'\\end\{{{env}\}}', before_text))
            
            nesting_level = len(begins) - len(ends)
            
            if nesting_level > 0:
                if debug:
                    print(f"      [DEBUG] Escluso: dentro ambiente {env}")
                    print(f"      [DEBUG] Nesting level: {nesting_level}")
                return True
        
        return False

    def is_properly_isolated(self, text: str, pos: int, term_len: int) -> bool:
        if pos > 0:
            char_before = text[pos - 1]
            if char_before.isalnum() or char_before in '/_:-':
                return False
        
        pos_after = pos + term_len
        if pos_after < len(text):
            char_after = text[pos_after]
            if char_after.isalnum() or char_after in '/_:-':
                return False
        
        return True

    def is_already_marked(self, text: str, match_pos: int, term: str) -> bool:
        check_end = match_pos + len(term) + 20
        following_text = text[match_pos:check_end]
        return r'\textsubscript{G}' in following_text

    def highlight_terms(self, input_file: str, output_file: str = None, dry_run: bool = False, debug: bool = False) -> int:
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"AVVISO: File non trovato: {input_file}")
            return 0
        
        original_content = content
        modifications = []
        sorted_terms = sorted(self.glossary_terms, key=len, reverse=True)
        
        for term in sorted_terms:
            pattern = rf'\b{re.escape(term)}\b'
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            
            if debug and matches:
                print(f"\n[DEBUG] Termine '{term}': trovate {len(matches)} occorrenze")
            
            for match in reversed(matches):
                pos = match.start()
                matched_term = match.group(0)
                
                if debug:
                    line_num = content[:pos].count('\n') + 1
                    print(f"  [DEBUG] Occorrenza '{matched_term}' a riga {line_num}")
                
                if self.is_in_excluded_context(content, pos, debug):
                    if debug:
                        print(f"    [DEBUG] -> SALTATO: contesto escluso")
                    continue
                
                if not self.is_properly_isolated(content, pos, len(matched_term)):
                    if debug:
                        print(f"    [DEBUG] -> SALTATO: non isolato (in URL o path)")
                    continue
                
                if self.is_already_marked(content, pos, matched_term):
                    if debug:
                        print(f"    [DEBUG] -> SALTATO: già marcato")
                    continue
                
                replacement = matched_term + r'\textsubscript{G}'
                content = content[:pos] + replacement + content[pos + len(matched_term):]
                
                line_num = content[:pos].count('\n') + 1
                modifications.append(f"Riga {line_num}: '{matched_term}' -> '{replacement}'")
                if debug:
                    print(f"    [DEBUG] -> MARCATO")
        
        if modifications:
            print(f"\nTrovate {len(modifications)} occorrenze da evidenziare in {input_file}:")
            for mod in modifications:
                print(f"  {mod}")
        else:
            print(f"\nNessuna modifica necessaria in {input_file}")
        
        if not dry_run and content != original_content:
            output_path = output_file or input_file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"File salvato: {output_path}")
        elif dry_run:
            print("[DRY RUN] Nessun file modificato")
        
        return len(modifications)

def is_excluded(filepath: str, exclude_patterns: list) -> bool:
    filepath_normalized = filepath.replace('\\', '/').lstrip('./')
    p = PurePosixPath(filepath_normalized)
    
    for pattern in exclude_patterns:
        pattern_normalized = pattern.replace('\\', '/').lstrip('./')
        
        if p.match(pattern_normalized):
            return True
        
        folder = pattern_normalized.rstrip('/*')
        if folder and folder in p.parts:
            return True
    
    return False

def find_glossary_file():
    matches = list(Path('.').rglob('Glossario_v*.tex'))
    if matches:
        matches.sort()
        glossary_file = str(matches[-1])
        print(f"Glossario trovato: {glossary_file}")
        return glossary_file
    
    return None

def main():
    parser = argparse.ArgumentParser(description='Evidenzia i termini del glossario nei documenti LaTeX')
    parser.add_argument('glossary', nargs='?', help='File del glossario (es: Glossario.tex o Glossario_v0_1.tex). Se omesso, cerca automaticamente.')
    parser.add_argument('files', nargs='*', help='File LaTeX da processare (se omesso, cerca tutti i .tex)')
    parser.add_argument('-o', '--output-suffix', default='', help='Suffisso da aggiungere ai file di output')
    parser.add_argument('--exclude-files', nargs='*', default=[], help='File da escludere dal processing')
    parser.add_argument('--dry-run', action='store_true', help='Mostra le modifiche senza salvare i file')
    parser.add_argument('--debug', action='store_true', help='Mostra informazioni di debug dettagliate')
    
    args = parser.parse_args()
    
    if not args.glossary:
        args.glossary = find_glossary_file()
        if not args.glossary:
            print("ERRORE: Nessun file glossario trovato!")
            print("Cerca file come: Glossario.tex, Glossario_v0_1.tex, ecc.")
            sys.exit(1)
    
    highlighter = GlossaryHighlighter()
    
    print("=" * 60)
    print("ESTRAZIONE TERMINI DAL GLOSSARIO")
    print("=" * 60)
    highlighter.extract_glossary_terms(args.glossary)
    
    if not args.files:
        tex_files = list(Path('.').rglob('*.tex'))
        args.files = [
            str(f) for f in tex_files
            if f.name != Path(args.glossary).name
            and not is_excluded(str(f), args.exclude_files)
        ]
        print(f"\nTrovati {len(args.files)} file .tex da processare")
    
    print("\n" + "=" * 60)
    print("ELABORAZIONE DOCUMENTI")
    print("=" * 60)
    
    total_modifications = 0
    
    for input_file in args.files:
        print(f"\n--- Processando: {input_file} ---")
        
        if args.output_suffix:
            input_path = Path(input_file)
            output_file = str(input_path.parent / f"{input_path.stem}{args.output_suffix}{input_path.suffix}")
        else:
            output_file = None
        
        mods = highlighter.highlight_terms(input_file, output_file, args.dry_run, args.debug)
        total_modifications += mods
    
    print("\n" + "=" * 60)
    print("COMPLETATO")
    print("=" * 60)
    print(f"Totale modifiche: {total_modifications}")
    
    sys.exit(0)


if __name__ == '__main__':
    main()