from core.router_utils import normalize_text


def detect_image_analysis_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {
        "analisar imagem no navegador",
        "analisar a imagem no navegador",
        "interpretar imagem no navegador",
        "interpretar a imagem no navegador",
        "identificar elementos no navegador",
        "descrever cena no navegador",
        "o que tem na imagem do navegador",
        "o que ha na imagem do navegador",
        "ler imagem no navegador",
        "ver imagem no navegador",
        "ler visual do navegador",
        "leitura visual do navegador",
    }:
        return {"intent": "image_analyze_browser", "target": None}

    if lower in {
        "analisar imagem copiada",
        "interpretar imagem copiada",
        "descrever imagem copiada",
        "analisar imagem do clipboard",
        "interpretar imagem do clipboard",
        "analisar imagem da area de transferencia",
        "interpretar imagem da area de transferencia",
        "analisar print copiado",
        "ler imagem copiada",
        "ler clipboard",
        "ler o clipboard",
        "ler area de transferencia",
    }:
        return {"intent": "image_analyze_clipboard", "target": None}

    if lower in {
        "analisar grafico",
        "analisa grafico",
        "analise grafico",
        "interpretar grafico",
        "interpreta grafico",
        "interprete grafico",
        "interpretar grafico da tela",
        "ler grafico",
    }:
        return {"intent": "image_analyze_screen_graph", "target": None}

    if lower in {
        "analisar imagem",
        "analisa imagem",
        "analise imagem",
        "interpretar imagem",
        "interpreta imagem",
        "interprete imagem",
        "descrever imagem",
        "descreve imagem",
        "descreva imagem",
        "descrever a imagem",
        "identificar elementos",
        "identifica elementos",
        "identifique elementos",
        "descrever cena",
        "descreve cena",
        "descreva cena",
        "descrever a cena",
        "o que aparece nessa imagem",
        "o que aparece na imagem",
        "o que tem nessa imagem",
        "o que tem na imagem",
        "o que ha nessa imagem",
        "o que ha na imagem",
    }:
        return {"intent": "image_analyze_screen", "target": None}

    if lower in {
        "analisar imagem da tela",
        "analisar a imagem da tela",
        "analisa imagem da tela",
        "analise a imagem da tela",
        "interpretar imagem da tela",
        "interpretar a imagem da tela",
        "identificar elementos da tela",
        "descrever imagem da tela",
        "descreve imagem da tela",
        "descreva imagem da tela",
        "o que aparece na tela",
        "ler tela",
        "leia a tela",
        "ler visual da tela",
        "leitura visual da tela",
        "analisar print da tela",
        "analisar screenshot da tela",
        "ler imagem da tela",
        "leia imagem da tela",
        "ocr da tela",
        "ver imagem da tela",
    }:
        return {"intent": "image_analyze_screen", "target": None}

    for prefix in (
        "analisar grafico ",
        "interpretar grafico ",
    ):
        if lower.startswith(prefix):
            target = user_input[len(prefix):].strip()
            if target:
                return {"intent": "image_analyze_graph", "target": target}

    for prefix in (
        "analisar imagem ",
        "analisa imagem ",
        "interpretar imagem ",
        "interprete imagem ",
        "descrever imagem ",
        "descreva imagem ",
        "identificar elementos em ",
        "identificar elementos da imagem ",
        "o que tem na imagem ",
        "o que aparece na imagem ",
        "o que ha na imagem ",
        "analisar grafico ",
        "interpretar grafico ",
        "ler imagem ",
        "leia a imagem ",
        "extrair texto da imagem ",
        "extrai texto da imagem ",
        "ocr da imagem ",
        "ler arquivo ",
        "leia o arquivo ",
        "leitura visual do arquivo ",
        "analisar print ",
        "analisa print ",
        "analisar screenshot ",
    ):
        if lower.startswith(prefix):
            target = user_input[len(prefix):].strip()
            if target:
                return {"intent": "image_analyze", "target": target}

    return None


IMAGE_DETECTORS = (
    detect_image_analysis_command,
)
