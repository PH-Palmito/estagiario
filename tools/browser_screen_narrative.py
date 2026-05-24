from __future__ import annotations

import re
from urllib.parse import urlparse

from tools.browser_screen_analysis import (
    content_showcase,
    detect_screen_category,
    extract_finance_focus_lines,
    extract_finance_metrics,
    normalize_text_for_match,
    trim_detail_text,
)


def clean_browser_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", title or "").strip(" -|")
    cleaned = re.sub(
        r"\s*-\s*(google chrome|chrome|microsoft edge|edge|mozilla firefox|firefox|opera|brave)$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def parse_github_repo_from_url(page_url: str) -> str:
    parsed = urlparse(page_url or "")
    if "github.com" not in parsed.netloc.lower():
        return ""

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return ""


def parse_github_profile_from_url(page_url: str) -> str:
    parsed = urlparse(page_url or "")
    if "github.com" not in parsed.netloc.lower():
        return ""

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) == 1:
        return parts[0]
    return ""


def parse_title_content(clean_title: str, page_url: str) -> str:
    if not clean_title:
        return ""

    parsed = urlparse(page_url or "")
    host = parsed.netloc.lower()

    if "youtube.com" in host or "youtu.be" in host:
        return re.sub(r"\s*-\s*youtube$", "", clean_title, flags=re.IGNORECASE).strip()

    if "github.com" in host:
        match = re.match(r"GitHub\s*-\s*([^:]+):\s*(.+)$", clean_title, flags=re.IGNORECASE)
        if match:
            return match.group(2).strip()

    return clean_title


def strip_repo_prefix_from_title(title_content: str, repo_name: str) -> str:
    compact = re.sub(r"\s+", " ", title_content or "").strip()
    if not compact or not repo_name:
        return compact

    pattern = rf"^{re.escape(repo_name)}\s*[:\-|]\s*"
    stripped = re.sub(pattern, "", compact, flags=re.IGNORECASE).strip()
    return stripped or compact


def relevance_terms_from_context(page_url: str = "", page_title: str = "") -> set[str]:
    stopwords = {
        "para", "com", "sem", "por", "uma", "uns", "umas", "the", "and", "from",
        "that", "this", "como", "mais", "menos", "sobre", "resumo", "detalhe",
        "home", "inicio", "page", "pagina", "site", "oficial", "google", "chrome",
        "edge", "firefox", "youtube", "github", "investidor10",
    }
    tokens = set()

    clean_title = clean_browser_title(page_title)
    title_content = parse_title_content(clean_title, page_url)
    normalized_title = normalize_text_for_match(title_content)
    for token in normalized_title.split():
        if len(token) >= 4 and token not in stopwords and not token.isdigit():
            tokens.add(token)

    parsed = urlparse(page_url or "")
    host = parsed.netloc.lower()
    for piece in re.split(r"[\.\-_/]+", host):
        piece = piece.strip()
        if len(piece) >= 4 and piece not in {"www", "com", "br"} and piece not in stopwords:
            tokens.add(piece)

    return tokens


