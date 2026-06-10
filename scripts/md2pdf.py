#!/usr/bin/env python3
"""
md2pdf.py — 小龙虾 PDF 生成工具
遵循小马样式规格：#C00000 深红色系 + markdown-it-py + wkhtmltopdf
"""
import sys
import os
import subprocess
import argparse
import re
from pathlib import Path

# Try markdown-it-py first, fallback to markdown
try:
    from markdown_it import MarkdownIt
    MARKDOWN_IT = True
except ImportError:
    MARKDOWN_IT = False

try:
    import markdown
    MARKDOWN_PY = True
except ImportError:
    MARKDOWN_PY = False


CSS_TEMPLATE = """@page {{
    size: A4;
    margin: 15mm 15mm 15mm 15mm;
    @bottom-center {{
        content: counter(page);
        font-size: 10px;
        color: #888;
    }}
}}

* {{
    box-sizing: border-box;
}}

body {{
    font-family: "Noto Sans CJK SC", "Noto Sans CJK", "DejaVu Sans", sans-serif;
    font-size: 11pt;
    line-height: 1.7;
    color: #222;
}}

/* ===== 标题体系 ===== */
h1 {{
    font-size: 22pt;
    font-weight: bold;
    color: #C00000;
    border-bottom: 2px solid #C00000;
    padding-bottom: 6px;
    margin: 0 0 20px 0;
    page-break-after: avoid;
}}

h2 {{
    font-size: 16pt;
    font-weight: bold;
    color: #333;
    border-left: 4px solid #C00000;
    padding: 4px 0 4px 10px;
    margin: 28px 0 14px 0;
    page-break-after: avoid;
}}

h3 {{
    font-size: 13pt;
    font-weight: bold;
    color: #555;
    margin: 20px 0 8px 0;
    page-break-after: avoid;
}}

h4 {{
    font-size: 11pt;
    font-weight: bold;
    color: #666;
    margin: 14px 0 6px 0;
}}

/* ===== 强调 ===== */
strong, b {{
    color: #C00000;
    font-weight: bold;
}}

em, i {{
    font-style: italic;
    color: #444;
}}

/* ===== 代码 ===== */
code {{
    font-family: "DejaVu Sans Mono", "Menlo", "Monaco", monospace;
    font-size: 9pt;
    color: #C00000;
    background: #f4f4f4;
    padding: 1px 5px;
    border-radius: 3px;
    border: 1px solid #e0e0e0;
}}

pre {{
    font-family: "DejaVu Sans Mono", "Menlo", "Monaco", monospace;
    font-size: 9pt;
    background: #f8f8f8;
    border-left: 4px solid #C00000;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 12px 14px;
    margin: 12px 0;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
}}

pre code {{
    background: none;
    border: none;
    padding: 0;
    color: #222;
    font-size: inherit;
}}

/* ===== 列表 ===== */
ul, ol {{
    margin: 8px 0 12px 0;
    padding-left: 24px;
}}

li {{
    margin: 4px 0;
}}

li > ul, li > ol {{
    margin: 2px 0 2px 0;
}}

/* ===== 表格 ===== */
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 14px 0;
    font-size: 10.5pt;
    page-break-inside: avoid;
}}

thead tr {{
    background: #C00000;
    color: #fff;
}}

th {{
    padding: 8px 10px;
    text-align: left;
    font-weight: bold;
    border: 1px solid #a00000;
}}

td {{
    padding: 7px 10px;
    border: 1px solid #ddd;
    vertical-align: top;
}}

tbody tr:nth-child(even) td {{
    background: #f9f9f9;
}}

tbody tr:hover td {{
    background: #fff5f5;
}}

/* ===== 引用块 ===== */
blockquote {{
    border-left: 4px solid #888;
    background: #fafafa;
    color: #555;
    margin: 14px 0;
    padding: 10px 16px;
    font-style: italic;
}}

blockquote strong {{
    color: #C00000;
}}

/* ===== 分割线 ===== */
hr {{
    border: none;
    border-top: 1px solid #e0e0e0;
    margin: 24px 0;
}}

/* ===== 链接 ===== */
a {{
    color: #C00000;
    text-decoration: none;
}}

a:hover {{
    text-decoration: underline;
}}

/* ===== Emoji ===== */
.emoji {
    font-family: "Noto Color Emoji", "Emoji One", "Apple Color Emoji", sans-serif;
    font-size: 1em;
}

/* ===== 页眉 ===== */
.report-header {{
    text-align: center;
    margin-bottom: 28px;
    padding-bottom: 18px;
    border-bottom: 2px solid #1a1a1a;
}}

.report-header h1 {{
    border-bottom: none;
    margin-bottom: 8px;
}}

.report-header .meta {{
    font-size: 10pt;
    color: #666;
}}

.report-footer {{
    margin-top: 32px;
    padding-top: 12px;
    border-top: 1px solid #ddd;
    font-size: 9pt;
    color: #888;
    text-align: center;
}}

/* ===== 检查符号 ===== */
.success {{
    color: #1a7f37;
    font-weight: bold;
}}

.pending {{
    color: #9a6700;
}}

/* ===== 代码高亮（highlight.js风格） ===== */
.hljs {{
    background: #f8f8f8;
    border-left: 4px solid #C00000;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 12px 14px;
}}

/* ===== 页面断行控制 ===== */
h1, h2, h3, h4 {{
    page-break-after: avoid;
}}

p {{
    orphans: 3;
    widows: 3;
}}
"""


