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