def extract_generic_focus_lines(lines, page_url: str = "", page_title: str = "", limit: int = 5) -> list[str]:
    prioritized = []
    relevance_terms = relevance_terms_from_context(page_url=page_url, page_title=page_title)
    generic_noise = (
        "cookie",
        "politica de privacidade",
        "termos de uso",
        "menu",
        "entrar",
        "login",
        "minha conta",
        "carrinho",
        "sacola",
        "buscar",
        "pesquisar",
        "departamentos",
        "atendimento",
        "pular navegacao",
        "ir para o conte",
        "repository navigation",
        "visao geral",
    )

    for index, line in enumerate(lines):
        compact = re.sub(r"\s+", " ", line).strip()
        normalized = normalize_text_for_match(compact)
        if not compact or len(compact) < 4:
            continue
        if normalized.isdigit():
            continue
        if re.match(r"^https?://", compact, flags=re.IGNORECASE):
            continue
        if any(token in normalized for token in generic_noise):
            continue
        if "http://" in compact.lower() or "https://" in compact.lower():
            continue
        if (
            "direitos reservados" in normalized
            or "copyright" in normalized
            or "leia mais no texto original" in normalized
            or ("lei" in normalized and "9 610 98" in normalized)
        ):
            continue

        score = 0
        words = normalized.split()
        if len(words) >= 3:
            score += 2
        if len(words) >= 6:
            score += 2
        if len(compact) >= 28:
            score += 1
        if re.search(r"[.!:%]", compact):
            score += 1
        if any(term in normalized for term in relevance_terms):
            score += 6
        if re.search(r"[a-zA-Z\u00C0-\u017F]{4,}.*[a-zA-Z\u00C0-\u017F]{4,}", compact):
            score += 1
        if "copyright" in normalized or "direitos reservados" in normalized:
            score -= 8
        if re.fullmatch(r"[\W\d_]+", compact):
            score -= 6
        if compact in {"0", "0,0", "0.0"}:
            score -= 6
        if len(words) <= 2 and not any(term in normalized for term in relevance_terms):
            score -= 4

        prioritized.append((score, index, compact))

    prioritized.sort(key=lambda item: (-item[0], item[1]))
    chosen = []
    for score, _index, compact in prioritized:
        if score < 1 and chosen:
            continue
        if compact not in chosen:
            chosen.append(compact)
        if len(chosen) >= limit:
            break

    if chosen:
        return chosen

    relaxed = []
    for line in lines:
        compact = re.sub(r"\s+", " ", line).strip()
        normalized = normalize_text_for_match(compact)
        if not compact or len(compact) < 8:
            continue
        if re.match(r"^https?://", compact, flags=re.IGNORECASE):
            continue
        if "http://" in compact.lower() or "https://" in compact.lower():
            continue
        if "direitos reservados" in normalized or "copyright" in normalized or "leia mais no texto original" in normalized:
            continue
        if compact not in relaxed:
            relaxed.append(compact)
        if len(relaxed) >= limit:
            break

    return relaxed or chosen


def is_generic_github_line(normalized: str) -> bool:
    if not normalized:
        return True

    exact_noise = {
        "repository navigation",
        "code",
        "issues",
        "pull requests",
        "actions",
        "discussions",
        "agents",
        "security",
        "insights",
        "projects",
        "wiki",
        "releases",
        "packages",
        "overview",
        "repositories",
        "stars",
        "followers",
        "following",
        "navegacao do usuario",
        "visao geral",
        "repositorios",
        "popular repositories",
        "pinned",
        "contributions",
        "contribuicoes",
    }
    if normalized in exact_noise:
        return True

    contains_noise = (
        "skip to content",
        "ir para o conte",
        "sign in",
        "sign up",
        "repository navigation",
        "navegacao do usuario",
        "jump to",
        "search code",
        "search issues",
        "github stars",
    )
    return any(token in normalized for token in contains_noise)


def extract_github_focus_lines(lines, page_url: str = "", limit: int = 5) -> list[str]:
    repo_name = parse_github_repo_from_url(page_url)
    profile_name = parse_github_profile_from_url(page_url)
    prioritized = []

    for index, line in enumerate(lines):
        compact = re.sub(r"\s+", " ", line).strip()
        normalized = normalize_text_for_match(compact)
        if not compact or len(compact) < 4:
            continue
        if is_generic_github_line(normalized):
            continue
        if "http://" in compact.lower() or "https://" in compact.lower():
            continue
        if normalized.startswith("git clone"):
            continue

        score = 0
        if len(compact) >= 24:
            score += 2
        if len(compact) >= 50:
            score += 2
        if any(token in normalized for token in (
            "readme", "sobre", "about", "descricao", "description", "getting started",
            "instal", "installation", "setup", "como usar", "usage", "feature",
            "features", "topic", "python", "ai", "vision", "automation", "agent",
            "screen", "project", "projeto", "requirements", "requisitos", "example",
            "exemplo", "quick start", "overview", "demo",
        )):
            score += 6
        if repo_name and any(piece in normalized for piece in normalize_text_for_match(repo_name).split("/")):
            score += 2
        if profile_name and normalize_text_for_match(profile_name) in normalized:
            score += 1
        if re.search(r"[a-zA-Z\u00C0-\u017F]{4,}.*[a-zA-Z\u00C0-\u017F]{4,}", compact):
            score += 1
        if re.search(r"[.!:]", compact):
            score += 1
        if re.search(r"^(readme|about|descricao|description|installation|setup|usage|features|overview)\b", normalized):
            score += 3
        if any(token in normalized for token in ("followers", "following", "stars", "repositories", "overview", "contributions")):
            score -= 3
        if len(compact) <= 18:
            score -= 2
        if re.fullmatch(r"[\W\d_]+", compact):
            score -= 4

        prioritized.append((score, index, compact))

    prioritized.sort(key=lambda item: (-item[0], item[1]))
    chosen = []
    for score, _index, compact in prioritized:
        if score < 1 and chosen:
            continue
        if compact not in chosen:
            chosen.append(compact)
        if len(chosen) >= limit:
            break

    return chosen


