# -2-1-5-
//Этап 1 — Загрузка графа зависимостей
//depvis_stage1.py
import argparse
import xml.etree.ElementTree as ET
import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Set


def load_config(xml_path: str) -> Dict[str, str]:
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"Config file not found: {xml_path}")
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse XML config: {e}")

    def get_text(tag: str, required=True, default=""):
        el = root.find(tag)
        if el is None:
            if required:
                raise ValueError(f"Missing required config element: <{tag}>")
            return default
        return (el.text or "").strip()

    cfg = {
        "package": get_text("package"),
        "repository": get_text("repository"),
        "repo_mode": get_text("repo_mode", required=False, default="file"),
        "package_version": get_text("package_version", required=False, default=""),
        "output_mode": get_text("output_mode", required=False, default="ascii_tree"),
    }
    return cfg


def parse_test_repo(path: str, mode: str) -> Dict[str, List[str]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Repository/test-repo file not found: {path}")

    deps: Dict[str, List[str]] = {}
    if mode.lower() == "json" or path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if v is None or v == "":
                deps[k.strip()] = []
            elif isinstance(v, list):
                deps[k.strip()] = [s.strip() for s in v if s and s.strip()]
            else:
                deps[k.strip()] = [s.strip() for s in str(v).split(",") if s.strip()]
    else:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" not in line:
                    # treat as package with no deps
                    name = line.strip()
                    deps[name] = deps.get(name, [])
                    continue
                name, rest = line.split(":", 1)
                name = name.strip()
                items = [s.strip() for s in rest.split(",") if s.strip()]
                deps[name] = items
    return deps


def build_ascii_tree(root_pkg: str, deps_map: Dict[str, List[str]]) -> str:
    visited: Set[str] = set()
    lines: List[str] = []

    def dfs(pkg: str, prefix: str, is_last: bool):
        marker = "└─ " if is_last else "├─ "
        if prefix == "":
            lines.append(pkg)
        else:
            lines.append(prefix + marker + pkg)
        if pkg in visited:
            lines.append(prefix + ("   " if is_last else "│  ") + "(cycle detected)")
            return
        visited.add(pkg)
        children = deps_map.get(pkg, [])
        for i, child in enumerate(children):
            last = (i == len(children) - 1)
            new_prefix = prefix + ("   " if is_last else "│  ")
            dfs(child, new_prefix, last)

    dfs(root_pkg, "", True)
    return "\n".join(lines)


def save_and_commit(output_text: str, repo_path: str, package: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"dependency_tree_{package}_{timestamp}.txt"

    target_dir = repo_path if os.path.isdir(repo_path) else os.path.dirname(os.path.abspath(repo_path)) or "."

    out_path = os.path.join(target_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output_text)

    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
       
        res = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=target_dir,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and res.stdout.strip() == "true":
            subprocess.run(["git", "add", filename], cwd=target_dir, check=True)
            commit_msg = f"Add dependency tree for {package} at {timestamp}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=target_dir, check=True)
            return f"Saved and committed as {out_path}"
        else:
            commit_note = os.path.join(target_dir, ".commit.txt")
            with open(commit_note, "a", encoding="utf-8") as c:
                c.write(f"{timestamp} - created {filename}\n")
            return f"Saved to {out_path} (not a git repo; wrote .commit.txt)"
    except FileNotFoundError:
        commit_note = os.path.join(target_dir, ".commit.txt")
        with open(commit_note, "a", encoding="utf-8") as c:
            c.write(f"{timestamp} - created {filename} (git not found)\n")
        return f"Saved to {out_path} (git not available; wrote .commit.txt)"
    except subprocess.CalledProcessError as e:
        commit_note = os.path.join(target_dir, ".commit.txt")
        with open(commit_note, "a", encoding="utf-8") as c:
            c.write(f"{timestamp} - created {filename} (git error: {e})\n")
        return f"Saved to {out_path} (git error; wrote .commit.txt)"


def main():
    parser = argparse.ArgumentParser(description="Минимальный прототип визуализации графа зависимостей (этап 1).")
    parser.add_argument("--config", "-c", required=True, help="Путь к XML конфигу.")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    print("Параметры (ключ=значение):")
    for k, v in cfg.items():
        print(f"{k}={v}")

    pkg = cfg["package"]
    repo = cfg["repository"]
    mode = cfg["repo_mode"]
    version = cfg["package_version"]
    out_mode = cfg["output_mode"]

    if not pkg:
        print("ERROR: package name is empty.", file=sys.stderr)
        sys.exit(3)
    if not repo:
        print("ERROR: repository path/url is empty.", file=sys.stderr)
        sys.exit(3)
    if out_mode.lower() != "ascii_tree":
        print(f"WARNING: output_mode '{out_mode}' not recognized; defaulting to ascii_tree.")
        out_mode = "ascii_tree"

    try:
        deps_map = parse_test_repo(repo, mode)
    except Exception as e:
        print(f"ERROR reading test repository: {e}", file=sys.stderr)
        sys.exit(4)

    if pkg not in deps_map:
        print(f"WARNING: package '{pkg}' not found in test repository. It will be shown as leaf.")
        deps_map.setdefault(pkg, [])

    try:
        ascii_output = build_ascii_tree(pkg, deps_map)
    except Exception as e:
        print(f"ERROR building ASCII tree: {e}", file=sys.stderr)
        sys.exit(5)

    print("\n=== ASCII Dependency Tree ===")
    print(ascii_output)
    print("=== End ===\n")

    try:
        msg = save_and_commit(ascii_output, repo, pkg)
        print(msg)
    except Exception as e:
        print(f"ERROR saving/committing result: {e}", file=sys.stderr)
        sys.exit(6)

if __name__ == "__main__":
    main()

//Вывод программы:
=== ASCII Dependency Tree ===
my-package
   ├─ libA
   │  └─ libC
   └─ libB
      ├─ libC
      │  (cycle detected)
      └─ libD
         └─ libE
=== End ===



//Этап 2 — Поиск зависимостей
//depvis_stage2.py
import argparse
import xml.etree.ElementTree as ET
import os
import sys
import urllib.request
import tarfile
import io
import gzip

def load_config(xml_path: str):
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"Config not found: {xml_path}")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    cfg = {tag.tag: tag.text.strip() for tag in root if tag.text}
    return cfg

def download_apkindex(repo_url: str) -> bytes:
    
    if not repo_url.endswith("/"):
        repo_url += "/"
    url = repo_url + "APKINDEX.tar.gz"
    print(f"Скачиваем индекс: {url}")
    with urllib.request.urlopen(url) as r:
        return r.read()

def parse_apkindex(data: bytes):
    packages = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.name == "APKINDEX":
                f = tar.extractfile(member)
                content = f.read().decode("utf-8", errors="ignore")
                break
        else:
            raise ValueError("В архиве нет файла APKINDEX")

    entries = content.strip().split("\n\n")
    for entry in entries:
        pkg = {}
        for line in entry.splitlines():
            if not line.strip():
                continue
            key, val = line.split(":", 1)
            pkg[key] = val.strip()
        if "P" in pkg:  # имя пакета
            name = pkg["P"]
            packages[name] = {
                "version": pkg.get("V", ""),
                "depends": pkg.get("D", "").split() if "D" in pkg else []
            }
    return packages

def main():
    parser = argparse.ArgumentParser(description="Этап 2: Сбор данных о зависимостях Alpine пакетов.")
    parser.add_argument("--config", "-c", required=True, help="Путь к XML конфигу.")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"Ошибка чтения конфига: {e}", file=sys.stderr)
        sys.exit(1)

    package = cfg.get("package")
    repo = cfg.get("repository")
    version = cfg.get("package_version")

    if not package or not repo:
        print("Укажите package и repository в config.xml")
        sys.exit(2)

    try:
        raw_data = download_apkindex(repo)
    except Exception as e:
        print(f"Не удалось скачать APKINDEX: {e}")
        sys.exit(3)

    try:
        packages = parse_apkindex(raw_data)
    except Exception as e:
        print(f"Ошибка при разборе APKINDEX: {e}")
        sys.exit(4)

    if package not in packages:
        print(f"Пакет {package} не найден в репозитории")
        sys.exit(0)

    pkginfo = packages[package]
    deps = pkginfo["depends"]
    print(f"\nПакет: {package}")
    print(f"Версия: {pkginfo['version']}")
    print(f"Прямые зависимости ({len(deps)}):")
    for dep in deps:
        print(f"  - {dep}")

    with open(f"{package}_deps.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(deps))

    print(f"\nСписок зависимостей сохранён в {package}_deps.txt")

if __name__ == "__main__":
    main()

    
//Вывод программы:
Скачиваем индекс: https://dl-cdn.alpinelinux.org/alpine/v3.18/main/x86_64/APKINDEX.tar.gz

Пакет: bash
Версия: 5.2.15-r5
Прямые зависимости (3):
  - /bin/sh
  - so:libc.musl-x86_64.so.1
  - so:libreadline.so.8

Список зависимостей сохранён в bash_deps.txt




//Этап 3 — Визуализация в Graphviz
//depvis_stage3.py

import argparse
from collections import deque, defaultdict

def load_graph(file_path: str):
    graph = defaultdict(list)
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            pkg, deps = line.split(":", 1)
            pkg = pkg.strip().upper()
            deps_list = [d.strip().upper() for d in deps.split() if d.strip()]
            graph[pkg].extend(deps_list)
    return graph


def bfs_dependencies(graph, start):
    visited = set()
    queue = deque([start])
    order = []

    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        order.append(node)

        for dep in graph.get(node, []):
            if dep not in visited:
                queue.append(dep)
    return order


def detect_cycles(graph):
    visited = set()
    stack = set()

    def visit(node):
        if node in stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        stack.add(node)
        for dep in graph[node]:
            if visit(dep):
                return True
        stack.remove(node)
        return False

    for node in graph:
        if visit(node):
            return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Этап 3: построение графа зависимостей (BFS)")
    parser.add_argument("--graph", "-g", required=True, help="Путь к файлу графа зависимостей (режим тестирования)")
    parser.add_argument("--start", "-s", required=True, help="Имя пакета, с которого начинать обход")
    args = parser.parse_args()

    graph = load_graph(args.graph)

    print("Граф зависимостей:")
    for k, v in graph.items():
        print(f"{k}: {', '.join(v) if v else '-'}")

    if detect_cycles(graph):
        print("\nОбнаружены циклические зависимости!")
    else:
        print("\nЦиклические зависимости отсутствуют.")

    deps = bfs_dependencies(graph, args.start)
    print(f"\nПорядок обхода зависимостей для {args.start}:")
    print(" → ".join(deps))
    with open("bash_deps.txt", "w", encoding="utf-8") as f:
        f.write(f"Результат обхода зависимостей от {args.start}:\n")
        f.write(" -> ".join(deps))
    print('\nРезультат сохранён в bash_deps.txt')

if __name__ == "__main__":
    main()


//Вывод программы:
Граф зависимостей:
A: B, C
B: D
C: D, E
D: E
E: -

Циклические зависимости отсутствуют.

Порядок обхода зависимостей для A:
A → B → C → D → E

Результат сохранён в bash_deps.txt



//Этап 4 — ASCII-граф
//depvis_stage4.py
import argparse
from collections import deque

def load_graph(filename):
    graph = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                key, values = line.strip().split(":")
                graph[key.strip()] = values.strip().split() if values.strip() else []
    return graph

def reverse_graph(graph):
    reversed_graph = {node: [] for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            reversed_graph[dep].append(node)
    return reversed_graph

def bfs_dependencies(graph, start):
    visited = set()
    queue = deque([start])
    order = []

    while queue:
        node = queue.popleft()
        if node not in visited:
            visited.add(node)
            order.append(node)
            queue.extend(graph.get(node, []))
    return order

def main():
    parser = argparse.ArgumentParser(description="Анализ графа зависимостей")
    parser.add_argument("--graph", "-g", required=True, help="Файл с описанием графа зависимостей")
    parser.add_argument("--start", "-s", required=True, help="Начальный пакет для обхода")
    parser.add_argument("--reverse", action="store_true", help="Включить режим обратных зависимостей")

    args = parser.parse_args()

    graph = load_graph(args.graph)
    print("\nЗагруженный граф зависимостей:")
    for k, v in graph.items():
        print(f"{k}: {' '.join(v)}")

    if args.reverse:
        print("\nРежим: обратные зависимости")
        graph = reverse_graph(graph)
    else:
        print("\nРежим: прямые зависимости")

    deps = bfs_dependencies(graph, args.start.upper())

    print(f"\nПорядок обхода зависимостей для {args.start.upper()}:")
    print(" → ".join(deps))

    with open("bash_deps.txt", "w", encoding="utf-8") as f:
        f.write(f"Результат обхода зависимостей для {args.start.upper()} ({'обратный' if args.reverse else 'прямой'}):\n")
        f.write(" → ".join(deps))
    print("\nРезультат сохранён в bash_deps.txt")

if __name__ == "__main__":
    main()

//Вывод программы:
Загруженный граф зависимостей:
A: B C
B: D
C: D E
D: E
E:

Режим: обратные зависимости

Порядок обхода зависимостей для E:
E → C → D → A → B

Результат сохранён в bash_deps.txt



//Этап 5 — Полноценная CLI-утилита
//depvis_stage5.py

import argparse
from collections import deque
import graphviz

def load_graph(filename):
    graph = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                key, values = line.strip().split(":")
                graph[key.strip()] = values.strip().split() if values.strip() else []
    return graph

def reverse_graph(graph):
    reversed_graph = {node: [] for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            reversed_graph[dep].append(node)
    return reversed_graph

def bfs_dependencies(graph, start):
    visited = set()
    queue = deque([start])
    order = []

    while queue:
        node = queue.popleft()
        if node not in visited:
            visited.add(node)
            order.append(node)
            queue.extend(graph.get(node, []))
    return order

def create_graphviz(graph, output_file, reverse=False):
    dot = graphviz.Digraph(comment="Граф зависимостей", format="png")
    for node, deps in graph.items():
        for dep in deps:
            if reverse:
                dot.edge(dep, node)
            else:
                dot.edge(node, dep)
    dot.render(output_file, view=True)
    print(f"\nФайл визуализации сохранён как {output_file}.png")

def print_ascii_tree(graph, start, prefix="", visited=None):
    if visited is None:
        visited = set()
    if start in visited:
        print(prefix + start + " (циклическая зависимость)")
        return
    print(prefix + start)
    visited.add(start)
    for dep in graph.get(start, []):
        print_ascii_tree(graph, dep, prefix + "   ", visited)

def main():
    parser = argparse.ArgumentParser(description="Визуализация графа зависимостей")
    parser.add_argument("--graph", "-g", required=True, help="Файл с описанием графа зависимостей")
    parser.add_argument("--start", "-s", required=True, help="Начальный пакет")
    parser.add_argument("--reverse", action="store_true", help="Режим обратных зависимостей")
    parser.add_argument("--ascii", action="store_true", help="Вывод зависимостей в виде ASCII-дерева")

    args = parser.parse_args()

    graph = load_graph(args.graph)
    print("\nЗагруженный граф зависимостей:")
    for k, v in graph.items():
        print(f"{k}: {' '.join(v)}")

    if args.reverse:
        print("\nРежим: обратные зависимости")
        graph = reverse_graph(graph)
    else:
        print("\nРежим: прямые зависимости")

    deps = bfs_dependencies(graph, args.start.upper())
    print(f"\nПорядок обхода зависимостей для {args.start.upper()}:")
    print(" → ".join(deps))

    if args.ascii:
        print("\nЗависимости в виде ASCII-дерева:")
        print_ascii_tree(graph, args.start.upper())

    create_graphviz(graph, "dependency_graph", reverse=args.reverse)

    with open("bash_deps.txt", "w", encoding="utf-8") as f:
        f.write(f"Результат для {args.start.upper()} ({'обратный' if args.reverse else 'прямой'}):\n")
        f.write(" → ".join(deps))
    print("\nРезультат сохранён в bash_deps.txt")

if __name__ == "__main__":
    main()

    

//Вывод программы:
Загруженный граф зависимостей:
A: B C
B: D
C: D E
D:
E:

Режим: прямые зависимости

Порядок обхода зависимостей для A:
A → B → C → D → E

Файл визуализации сохранён как dependency_graph.png

Результат сохранён в bash_deps.txt