def convert_md_to_html(md_text: str) -> str:
    """Convert markdown to HTML using markdown-it-py or markdown."""
    
    if MARKDOWN_IT:
        md = MarkdownIt("gfm-like", {"typographer": True, "linkify": False})
        html_body = md.render(md_text)
    else:
        html_body = markdown.markdown(
            md_text,
            extensions=["tables", "fenced_code", "codehilite", "toc"]
        )
    
    return html_body


def build_full_html(html_body: str, title: str = "") -> str:
    """Wrap HTML body in full document with stylesheet."""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{CSS_TEMPLATE}
</style>
</head>
<body>
{html_body}
</body>
</html>"""


def html_to_pdf(html_path: str, pdf_path: str) -> bool:
    """Convert HTML to PDF using WeasyPrint (CJK-capable, no wkhtmltopdf needed)."""
    try:
        from weasyprint import HTML as WeasyHTML
        import logging
        logging.getLogger('weasyprint').setLevel(logging.WARNING)
        WeasyHTML(filename=html_path).write_pdf(pdf_path)
        return True
    except Exception as e:
        print(f"ERROR: WeasyPrint failed: {e}")
        return False


def convert(input_path: str, output_path: str = None) -> bool:
    """
    Main conversion: MD → HTML → PDF.
    Returns True on success.
    """
    input_p = Path(input_path)
    if not input_p.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return False

    # Read markdown
    md_text = input_p.read_text(encoding="utf-8")

    # Convert to HTML
    html_body = convert_md_to_html(md_text)

    # Extract title from first h1, or use filename
    title_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html_body)
    title = title_match.group(1) if title_match else input_p.stem

    # Build full HTML document
    full_html = build_full_html(html_body, title=title)

    # Write temp HTML
    html_path = output_path.replace(".pdf", ".html") if output_path else input_p.with_suffix(".html").name
    Path(html_path).write_text(full_html, encoding="utf-8")
    print(f"  HTML → {html_path}")

    # Convert to PDF
    pdf_path = output_path or input_p.with_suffix(".pdf").name
    print(f"  PDF  → {pdf_path}")

    if not html_to_pdf(html_path, pdf_path):
        return False

    # Cleanup temp HTML
    try:
        Path(html_path).unlink()
    except Exception:
        pass

    pdf_size = Path(pdf_path).stat().st_size
    print(f"  Done! ({pdf_size / 1024:.1f} KB)")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="md2pdf.py — Markdown 转 PDF（小马样式规格）"
    )
    parser.add_argument("input", help="输入 Markdown 文件")
    parser.add_argument("-o", "--output", help="输出 PDF 文件路径（默认同目录）")
    parser.add_argument("-t", "--title", help="文档标题")

    args = parser.parse_args()

    output = args.output
    if not output and not args.input.endswith(".pdf"):
        output = args.input.replace(".md", ".pdf")

    success = convert(args.input, output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