def items_are_navigation_heavy(lines, page_url: str = "", page_title: str = "") -> bool:
    if not lines:
        return True

    category = detect_screen_category(lines, page_url=page_url, page_title=page_title)
    if category in {"repositorio github", "video youtube", "financas"}:
        return True

    generic_hits = 0
    useful_hits = 0
    for line in lines:
        normalized = normalize_text_for_match(line)
        if not normalized:
            continue
        if is_generic_github_line(normalized):
            generic_hits += 1
        if len(normalized.split()) >= 4:
            useful_hits += 1
        if any(token in normalized for token in {"readme", "sobre", "descricao", "description", "instal", "usage", "projeto", "project"}):
            useful_hits += 2

    return generic_hits >= max(2, useful_hits)


def summarize_screen_lines(lines, page_url: str = "", page_title: str = "") -> str:
    if not lines:
        return "Nao consegui extrair um resumo confiavel da tela."

    normalized_lines = [normalize_text_for_match(line) for line in lines if line]
    category = detect_screen_category(lines, page_url=page_url, page_title=page_title)
    clean_title = clean_browser_title(page_title)
    title_content = parse_title_content(clean_title, page_url)

    if category == "repositorio github":
        repo_name = parse_github_repo_from_url(page_url)
        profile_name = parse_github_profile_from_url(page_url)
        title_content = strip_repo_prefix_from_title(title_content, repo_name)
        showcase = content_showcase(extract_github_focus_lines(lines, page_url=page_url, limit=4), limit=3)
        if repo_name and title_content and title_content.lower() != repo_name.lower():
            return f"E o repositorio {repo_name} no GitHub. Pelo titulo, o foco parece ser: {title_content}. No conteudo visivel, vejo: " + "; ".join(showcase) + "."
        if repo_name and showcase:
            return f"E o repositorio {repo_name} no GitHub. No conteudo visivel, vejo: " + "; ".join(showcase) + "."
        if repo_name:
            return f"E o repositorio {repo_name} no GitHub. Estou vendo a navegacao principal com Code, Issues, Pull requests, Discussions e Actions."
        if profile_name and title_content:
            return f"E o perfil {profile_name} no GitHub. Pelo titulo, o foco parece ser: {title_content}."
        if profile_name and showcase:
            return f"E o perfil {profile_name} no GitHub. No que ficou visivel, vejo: " + "; ".join(showcase) + "."
        return "Parece um repositorio no GitHub. Estou vendo a navegacao principal e parte do conteudo do projeto."

    if category == "video youtube":
        title = title_content or clean_title or "um video no YouTube"
        showcase = content_showcase([line for line in lines if normalize_text_for_match(line) not in {"up next", "youtube"}], limit=2)
        if showcase:
            return f"Parece a pagina de um video no YouTube: {title}. Na tela, vejo: " + "; ".join(showcase) + "."
        return f"Parece a pagina de um video no YouTube: {title}."

    if category == "noticia":
        showcase = content_showcase(extract_generic_focus_lines(lines, page_url=page_url, page_title=page_title, limit=6), limit=4)
        if title_content and showcase:
            return f"Parece uma noticia. O titulo sugere: {title_content}. Pontos principais visiveis: " + "; ".join(showcase) + "."
        if title_content:
            return f"Parece uma noticia. O titulo sugere: {title_content}."
        if showcase:
            return "Parece uma noticia. Pontos principais visiveis: " + "; ".join(showcase) + "."
        return "Parece uma noticia, mas ainda nao capturei o trecho principal com confianca."

    if category == "financas":
        showcase = content_showcase(extract_finance_focus_lines(lines, limit=5), limit=4)
        if title_content and showcase:
            return f"Parece uma pagina financeira. Pelo titulo, o foco parece ser: {title_content}. Pontos uteis visiveis: " + "; ".join(showcase) + "."
        if showcase:
            return "Parece uma pagina financeira. Pontos uteis visiveis: " + "; ".join(showcase) + "."
        if title_content:
            return f"Parece uma pagina financeira. Pelo titulo, o foco parece ser: {title_content}."
        return "Parece uma pagina financeira, mas ainda nao consegui capturar os valores e rotulos mais importantes."

    pure_price_lines = 0
    for line in lines:
        line_lower = line.lower()
        if re.search(r"r\$\s*\d|\d+,\d{2}", line_lower) and not re.search(r"[a-zA-Z\u00C0-\u017F]{4,}", line):
            pure_price_lines += 1
        if "sem juros" in line_lower or "vez" in line_lower:
            pure_price_lines += 1

    if pure_price_lines >= max(3, len(lines) // 2):
        return "Vejo principalmente precos e parcelas. A tela parece comercial, mas ainda nao peguei bem os nomes principais dos itens."

    showcase = content_showcase(extract_generic_focus_lines(lines, page_url=page_url, page_title=page_title, limit=5), limit=3)

    if category in {"smartphones", "notebooks", "lavadoras", "televisores", "relogios"}:
        return f"Parece uma lista de {category}. Destaques: " + "; ".join(showcase) + "."

    if any("repository navigation" in line or "pull requests" in line for line in normalized_lines):
        return "Parece uma pagina de repositorio com navegacao e abas principais, mais do que conteudo detalhado do projeto."

    if title_content and title_content not in showcase and showcase:
        return f"Pelo titulo da pagina, o foco parece ser: {title_content}. Na tela, vejo: " + "; ".join(showcase) + "."

    if title_content and not showcase:
        return f"Pelo titulo da pagina, o foco parece ser: {title_content}."

    if not showcase:
        return "Ainda nao consegui separar os pontos mais relevantes dessa pagina."

    return f"Vejo {len(lines)} itens principais na tela. Destaques: " + "; ".join(showcase) + "."


def explain_screen_lines(lines, page_url: str = "", page_title: str = "") -> str:
    if not lines:
        return "Ainda nao consegui extrair detalhes confiaveis da tela."

    category = detect_screen_category(lines, page_url=page_url, page_title=page_title)
    clean_title = clean_browser_title(page_title)
    title_content = trim_detail_text(parse_title_content(clean_title, page_url), max_length=260)
    showcase = content_showcase(extract_generic_focus_lines(lines, page_url=page_url, page_title=page_title, limit=6), limit=5)

    if category == "repositorio github":
        repo_name = parse_github_repo_from_url(page_url)
        profile_name = parse_github_profile_from_url(page_url)
        title_content = strip_repo_prefix_from_title(title_content, repo_name)
        visible = content_showcase(extract_github_focus_lines(lines, page_url=page_url, limit=6), limit=5)

        if repo_name:
            if title_content and visible:
                return f"Na tela esta o repositorio {repo_name}. Pelo titulo, ele parece ser sobre {title_content}. Do que ficou visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
            if title_content:
                return f"Na tela esta o repositorio {repo_name}. Pelo titulo, ele parece ser sobre {title_content}."
            if visible:
                return f"Na tela esta o repositorio {repo_name}. Do que ficou visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
            return f"Na tela esta o repositorio {repo_name}. Ainda estou vendo mais a moldura do GitHub do que README ou conteudo do projeto."

        if profile_name:
            if title_content and visible:
                return f"Na tela esta o perfil {profile_name} no GitHub. Pelo titulo, ele parece ser sobre {title_content}. No trecho visivel, encontrei: " + "; ".join(visible) + "."
            if visible:
                return f"Na tela esta o perfil {profile_name} no GitHub. No trecho visivel, encontrei: " + "; ".join(visible) + "."
            return f"Na tela esta o perfil {profile_name} no GitHub. Estou vendo visao geral, repositorios e navegacao principal do perfil."

        if title_content and visible:
            return f"Na tela esta uma pagina do GitHub. Pelo titulo, ela parece ser sobre {title_content}. No trecho visivel, encontrei: " + "; ".join(visible) + "."
        if visible:
            return "Na tela esta uma pagina do GitHub. No trecho visivel, encontrei: " + "; ".join(visible) + "."
        return "Na tela esta uma pagina do GitHub, mas ainda com pouco conteudo util exposto."

    if category == "video youtube":
        title = title_content or clean_title or "um video no YouTube"
        filtered = [line for line in showcase if normalize_text_for_match(line) not in {"up next", "youtube"}]
        if filtered:
            return f"Na tela esta a pagina de video {title}. No que ficou visivel, encontrei: " + "; ".join(filtered[:3]) + "."
        return f"Na tela esta a pagina de video {title}."

    if category == "noticia":
        visible = content_showcase(extract_generic_focus_lines(lines, page_url=page_url, page_title=page_title, limit=8), limit=5)
        if title_content and visible:
            return f"Na tela parece haver uma noticia sobre {title_content}. Do trecho visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
        if title_content:
            return f"Na tela parece haver uma noticia sobre {title_content}."
        if visible:
            return "Na tela parece haver uma noticia. Do trecho visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
        return "Na tela parece haver uma noticia, mas ainda nao separei o corpo principal do restante da pagina."

    if category in {"smartphones", "notebooks", "lavadoras", "televisores", "relogios"}:
        if title_content and title_content not in showcase:
            return f"Parece uma lista de {category}. Pelo titulo da pagina, o foco parece ser {title_content}. Entre os itens visiveis, vejo: " + "; ".join(showcase[:4]) + "."
        return f"Parece uma lista de {category}. Entre os itens visiveis, vejo: " + "; ".join(showcase[:4]) + "."

    if category == "financas":
        visible = content_showcase(extract_finance_focus_lines(lines, limit=6), limit=5)
        if title_content and visible:
            return f"Na tela esta uma pagina financeira. Pelo titulo, ela parece ser sobre {title_content}. Do que ficou visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
        if visible:
            return "Na tela esta uma pagina financeira. Do que ficou visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
        if title_content:
            return f"Na tela esta uma pagina financeira. Pelo titulo, ela parece ser sobre {title_content}, mas ainda nao capturei os valores e rotulos principais."
        return "Na tela esta uma pagina financeira, mas ainda nao capturei os valores e rotulos principais."

    if title_content and showcase:
        return f"Pelo titulo da pagina, o foco parece ser {title_content}. No conteudo visivel, encontrei: " + "; ".join(showcase[:4]) + "."

    if title_content:
        summary = summarize_screen_lines(lines, page_url=page_url, page_title=page_title)
        if summary and "nao consegui" not in normalize_text_for_match(summary):
            return summary
        return f"Pelo titulo da pagina, o foco parece ser {title_content}, mas ainda nao separei detalhes confiaveis na area visivel."

    if not showcase:
        return "Ainda nao consegui separar detalhes confiaveis da area visivel da tela."

    return "No conteudo visivel, encontrei: " + "; ".join(showcase[:4]) + "."


def should_auto_summarize(lines, quality_score: int, page_url: str = "", page_title: str = "") -> bool:
    if not lines:
        return False

    if detect_screen_category(lines, page_url=page_url, page_title=page_title) in {"repositorio github", "video youtube", "financas", "noticia"}:
        return True

    summary_hint = summarize_screen_lines(lines, page_url=page_url, page_title=page_title).lower()
    if "precos e parcelas" in summary_hint:
        return True

    if quality_score < 22:
        return True

    long_lines = sum(1 for line in lines if len(line) >= 70)
    if len(lines) >= 6 and long_lines >= 4:
        return True

    if len("; ".join(lines)) >= 520:
        return True

    return False


def investment_screen_summary(lines, page_url: str = "", page_title: str = "") -> str:
    category = detect_screen_category(lines, page_url=page_url, page_title=page_title)
    title_content = parse_title_content(clean_browser_title(page_title), page_url)
    metrics = extract_finance_metrics(lines, limit=7)
    focus_lines = extract_finance_focus_lines(lines, limit=7)

    if category != "financas" and not metrics:
        return "Nao parece ser uma tela financeira. Abra sua carteira, ativo ou pagina de investimentos e peca de novo."

    if metrics:
        intro = "Resumo financeiro da tela"
        if title_content:
            intro += f" ({trim_detail_text(title_content, max_length=90)})"
        return (
            intro
            + ": "
            + "; ".join(metrics)
            + ". Dados lidos da tela atual; nao e recomendacao de compra ou venda."
        )

    if focus_lines:
        return (
            "Modo investimentos: encontrei uma pagina financeira, mas os valores principais nao ficaram bem pareados com rotulos. "
            "Pontos visiveis: "
            + "; ".join(content_showcase(focus_lines, limit=5))
            + "."
        )

    return "Modo investimentos: a pagina parece financeira, mas ainda nao capturei patrimonio, rentabilidade, proventos ou posicoes com clareza."
