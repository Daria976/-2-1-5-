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


