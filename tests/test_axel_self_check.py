import unittest

from core.axel_self_check import run_axel_self_check


class AxelSelfCheckTests(unittest.TestCase):
    def test_self_check_reports_all_core_routes_ok(self):
        def fake_route(text):
            routes = {
                "axel esta ai?": {"intent": "respond", "response": "Estou aqui."},
                "oq e tesla?": {"intent": "respond", "response": "Tesla pode ser a empresa ou Nikola Tesla."},
                "me ajuda a estudar redes": {
                    "intent": "respond",
                    "response": "Sim. Para estudar redes, use perguntas de fixação.",
                },
                "me da uma ideia de presente para minha mãe": {
                    "intent": "respond",
                    "response": "Para sua mãe, escolha algo com sinal de cuidado.",
                },
                "dicas de treino sem equipamento": {
                    "intent": "respond",
                    "response": "Treino em casa sem equipamento.",
                },
                "quero comer melhor sem fazer dieta": {
                    "intent": "respond",
                    "response": "Dá para melhorar sem chamar isso de dieta.",
                },
                "me da exemplos": {
                    "intent": "respond",
                    "response": "Exemplos.",
                },
                "I'm doing well significa o que?": {
                    "intent": "respond",
                    "response": "Estou bem.",
                },
                "o que tem na tela?": {"intent": "browser_describe_screen"},
                "como o el nino afeta o VGIA11?": {"intent": "investment_memory_answer"},
                "briefing": {"intent": "daily_briefing"},
                "me lembre todo dia 2 de junho do presente do dia dos namorados dia 12/06": {
                    "intent": "reminder_add"
                },
                'analisar arquivos anexados: ["C:/fake/RedesBasico.pdf"] :: oq tem na pagina 2?': {
                    "intent": "study.analyze_files"
                },
                "toca rock e depois me da uma dica de treino": {"intent": "browser_music_session"},
                "abre youtube e depois me explica redes": {"intent": "open_url"},
                "me explica redes e toca musica para estudar": {"intent": "browser_music_session"},
                "me explica redes e depois me lembre de revisar redes amanha": {"intent": "reminder_add"},
                "me explica redes e pesquise tcp no youtube": {"intent": "browser_search_site"},
            }
            return routes[text]

        def fake_shared(text):
            if text == "personalidade":
                return "Personalidade do Axel: ligada."
            if text == "/model":
                return "Modelo do Axel: provedor auto; modelo local/chat qwen."
            if text == "/skills":
                return "Skills procedurais: estudos."
            if text == "capacidades reais do axel":
                return "Capacidades reais do Axel: Funcional: comandos. Parcial: agentes. Visual/organizacional: metas. Regra prática: verificar evidência."
            if text == "/usage":
                return "Latencia do Axel: ok."
            if text == "/help":
                return "Comandos comuns: /status."
            return "Status do Axel: operacional."

        result = run_axel_self_check(route_func=fake_route, shared_func=fake_shared)

        self.assertIn("25/25 rotas essenciais OK", result)
        self.assertIn("aprendizado", result)
        self.assertIn("conselho cotidiano", result)
        self.assertIn("arquivos", result)
        self.assertIn("auditoria de capacidades", result)

    def test_self_check_reports_route_failure(self):
        def fake_route(text):
            if text == "o que tem na tela?":
                return {"intent": "respond"}
            expected_responses = {
                "axel esta ai?": "Estou aqui.",
                "me ajuda a estudar redes": "perguntas de fixação",
                "me da uma ideia de presente para minha mãe": "sinal de cuidado",
                "dicas de treino sem equipamento": "sem equipamento",
                "quero comer melhor sem fazer dieta": "sem chamar isso de dieta",
                "me da exemplos": "Exemplos.",
                "I'm doing well significa o que?": "Estou bem",
            }
            if text in expected_responses:
                return {"intent": "respond", "response": expected_responses[text]}
            if text == "oq e tesla?":
                return {"intent": "respond", "response": "Tesla."}
            special_intents = {
                "como o el nino afeta o VGIA11?": "investment_memory_answer",
                "briefing": "daily_briefing",
                "me lembre todo dia 2 de junho do presente do dia dos namorados dia 12/06": "reminder_add",
                'analisar arquivos anexados: ["C:/fake/RedesBasico.pdf"] :: oq tem na pagina 2?': "study.analyze_files",
                "toca rock e depois me da uma dica de treino": "browser_music_session",
                "abre youtube e depois me explica redes": "open_url",
                "me explica redes e toca musica para estudar": "browser_music_session",
                "me explica redes e depois me lembre de revisar redes amanha": "reminder_add",
                "me explica redes e pesquise tcp no youtube": "browser_search_site",
            }
            if text in special_intents:
                return {"intent": special_intents[text]}
            return {
                "intent": "respond",
                "response": "Estou aqui.",
            }

        result = run_axel_self_check(
            route_func=fake_route,
            shared_func=lambda text: "Personalidade do Axel: ligada."
            if text == "personalidade"
            else "Modelo do Axel: provedor auto."
            if text == "/model"
            else "Skills procedurais: estudos."
            if text == "/skills"
            else "Capacidades reais do Axel: Regra prática."
            if text == "capacidades reais do axel"
            else "Latencia do Axel: ok."
            if text == "/usage"
            else "Comandos comuns: /status."
            if text == "/help"
            else "Status do Axel: operacional.",
        )

        self.assertIn("Atenção em", result)
        self.assertIn("leitura de tela", result)


if __name__ == "__main__":
    unittest.main()
