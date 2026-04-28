from memory.investment_snapshot import (
    answer_investment_snapshot_question,
    format_investment_snapshot_summary,
    load_investment_snapshot,
)


def investment_memory_summary():
    return format_investment_snapshot_summary()


def investment_memory_answer(question: str):
    return answer_investment_snapshot_question(question)


def investment_memory_status():
    snapshot = load_investment_snapshot()
    if snapshot.get("updated_at"):
        return "Memória local de investimentos disponível."
    return "Ainda não há memória local de investimentos salva."
