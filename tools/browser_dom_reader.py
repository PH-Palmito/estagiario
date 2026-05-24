from __future__ import annotations

import json
import re

from tools.browser_screen_analysis import normalize_text_for_match

PRODUCT_CARDS_MARKER = "__ESTAGIARIO_PRODUCTS__\n"


def build_product_cards_script(limit: int = 10, marker: str = PRODUCT_CARDS_MARKER) -> str:
    return f"""void ((()=>{{
const marker={json.dumps(marker)};
const limit={int(limit)};
const viewportOffsetX=Math.max(0, Math.round((window.outerWidth - window.innerWidth)/2));
const viewportOffsetY=Math.max(0, Math.round(window.outerHeight - window.innerHeight));
const norm=s=>(s||"").normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase().replace(/[^\\p{{L}}\\p{{N}}\\s]/gu," ").replace(/\\s+/g," ").trim();
const clean=s=>(s||"").replace(/\\s+/g," ").trim();
const visible=el=>{{
  const r=el.getBoundingClientRect();
  const st=getComputedStyle(el);
  return r.width>35&&r.height>20&&r.bottom>90&&r.top<innerHeight&&st.visibility!=="hidden"&&st.display!=="none";
}};
const productRe=/\\b(celular|smartphone|notebook|iphone|galaxy|xiaomi|redmi|samsung|motorola|realme|lenovo|acer|dell|tablet)\\b/i;
const noiseRe=/\\b(memoria ram|cupom|frete|departamento|categoria|sacola|carrinho|entrar|login|favorito|ordenar|filtrar|avaliacao|avaliacoes|sem juros|cashback)\\b/i;
const slugText=href=>{{
  try {{
    const url=new URL(href, location.href);
    const part=decodeURIComponent(url.pathname.split("/").filter(Boolean)[0]||"");
    return clean(part.replace(/-/g," "));
  }} catch(e) {{
    return "";
  }}
}};
const bestCardText=a=>{{
  const chunks=[];
  chunks.push(a.innerText, a.getAttribute("aria-label"), a.title);
  const img=a.querySelector("img");
  if(img) chunks.push(img.alt);

  let node=a;
  for(let depth=0; node&&depth<5; depth++, node=node.parentElement) {{
    if(!visible(node)) continue;
    const text=clean(node.innerText||node.textContent||"");
    if(text.length>=8&&text.length<=700) chunks.push(text);
  }}

  let best="";
  for(const raw of chunks) {{
    const text=clean(raw);
    const n=norm(text);
    if(!text||noiseRe.test(n)) continue;
    if(productRe.test(n)||/r\\$\\s*\\d/i.test(text)) {{
      if(text.length>best.length) best=text;
    }}
  }}

  if(best) return best;
  return slugText(a.href);
}};
const anchors=[...document.querySelectorAll("a[href]")];
const rows=[];
const seen=new Set();
for(const a of anchors) {{
  if(!visible(a)) continue;
  const href=a.href||"";
  const raw=bestCardText(a);
  let text=clean(raw);
  if(!text) continue;
  if(text.length>170) text=text.slice(0,167).trim()+"...";
  const n=norm(text);
  const hrefNorm=norm(slugText(href));
  const looksProduct=productRe.test(n)||productRe.test(hrefNorm)||/\\/p\\//.test(href);
  if(!looksProduct||noiseRe.test(n)) continue;
  if(n.length<8||seen.has(href)||seen.has(n)) continue;
  seen.add(href);
  seen.add(n);
  const r=a.getBoundingClientRect();
  rows.push({{
    top:r.top,
    left:r.left,
    x:Math.round(window.screenX + viewportOffsetX + r.left + Math.min(Math.max(r.width/2, 20), 220)),
    y:Math.round(window.screenY + viewportOffsetY + r.top + Math.min(Math.max(r.height/2, 16), 90)),
    text,
    type:"Hyperlink"
  }});
}}
rows.sort((a,b)=>a.top-b.top||a.left-b.left);
const output=marker+JSON.stringify(rows.slice(0,limit));
const fallback=()=>{{
  const ta=document.createElement("textarea");
  ta.value=output;
  ta.style.position="fixed";
  ta.style.left="-9999px";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {{ document.execCommand("copy"); }} catch(e) {{}}
  ta.remove();
}};
if(navigator.clipboard&&navigator.clipboard.writeText) {{
  navigator.clipboard.writeText(output).catch(fallback);
}} else {{
  fallback();
}}
}})())"""


def parse_product_cards_payload(payload: str, limit: int = 10) -> list[dict]:
    try:
        rows = json.loads(payload or "")
    except json.JSONDecodeError:
        return []

    items = []
    seen = set()

    for row in rows:
        if not isinstance(row, dict):
            continue

        line = re.sub(r"\s+", " ", str(row.get("text", ""))).strip()
        normalized = normalize_text_for_match(line)

        if len(line) < 8 or not normalized or normalized in seen:
            continue

        try:
            items.append(
                {
                    "text": line,
                    "x": int(row.get("x")),
                    "y": int(row.get("y")),
                    "type": str(row.get("type", "Hyperlink")).strip() or "Hyperlink",
                    "source": "dom_product",
                }
            )
        except (TypeError, ValueError):
            continue

        seen.add(normalized)

        if len(items) >= limit:
            break

    return items
