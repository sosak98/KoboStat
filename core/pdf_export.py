"""Export PDF du rapport, via rendu HTML + WeasyPrint."""
import base64
import io
from weasyprint import HTML

CSS = """
<style>
  body { font-family: 'Helvetica', Arial, sans-serif; color: #1f2937; margin: 2.5cm 2cm; }
  h1 { color: #1e3a8a; border-bottom: 2px solid #2563EB; padding-bottom: 6px; }
  h2 { color: #1e40af; margin-top: 28px; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0 18px 0; font-size: 12px; }
  th, td { border: 1px solid #cbd5e1; padding: 5px 8px; text-align: left; }
  th { background-color: #eff6ff; font-weight: 600; }
  img { max-width: 100%; margin: 10px 0; }
  .caption { font-size: 11px; font-style: italic; color: #555; text-align: center; margin-top: -6px; }
  p { line-height: 1.5; font-size: 13px; }
  .cover { text-align: center; margin-bottom: 40px; }
</style>
"""


def _df_to_html(df):
    return df.to_html(index=False, border=0, classes="tbl")


def build_pdf(report_items, title="Résultats et analyses", author=""):
    html_parts = [f"<html><head>{CSS}</head><body>"]
    html_parts.append(f"<div class='cover'><h1>{title}</h1>")
    if author:
        html_parts.append(f"<p>Préparé par : {author}</p>")
    html_parts.append("</div>")

    for item in report_items:
        t = item["type"]
        if t == "heading":
            html_parts.append(f"<h2>{item['content']}</h2>")
        elif t == "text":
            html_parts.append(f"<p>{item['content']}</p>")
        elif t == "table":
            if item.get("caption"):
                html_parts.append(f"<p class='caption'>{item['caption']}</p>")
            html_parts.append(_df_to_html(item["content"]))
        elif t == "image":
            b64 = base64.b64encode(item["content"]).decode("ascii")
            html_parts.append(f"<img src='data:image/png;base64,{b64}' />")
            if item.get("caption"):
                html_parts.append(f"<p class='caption'>{item['caption']}</p>")

    html_parts.append("</body></html>")
    full_html = "\n".join(html_parts)

    buf = io.BytesIO()
    HTML(string=full_html).write_pdf(buf)
    buf.seek(0)
    return buf
