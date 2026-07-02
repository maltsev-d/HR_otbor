from aiogram.fsm.state import State, StatesGroup


class ApplicationForm(StatesGroup):
    waiting_for_vacancy       = State()  # 0 — выбор вакансии
    waiting_for_search_query  = State()  # поиск по RAG
    waiting_for_full_name     = State()  # 1 — ФИО
    waiting_for_consent       = State()  # 2 — согласие
    waiting_for_resume        = State()  # 3 — резюме
    waiting_for_contact       = State()  # 4
    waiting_for_location      = State()  # 5
    waiting_for_age           = State()  # 6 — возраст
    waiting_for_english       = State()  # 7
    waiting_for_salary        = State()  # 8
    waiting_for_start_date    = State()  # 9
    waiting_for_contract_type = State()  # 10
    confirming                = State()