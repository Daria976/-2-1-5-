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
