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
