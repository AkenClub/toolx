"""Convert the source ToolX PNG into a Windows multi-size ICO."""

from pathlib import Path

from PIL import Image


ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def main():
    project_root = Path(__file__).resolve().parents[1]
    source_path = project_root / "assets" / "app_icon.png"
    output_path = project_root / "assets" / "app_icon.ico"
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    image = Image.open(source_path).convert("RGBA")
    image.save(output_path, format="ICO", sizes=[(size, size) for size in ICON_SIZES])
    print(output_path)


if __name__ == "__main__":
    main()
