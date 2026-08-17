from aiogram.fsm.state import State, StatesGroup


class ApplicationForm(StatesGroup):
    waiting_for_vacancy       = State()  # 0  — выбор вакансии
    waiting_for_search_query  = State()  # 0b — RAG поиск
    waiting_for_vacancy_confirm = State() # 0c — карточка вакансии: Apply / Back
    waiting_for_full_name     = State()  # 1
    waiting_for_consent       = State()  # 2
    waiting_for_resume        = State()  # 3
    waiting_for_contact       = State()  # 4
    waiting_for_location      = State()  # 5
    waiting_for_age           = State()  # 6
    waiting_for_languages     = State()  # 7  — было english_level
    waiting_for_experience    = State()  # 8  — новое
    waiting_for_salary        = State()  # 9
    waiting_for_start_date    = State()  # 10
    waiting_for_work_type     = State()  # 11 — было contract_type