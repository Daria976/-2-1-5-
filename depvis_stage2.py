#!/usr/bin/env python3
"""
depvis_stage2.py
Этап 2: Сбор данных о зависимостях пакетов Alpine (apk).
"""
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
    """
    Скачивает APKINDEX.tar.gz из указанного репозитория.
    Пример URL: https://dl-cdn.alpinelinux.org/alpine/v3.18/main/x86_64/
    """
    if not repo_url.endswith("/"):
        repo_url += "/"
    url = repo_url + "APKINDEX.tar.gz"
    print(f"→ Скачиваем индекс: {url}")
    with urllib.request.urlopen(url) as r:
        return r.read()

def parse_apkindex(data: bytes):
    """
    Распаковывает APKINDEX.tar.gz и извлекает записи пакетов.
    Возвращает словарь: {pkgname: {'version': ..., 'depends': [...]}}
    """
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
        print("❌ Укажите package и repository в config.xml")
        sys.exit(2)

    try:
        raw_data = download_apkindex(repo)
    except Exception as e:
        print(f"❌ Не удалось скачать APKINDEX: {e}")
        sys.exit(3)

    try:
        packages = parse_apkindex(raw_data)
    except Exception as e:
        print(f"❌ Ошибка при разборе APKINDEX: {e}")
        sys.exit(4)

    if package not in packages:
        print(f"⚠️ Пакет {package} не найден в репозитории")
        sys.exit(0)

    pkginfo = packages[package]
    deps = pkginfo["depends"]
    print(f"\nПакет: {package}")
    print(f"Версия: {pkginfo['version']}")
    print(f"Прямые зависимости ({len(deps)}):")
    for dep in deps:
        print(f"  - {dep}")

    # (опционально) сохранить вывод в файл
    with open(f"{package}_deps.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(deps))

    print(f"\nСписок зависимостей сохранён в {package}_deps.txt")

if __name__ == "__main__":
    main()
