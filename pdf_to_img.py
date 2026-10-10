import argparse
import getpass
import sys
from pathlib import Path

import pymupdf

NATIVE_FORMATS = {"png", "jpg", "jpeg", "pnm", "pam", "psd", "ps"}
PILLOW_FORMATS = {"webp", "tiff", "tif", "bmp"}  # require: pip install pillow
SUPPORTED_FORMATS = NATIVE_FORMATS | PILLOW_FORMATS
LOSSY_FORMATS = {"jpg", "jpeg", "webp"}


def pdf_to_images(pdf_path, output_folder, dpi=200, image_format="png",
                  first_page=1, last_page=None, password=None,
                  quality=95, get_password=None, verbose=True):
    """Render PDF pages to images and return the list of saved paths.

    Pages are 1-indexed and the range is inclusive. Filenames are zero-padded
    (page_001.png) so they sort correctly. `quality` (1-100) applies to JPEG
    and WebP. If the PDF is encrypted and no `password` is given,
    `get_password(pdf_path)` is called to obtain one, when provided.
    """
    pdf_path = Path(pdf_path)
    output_folder = Path(output_folder)
    image_format = image_format.lower().lstrip(".")

    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if image_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format '{image_format}'. Choose from: {sorted(SUPPORTED_FORMATS)}")
    if dpi <= 0:
        raise ValueError("dpi must be positive")
    if not 1 <= quality <= 100:
        raise ValueError("quality must be between 1 and 100")
    if image_format in PILLOW_FORMATS:
        try:
            import PIL  # noqa: F401  (pymupdf uses it for pil_save)
        except ImportError:
            raise ValueError(f"Format '{image_format}' requires Pillow: pip install pillow") from None

    zoom = dpi / 72
    matrix = pymupdf.Matrix(zoom, zoom)
    saved = []

    with pymupdf.open(pdf_path) as doc:
        if doc.needs_pass:
            if password is None and get_password is not None:
                password = get_password(pdf_path)
            if not doc.authenticate(password or ""):
                raise PermissionError(f"{pdf_path.name} is encrypted; wrong or missing password")

        total = len(doc)
        if last_page is None:
            last_page = total
        last_page = min(last_page, total)
        if first_page < 1 or last_page < 1 or first_page > last_page:
            raise ValueError(f"Invalid page range {first_page}-{last_page} (document has {total} pages)")

        output_folder.mkdir(parents=True, exist_ok=True)
        width = len(str(total))
        count = last_page - first_page + 1
        for page_number in range(first_page - 1, last_page):
            # JPEG has no alpha channel; drop it for every format to keep files small.
            pixmap = doc.load_page(page_number).get_pixmap(matrix=matrix, alpha=False)
            output_path = output_folder / f"page_{page_number + 1:0{width}d}.{image_format}"
            if image_format in PILLOW_FORMATS:
                options = {"quality": quality} if image_format in LOSSY_FORMATS else {}
                pixmap.pil_save(output_path, **options)
            else:
                pixmap.save(output_path, jpg_quality=quality)
            saved.append(output_path)
            if verbose:
                print(f"[{len(saved)}/{count}] {output_path}")

    return saved


def collect_pdfs(inputs):
    """Expand files and folders into a sorted, de-duplicated list of PDF paths."""
    pdfs = []
    for item in map(Path, inputs):
        if item.is_dir():
            pdfs.extend(sorted(p for p in item.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"))
        else:
            pdfs.append(item)
    return list(dict.fromkeys(pdfs))


def stdin_is_console():
    if not sys.stdin.isatty():
        return False
    if sys.platform == "win32":
        # NUL also reports isatty() on Windows; only a real console has a console mode.
        import ctypes
        import msvcrt
        mode = ctypes.c_uint32()
        handle = msvcrt.get_osfhandle(sys.stdin.fileno())
        return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)))
    return True


def prompt_password(pdf_path):
    if not stdin_is_console():
        return None
    return getpass.getpass(f"Password for {pdf_path.name}: ")


def main():
    parser = argparse.ArgumentParser(description="Convert PDF pages to images.")
    parser.add_argument("inputs", nargs="*", default=["input.pdf"],
                        help="PDF files and/or folders containing PDFs (default: input.pdf)")
    parser.add_argument("-o", "--output", default="output_images", help="output folder (default: output_images)")
    parser.add_argument("-d", "--dpi", type=int, default=200, help="resolution (default: 200)")
    parser.add_argument("-f", "--format", default="png",
                        help=f"one of {', '.join(sorted(SUPPORTED_FORMATS))} (default: png)")
    parser.add_argument("-q", "--quality", type=int, default=95, help="JPEG/WebP quality 1-100 (default: 95)")
    parser.add_argument("--first", type=int, default=1, help="first page, 1-indexed (default: 1)")
    parser.add_argument("--last", type=int, default=None, help="last page, inclusive (default: end)")
    parser.add_argument("-p", "--password", default=None,
                        help="password for encrypted PDFs (omit to be prompted securely)")
    args = parser.parse_args()

    pdfs = collect_pdfs(args.inputs)
    if not pdfs:
        sys.exit("Error: no PDF files found")

    # A single PDF writes straight into the output folder; several get a subfolder each.
    batch = len(pdfs) > 1
    total_images = 0
    failures = []
    for pdf in pdfs:
        output = Path(args.output) / pdf.stem if batch else Path(args.output)
        if batch:
            print(f"== {pdf} -> {output}")
        try:
            files = pdf_to_images(pdf, output, args.dpi, args.format, args.first, args.last,
                                  args.password, args.quality, get_password=prompt_password)
            total_images += len(files)
        except (FileNotFoundError, ValueError, PermissionError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            failures.append(pdf)

    print(f"Saved {total_images} images from {len(pdfs) - len(failures)} of {len(pdfs)} PDF(s) to {args.output}")
    if failures:
        sys.exit(f"Failed: {', '.join(str(p) for p in failures)}")


if __name__ == "__main__":
    main()
