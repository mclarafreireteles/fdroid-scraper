import os
import re
import csv
import json
import argparse
import subprocess
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Instale pyyaml: pip install pyyaml")
    raise

REPO_URL    = "https://github.com/f-droid/fdroiddata.git"
REPO_DIR    = Path("./fdroiddata")
METADATA_DIR = REPO_DIR / "metadata"
OUTPUT_CSV  = "fdroid_react_native.csv"
OUTPUT_JSON = "fdroid_react_native.json"

RN_PATTERNS = [
    r"react[-_]native",
    r"react-native-cli",
    r"@react-native",
    r"com\.facebook\.react",
    r"node_modules/react-native",
]

def clone_or_update_repo(repo_dir: Path, force_clone: bool = False):
    """Clona o repositório fdroiddata ou atualiza se já existir."""
    if repo_dir.exists() and not force_clone:
        print(f"[INFO] Repositório já existe em '{repo_dir}'. Atualizando...")
        subprocess.run(
            ["git", "-C", str(repo_dir), "pull", "--ff-only"],
            check=True
        )
    else:
        print(f"[INFO] Clonando repositório (shallow clone)...")
        subprocess.run([
            "git", "clone",
            "--depth=1",          
            "--filter=blob:none", 
            "--sparse",          
            REPO_URL,
            str(repo_dir)
        ], check=True)

        subprocess.run(
            ["git", "-C", str(repo_dir), "sparse-checkout", "set", "metadata"],
            check=True
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "read-tree", "-mu", "HEAD"],
            check=True
        )
    print("[OK] Repositório pronto.\n")


def is_react_native(content: str) -> bool:
    """Verifica se o conteúdo do arquivo .yml referencia React Native."""
    content_lower = content.lower()
    for pattern in RN_PATTERNS:
        if re.search(pattern, content_lower):
            return True
    return False


def extract_metadata(yml_path: Path) -> dict:
    """
    Lê um arquivo .yml do fdroiddata e extrai os campos relevantes.
    Retorna um dicionário com os metadados do app.
    """
    app_id = yml_path.stem  

    try:
        content = yml_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"app_id": app_id, "erro": str(e)}

    if not is_react_native(content):
        return None

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        data = {}

    if not isinstance(data, dict):
        data = {}

    builds = data.get("Builds", []) or []
    versoes = []
    for b in builds:
        if isinstance(b, dict):
            v = b.get("versionName") or b.get("VersionName")
            c = b.get("versionCode") or b.get("VersionCode")
            if v:
                versoes.append(f"{v} (code: {c})" if c else str(v))

    linhas_rn = []
    for i, linha in enumerate(content.splitlines()):
        if re.search(r"react[-_]native", linha, re.IGNORECASE):
            linhas_rn.append(f"L{i+1}: {linha.strip()}")

    return {
        "app_id":       app_id,
        "nome":         data.get("AutoName", ""),
        "licenca":      data.get("License", ""),
        "categorias":   ", ".join(data.get("Categories", []) or []),
        "website":      data.get("WebSite", ""),
        "source_code":  data.get("SourceCode", ""),
        "issue_tracker":data.get("IssueTracker", ""),
        "changelog":    data.get("Changelog", ""),
        "versao_atual": versoes[-1] if versoes else "",
        "total_versoes":len(versoes),
        "todas_versoes":"; ".join(versoes),
        "trecho_rn":    " | ".join(linhas_rn[:3]), 
    }


def salvar_csv(apps: list[dict], caminho: str):
    """Salva a lista de apps em CSV."""
    if not apps:
        print("[AVISO] Nenhum app encontrado para salvar.")
        return

    campos = list(apps[0].keys())
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(apps)
    print(f"[OK] CSV salvo em: {caminho}")


def salvar_json(apps: list[dict], caminho: str):
    """Salva a lista de apps em JSON."""
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(apps, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON salvo em: {caminho}")


def imprimir_resumo(apps: list[dict]):
    """Imprime um resumo no terminal."""
    print("\n" + "=" * 60)
    print(f"  Total de apps React Native encontrados: {len(apps)}")
    print("=" * 60)

    from collections import Counter
    todas_cats = []
    for app in apps:
        cats = [c.strip() for c in app["categorias"].split(",") if c.strip()]
        todas_cats.extend(cats)

    print("\nDistribuição por categoria:")
    for cat, n in Counter(todas_cats).most_common(10):
        print(f"  {cat:<25} {n} apps")

    print("\nApps encontrados:")
    for app in apps:
        nome = app["nome"] or app["app_id"]
        print(f"  • {nome:<35} [{app['licenca']}] {app['categorias']}")

def main():
    parser = argparse.ArgumentParser(
        description="Levanta apps React Native no F-Droid via repositório fdroiddata"
    )
    parser.add_argument(
        "--no-clone",
        action="store_true",
        help="Não clona/atualiza o repositório (usa o que já existe localmente)"
    )
    parser.add_argument(
        "--force-clone",
        action="store_true",
        help="Força novo clone mesmo se o repositório já existir"
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_CSV,
        help=f"Nome do arquivo CSV de saída (padrão: {OUTPUT_CSV})"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Também salva saída em JSON"
    )
    args = parser.parse_args()

    if not args.no_clone:
        clone_or_update_repo(REPO_DIR, force_clone=args.force_clone)
    else:
        print("[INFO] Pulando clone, usando repositório local.\n")

    ymls = sorted(METADATA_DIR.glob("*.yml"))
    total = len(ymls)
    print(f"[INFO] Analisando {total} arquivos de metadados...")

    apps_rn = []
    for i, yml_path in enumerate(ymls, 1):
        if i % 500 == 0:
            print(f"  ... {i}/{total} arquivos processados")
        resultado = extract_metadata(yml_path)
        if resultado:
            apps_rn.append(resultado)

    print(f"\n[OK] Varredura concluída. {len(apps_rn)} apps React Native encontrados.\n")

    salvar_csv(apps_rn, args.output)
    if args.json:
        salvar_json(apps_rn, OUTPUT_JSON)

    imprimir_resumo(apps_rn)


if __name__ == "__main__":
    main()