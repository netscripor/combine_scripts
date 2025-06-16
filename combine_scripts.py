#!/usr/bin/env python3
"""
Obsidian-ready ревью-кобинатор: объединяет все текстовые файлы из каталога в markdown-отчёт,
делает структуру для Obsidian (заголовки, блоки кода с нужным языком), красивые линии, ls -lR и tree.
"""

import os
import argparse
import subprocess

# Карта расширений → языка для markdown
EXT_LANG = {
    '.py': 'python',
    '.sh': 'bash',
    '.js': 'javascript',
    '.html': 'html',
    '.css': 'css',
    '.php': 'php',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.ini': 'ini',
    '.service': 'ini',
    '.timer': 'ini',
}

def is_hidden(path):
    return any(part.startswith('.') for part in path.split(os.sep) if part)

def write_ls_lr(input_dir, outfile):
    try:
        ls_output = subprocess.check_output(['ls', '-lR', input_dir], encoding='utf-8', errors='replace')
        outfile.write("\n\n```\n")
        outfile.write(ls_output)
        outfile.write("\n```\n")
    except Exception as e:
        outfile.write(f"\n\n```\n[!] Ошибка при получении ls -lR: {str(e)}\n```\n")

def write_tree(input_dir, outfile):
    try:
        tree_output = subprocess.check_output(['tree', '-a', '-I', '.*', input_dir], encoding='utf-8', errors='replace')
        outfile.write("\n\n```\n")
        outfile.write(tree_output)
        outfile.write("\n```\n")
    except Exception as e:
        outfile.write(f"\n\n```\n[!] Ошибка при получении tree: {str(e)}\n```\n")

def should_exclude(rel_path, exclude_dirs_set):
    rel_path = rel_path.replace("\\", "/")
    for excl in exclude_dirs_set:
        excl = excl.replace("\\", "/")
        if rel_path == excl or rel_path.startswith(excl + "/"):
            return True
    return False

def escape_filename(name):
    """Экранирует [скобки] и пробелы для Obsidian."""
    if "[" in name or "]" in name or " " in name:
        return f"`{name}`"
    return name

def combine_scripts(input_dir, output_file, extensions=None, with_ls=False, with_tree=False, exclude_dirs=None):
    if extensions is not None:
        extensions = [e.lower() for e in extensions]
    if exclude_dirs is None:
        exclude_dirs = []
    exclude_dirs_set = set(os.path.normpath(d).replace("\\", "/") for d in exclude_dirs)
    input_dir_abs = os.path.abspath(input_dir)

    total_files, skipped_files = 0, 0
    sep = "=" * 40  # Укороченная линия

    with open(output_file, 'w', encoding='utf-8') as outfile:
        if with_tree:
            outfile.write("\n\n" + sep + "\n")
            outfile.write("**tree:**\n")
            write_tree(input_dir, outfile)
            outfile.write(sep + "\n")
        if with_ls:
            outfile.write("\n\n" + sep + "\n")
            outfile.write("**ls -lR:**\n")
            write_ls_lr(input_dir, outfile)
            outfile.write(sep + "\n")

        for root, dirs, files in os.walk(input_dir_abs):
            rel_root = os.path.relpath(root, input_dir_abs).replace("\\", "/")
            if rel_root == ".":
                rel_root = ""
            if should_exclude(rel_root, exclude_dirs_set):
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not is_hidden(d) and not should_exclude(os.path.join(rel_root, d), exclude_dirs_set)]
            if is_hidden(rel_root):
                continue

            # Markdown/Obsidian header
            outfile.write(f"\n\n{'#'*3 if rel_root else '#'} {rel_root if rel_root else os.path.basename(input_dir_abs)}\n")
            outfile.write(sep + "\n")

            for file in sorted(files):
                if is_hidden(file):
                    continue
                if extensions is not None and not any(file.lower().endswith(ext) for ext in extensions):
                    continue
                file_path = os.path.join(root, file)
                rel_file = os.path.join(rel_root, file) if rel_root else file
                rel_file_md = escape_filename(rel_file)
                ext = os.path.splitext(file)[-1].lower()
                lang = EXT_LANG.get(ext, '')

                # --- блок с минусами (обязательно переносы) ---
                outfile.write("\n\n---\n\n")
                outfile.write(f"**Файл:** {rel_file_md}\n\n")
                outfile.write("---\n\n")

                # --- Код ---
                outfile.write(f"```{lang}\n")
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                        total_files += 1
                except UnicodeDecodeError:
                    msg = f"[!] Не удалось прочитать файл (не текст, возможно бинарник): {file_path}\n"
                    print(msg.strip())
                    outfile.write(msg)
                    skipped_files += 1
                except Exception as e:
                    msg = f"[!] Ошибка при обработке файла {file_path}: {str(e)}\n"
                    print(msg.strip())
                    outfile.write(msg)
                    skipped_files += 1
                outfile.write("\n```\n")

        outfile.write("\n" + sep + "\n")
        outfile.write(f"[Отчет] Всего файлов добавлено: {total_files}, пропущено: {skipped_files}\n")
        outfile.write(sep + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Объединяет содержимое всех скриптов в директории в один markdown-отчёт для Obsidian')
    parser.add_argument('input_dir', help='Путь к корневой директории с исходниками')
    parser.add_argument('output_file', help='Имя выходного файла')
    parser.add_argument('--ext', nargs='+', default=['.py', '.sh', '.yaml', '.js', '.html', '.css', '.php', '.service', '.timer'],
                        help='Расширения файлов для включения (можно несколько)')
    parser.add_argument('--ls', action='store_true', help='Добавить вывод ls -lR в начало итогового файла')
    parser.add_argument('--tree', action='store_true', help='Добавить вывод tree в начало итогового файла')
    parser.add_argument('--exclude', nargs='+', default=[], help='Директории для исключения (относительно input_dir)')

    args = parser.parse_args()

    print(f"[i] Обрабатываю директорию: {args.input_dir}")
    print(f"[i] Сохраняю результат в: {args.output_file}")
    print(f"[i] Ищу файлы с расширениями: {args.ext}")
    if args.ls:
        print("[i] Добавляю ls -lR в отчет")
    if args.tree:
        print("[i] Добавляю tree в отчет")
    if args.exclude:
        print(f"[i] Исключаю директории: {args.exclude}")

    combine_scripts(args.input_dir, args.output_file, args.ext, with_ls=args.ls, with_tree=args.tree, exclude_dirs=args.exclude)
    print("[✓] Готово!")

# Пример запуска:

"""
./combine_scripts.py ./nids nids_review.txt \
    --ext .py .js .sh \
    --ls \
    --tree \
    --exclude venv .git __pycache__ build
"""
