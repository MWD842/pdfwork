# pdf_to_img

A small command-line tool that converts PDF pages to images using [PyMuPDF](https://pymupdf.readthedocs.io/). It can convert one PDF, several PDFs, or every PDF in a folder.

## Installation

Requires Python 3.8+ and PyMuPDF 1.24 or newer.

```bash
pip install pymupdf
```

For WebP, TIFF or BMP output, also install Pillow:

```bash
pip install pillow
```

## Usage

```bash
python pdf_to_img.py [inputs ...] [options]
```

With no arguments it converts `input.pdf` to PNGs in `output_images/`.

| Option | Description | Default |
| --- | --- | --- |
| `inputs` | One or more PDF files and/or folders containing PDFs | `input.pdf` |
| `-o`, `--output` | Output folder (created if missing) | `output_images` |
| `-d`, `--dpi` | Render resolution | `200` |
| `-f`, `--format` | `png`, `jpg`, `jpeg`, `pnm`, `pam`, `psd`, `ps`; with Pillow also `webp`, `tiff`, `tif`, `bmp` | `png` |
| `-q`, `--quality` | Quality 1–100 for JPEG and WebP (lower means smaller files) | `95` |
| `--first` | First page to convert (1-indexed) | `1` |
| `--last` | Last page to convert (inclusive) | last page |
| `-p`, `--password` | Password for encrypted PDFs | prompt |

### Examples

Convert a whole document at the default settings:

```bash
python pdf_to_img.py report.pdf
```

Convert pages 2–10 as 150 DPI JPEGs at quality 80:

```bash
python pdf_to_img.py report.pdf -o pages -d 150 -f jpg -q 80 --first 2 --last 10
```

Convert every PDF in a folder to WebP (requires Pillow):

```bash
python pdf_to_img.py scans/ -f webp -o images
```

Convert several specific files:

```bash
python pdf_to_img.py a.pdf b.pdf c.pdf
```

## Output

- **One PDF:** images go straight into the output folder.
- **Several PDFs:** each PDF gets its own subfolder named after the file (`output_images/report/`, `output_images/invoice/`, and so on), so pages never overwrite each other.

Files are named `page_<n>.<format>`, zero-padded to the width of the page count so they sort correctly (e.g. `page_001.png` … `page_120.png`).

Folder inputs are not searched recursively. `--first`, `--last` and `--password` apply to every PDF in a batch.

## Encrypted PDFs

If a PDF is encrypted and you didn't pass `-p`, the script asks for the password without echoing it. That keeps the password out of your shell history, which is safer than `-p`. When input is not an interactive terminal (scripts, pipes, scheduled tasks), it doesn't prompt: the file is reported as failed instead.

## Errors and exit code

In a batch, a PDF that fails (missing, corrupt, wrong password, invalid page range) is reported and skipped, and the remaining files are still converted. The script ends with a summary, lists the failed files, and exits with code `1` if any file failed, otherwise `0`.

## Use as a library

```python
from pdf_to_img import pdf_to_images

files = pdf_to_images("input.pdf", "output_images", dpi=200, image_format="jpg", quality=85)
print(f"Saved {len(files)} images")
```

`pdf_to_images` returns a list of `pathlib.Path` objects. Optional arguments:

- `first_page` and `last_page`: the pages to convert.
- `password`: the password for an encrypted PDF.
- `get_password`: a function called with the PDF path to supply a password when needed.
- `verbose=False`: turns off progress output.

It raises:

- `FileNotFoundError` if the PDF doesn't exist.
- `ValueError` for a bad format, DPI, quality or page range, or when Pillow is missing.
- `PermissionError` for a wrong or missing password.
- PyMuPDF's `FileDataError`, a subclass of `RuntimeError`, for a corrupt file.
