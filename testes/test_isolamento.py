"""O gabarito não chega ao agente, e a chave não aparece em código nem em resultados."""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LADO_DO_AGENTE = ["agente", "ferramentas", "seguranca", "memoria", "simulador", "config.py"]


def _arquivos(alvos):
    for alvo in alvos:
        caminho = RAIZ / alvo
        yield from ([caminho] if caminho.is_file() else caminho.rglob("*.py"))


def test_gabarito_nao_e_lido_pelo_agente():
    for arquivo in _arquivos(LADO_DO_AGENTE):
        assert "gabarito" not in arquivo.read_text(encoding="utf-8").lower(), arquivo
    assert not (RAIZ / "dados" / "gabarito.json").exists()


def test_tela_nao_le_o_gabarito():
    codigo = (RAIZ / "app.py").read_text(encoding="utf-8")
    assert "gabarito.json" not in codigo and "comparar_gabarito" not in codigo and "externo" not in codigo


def test_nenhuma_chave_versionada():
    padrao = re.compile(r"sk-[A-Za-z0-9_-]{20,}")
    for arquivo in RAIZ.rglob("*"):
        # Dependências da .venv são locais e não fazem parte do código versionável.
        if arquivo.is_relative_to(RAIZ / ".venv"):
            continue
        if arquivo.is_file() and arquivo.suffix in {".py", ".md", ".json", ".txt", ".example", ".csv", ".toml"}:
            assert not padrao.search(arquivo.read_text(encoding="utf-8", errors="ignore")), arquivo


def test_env_fora_do_versionamento():
    assert ".env" in (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
