import argparse
from collections import deque
import graphviz





# ======== Загрузка графа ========
def load_graph(filename):
    graph = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                key, values = line.strip().split(":")
                graph[key.strip()] = values.strip().split() if values.strip() else []
    return graph

# ======== Обратный граф ========
def reverse_graph(graph):
    reversed_graph = {node: [] for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            reversed_graph[dep].append(node)
    return reversed_graph

# ======== BFS обход ========
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

# ======== Построение Graphviz диаграммы ========
def create_graphviz(graph, output_file, reverse=False):
    dot = graphviz.Digraph(comment="Граф зависимостей", format="png")
    for node, deps in graph.items():
        for dep in deps:
            if reverse:
                dot.edge(dep, node)
            else:
                dot.edge(node, dep)
    dot.render(output_file, view=True)
    print(f"\n📊 Файл визуализации сохранён как {output_file}.png")

# ======== ASCII дерево ========
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

# ======== Главная функция ========
def main():
    print("✅ main() запущена")
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

    # Проверяем направление
    if args.reverse:
        print("\n🔁 Режим: обратные зависимости")
        graph = reverse_graph(graph)
    else:
        print("\n➡️ Режим: прямые зависимости")

    # BFS обход
    deps = bfs_dependencies(graph, args.start.upper())
    print(f"\nПорядок обхода зависимостей для {args.start.upper()}:")
    print(" → ".join(deps))

    # Вывод в ASCII-дерево
    if args.ascii:
        print("\n🌲 Зависимости в виде ASCII-дерева:")
        print_ascii_tree(graph, args.start.upper())

    # Генерация изображения Graphviz
    create_graphviz(graph, "dependency_graph", reverse=args.reverse)

    # Сохраняем результат в текст
    with open("bash_deps.txt", "w", encoding="utf-8") as f:
        f.write(f"Результат для {args.start.upper()} ({'обратный' if args.reverse else 'прямой'}):\n")
        f.write(" → ".join(deps))
    print("\n✅ Результат сохранён в bash_deps.txt")

# ======== Точка входа ========
if __name__ == "__main__":
    main()
    print("__name__ =", __name__)


