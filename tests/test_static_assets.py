from pathlib import Path

from app.utils.static_assets import compute_static_version


def test_compute_static_version_changes_when_css_changes(tmp_path):
    static_root = tmp_path / "static"
    css_dir = static_root / "css"
    css_dir.mkdir(parents=True)
    css = css_dir / "style.css"
    css.write_text("a {}", encoding="utf-8")

    first = compute_static_version(str(static_root))
    css.write_text("a { color: red; }", encoding="utf-8")
    second = compute_static_version(str(static_root))

    assert first
    assert second
    assert first != second


def test_compute_static_version_respects_env(monkeypatch, tmp_path):
    static_root = tmp_path / "static"
    (static_root / "css").mkdir(parents=True)
    (static_root / "css" / "style.css").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("STATIC_VERSION", "deploy-42")

    assert compute_static_version(str(static_root)) == "deploy-42"


def test_compute_static_version_changes_when_demo_image_changes(tmp_path):
    static_root = tmp_path / "static"
    demo_dir = static_root / "demo"
    demo_dir.mkdir(parents=True)
    image = demo_dir / "avto.jpg"
    image.write_bytes(b"first-image")

    first = compute_static_version(str(static_root))
    image.write_bytes(b"second-image-with-new-content")
    second = compute_static_version(str(static_root))

    assert first != second
