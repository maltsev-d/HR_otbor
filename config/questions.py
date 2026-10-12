import os

BOT_LANG = os.getenv("BOT_LANG", "en")

LANG_CURRENCY = {"ru": "RUB", "en": "USD", "lo": "LAK", "th": "THB"}
DEFAULT_CURRENCY = LANG_CURRENCY.get(BOT_LANG, "USD")

QUESTIONS: dict[str, dict[str, str]] = {

    # ── VACANCY FLOW ───────────────────────────────────────────
    "vacancy": {
        "ru": "Спасибо за интерес к нашей компании!\nВыберите вакансию из списка или воспользуйтесь поиском. 👇",
        "en": "Thanks for your interest!\nChoose a position from the list or use the search. 👇",
        "lo": "ຂອບໃຈທີ່ສົນໃຈບໍລິສັດຂອງເຮົາ!\nເລືອກຕຳແໜ່ງຈາກລາຍຊື່ ຫຼື ໃຊ້ການຄົ້ນຫາ. 👇",
        "th": "ขอบคุณที่สนใจบริษัทของเรา!\nเลือกตำแหน่งจากรายการหรือใช้การค้นหา 👇",
    },
    "vacancy_detail": {
        "ru": "📋 Подробнее о вакансии:",
        "en": "📋 Position details:",
        "lo": "📋 ລາຍລະອຽດຂອງຕຳແໜ່ງ:",
        "th": "📋 รายละเอียดตำแหน่ง:",
    },
    "vacancy_apply": {
        "ru": "✅ Откликнуться",
        "en": "✅ Apply",
        "lo": "✅ ສະໝັກ",
        "th": "✅ สมัครงาน",
    },
    "vacancy_back": {
        "ru": "← К списку вакансий",
        "en": "← Back to list",
        "lo": "← ກັບໄປລາຍຊື່",
        "th": "← กลับไปรายการ",
    },
    "search_prompt": {
        "ru": "💬 Опишите что ищёте — должность, сферу или условия.\n\n<i>Например: «разработчик» или «продажи»</i>",
        "en": "💬 Describe what you're looking for — role, field, or conditions.\n\n<i>E.g.: 'work with animals' or 'sales'</i>",
        "lo": "💬 ອະທິບາຍສິ່ງທີ່ທ່ານຊອກຫາ.\n\n<i>ຕົວຢ່າງ: 'ເຮັດວຽກກັບສັດ'</i>",
        "th": "💬 อธิบายสิ่งที่คุณกำลังมองหา\n\n<i>เช่น: 'งานกับสัตว์' หรือ 'งานขาย'</i>",
    },
    "search_btn": {
        "ru": "🔍 Найти другую вакансию",
        "en": "🔍 Search positions",
        "lo": "🔍 ຄົ້ນຫາຕຳແໜ່ງ",
        "th": "🔍 ค้นหาตำแหน่ง",
    },
    "search_no_results": {
        "ru": "😔 Ничего не нашлось. Попробуйте описать иначе.",
        "en": "😔 Nothing found. Try describing it differently.",
        "lo": "😔 ບໍ່ພົບຜົນ. ລອງອະທິບາຍຄືນໃໝ່.",
        "th": "😔 ไม่พบผลลัพธ์ ลองอธิบายใหม่อีกครั้ง",
    },

    # ── АНКЕТА ─────────────────────────────────────────────────
    "full_name": {
        "ru": "Как вас зовут? Напишите имя и фамилию 📝",
        "en": "What's your name? Please write your first and last name 📝",
        "lo": "ຊື່ຂອງທ່ານແມ່ນຫຍັງ? ກະລຸນາຂຽນຊື່ ແລະ ນາມສະກຸນ 📝",
        "th": "ชื่อของคุณคืออะไร? กรุณาระบุชื่อและนามสกุล 📝",
    },
    "consent": {
        "ru": "Необходимая формальность. Согласны ли вы на обработку ваших персональных данных? Данные используются только для рассмотрения вашей кандидатуры. 📋",
        "en": "Quick formality. Do you agree to the processing of your personal data for the purpose of reviewing your application? You can request deletion at any time. 📋",
        "lo": "ທ່ານຍິນຍອມໃຫ້ໃຊ້ຂໍ້ມູນສ່ວນຕົວຂອງທ່ານເພື່ອພິຈາລະນາໃບສະໝັກບໍ? 📋",
        "th": "คุณยินยอมให้เราเก็บและใช้ข้อมูลส่วนตัวของคุณเพื่อพิจารณาใบสมัครงานหรือไม่? 📋",
    },
    "consent_yes": {
        "ru": "✅ Да, согласен(а)",
        "en": "✅ Yes, I agree",
        "lo": "✅ ຕົກລົງ",
        "th": "✅ ยินยอม",
    },
    "consent_no": {
        "ru": "❌ Нет",
        "en": "❌ No",
        "lo": "❌ ບໍ່",
        "th": "❌ ไม่ยินยอม",
    },
    "consent_declined": {
        "ru": "😔 Без согласия мы не можем принять вашу анкету. Если передумаете — нажмите /start.",
        "en": "😔 Without consent we can't process your application. You can restart anytime with /start.",
        "lo": "😔 ພວກເຮົາບໍ່ສາມາດດຳເນີນການໄດ້ໂດຍບໍ່ມີການຍິນຍອມ. ກົດ /start ເພື່ອເລີ່ມຄືນໃໝ່.",
        "th": "😔 เราไม่สามารถดำเนินการได้โดยไม่ได้รับความยินยอม กด /start เพื่อเริ่มใหม่",
    },
    "resume": {
        "ru": "Прикрепите резюме — файлом (PDF/DOC) или ссылкой 📎",
        "en": "Please attach your resume — as a file (PDF/DOC) or a link 📎",
        "lo": "ກະລຸນາຄັດຕິດ CV ຂອງທ່ານ — ເປັນໄຟລ໌ (PDF/DOC) ຫຼື ລິ້ງ 📎",
        "th": "กรุณาแนบเรซูเม่ของคุณ — เป็นไฟล์ (PDF/DOC) หรือลิงก์ 📎",
    },
    "resume_invalid": {
        "ru": "Отправьте файл резюме или ссылку (начинается с http).",
        "en": "Please send a resume file or a link (starting with http).",
        "lo": "ກະລຸນາສົ່ງໄຟລ໌ CV ຫຼື ລິ້ງ (ເລີ່ມຕົ້ນດ້ວຍ http).",
        "th": "กรุณาส่งไฟล์เรซูเม่หรือลิงก์ (เริ่มต้นด้วย http)",
    },
    "contact": {
        "ru": "Как с вами удобнее связаться? 📲\n(Telegram, WhatsApp, телефон или e-mail)",
        "en": "How can we contact you? 📲\n(LINE, WhatsApp, Facebook, phone or email)",
        "lo": "ພວກເຮົາຕິດຕໍ່ທ່ານໄດ້ແນວໃດ? 📲\n(WhatsApp, Facebook, ໂທລະສັບ ຫຼື ອີເມວ)",
        "th": "เราติดต่อคุณได้อย่างไร? 📲\n(LINE, WhatsApp, Facebook, โทรศัพท์ หรืออีเมล)",
    },
    "location": {
        "ru": "В каком городе вы сейчас проживаете? 🌍",
        "en": "Which city do you currently live in? 🌍",
        "lo": "ທ່ານອາໄສຢູ່ເມືອງໃດໃນປັດຈຸບັນ? 🌍",
        "th": "คุณอาศัยอยู่ที่เมืองไหนในปัจจุบัน? 🌍",
    },
    "age": {
        "ru": "Сколько вам лет? 🎂",
        "en": "How old are you? 🎂",
        "lo": "ທ່ານອາຍຸເທົ່າໃດ? 🎂",
        "th": "คุณอายุเท่าไหร่? 🎂",
    },
    "age_invalid": {
        "ru": "Введите возраст числом, например: 25",
        "en": "Please enter your age as a number, e.g.: 25",
        "lo": "ກະລຸນາໃສ່ອາຍຸເປັນຕົວເລກ, ເຊັ່ນ: 25",
        "th": "กรุณาระบุอายุเป็นตัวเลข เช่น 25",
    },
    "languages": {
        "ru": "Какими языками вы владеете? 🌐\n(укажите язык и уровень, например: Английский B2, Тайский базовый)",
        "en": "What languages do you speak? 🌐\n(e.g.: English — fluent, Thai — basic)",
        "lo": "ທ່ານເວົ້າພາສາຫຍັງໄດ້ແດ່? 🌐\n(ເຊັ່ນ: ລາວ — ດີ, ອັງກິດ — ພື້ນຖານ)",
        "th": "คุณพูดภาษาอะไรได้บ้าง? 🌐\n(เช่น: ไทย — คล่อง, อังกฤษ — พื้นฐาน)",
    },
    "experience": {
        "ru": "Расскажите о своём опыте работы в данной сфере 💼\n(кратко: где работали, сколько лет)",
        "en": "Tell us about your work experience in this field 💼\n(briefly: where you worked, how many years)",
        "lo": "ບອກພວກເຮົາກ່ຽວກັບປະສົບການເຮັດວຽກຂອງທ່ານໃນຂະແໜງນີ້ 💼",
        "th": "บอกเกี่ยวกับประสบการณ์ทำงานของคุณในสาขานี้ 💼\n(สั้นๆ: ทำงานที่ไหน กี่ปี)",
    },
    "salary": {
        "ru": "Какой уровень дохода вы рассматриваете? 💰\nУкажите сумму цифрой.",
        "en": "What are your salary expectations? 💰\nEnter the amount as a number.",
        "lo": "ທ່ານຄາດຫວັງເງິນເດືອນເທົ່າໃດ? 💰\nໃສ່ຈຳນວນເງິນ.",
        "th": "คุณคาดหวังเงินเดือนเท่าไหร่? 💰\nระบุจำนวนเงิน",
    },
    "salary_invalid": {
        "ru": "Введите число, например: 80000",
        "en": "Please enter a number, e.g.: 1500",
        "lo": "ກະລຸນາໃສ່ຕົວເລກ, ເຊັ່ນ: 5000000",
        "th": "กรุณาระบุตัวเลข เช่น: 25000",
    },
    "start_date": {
        "ru": "Когда вы сможете приступить к работе?\n(например: «сразу», «через 2 недели» или укажите дату)",
        "en": "When can you start?\n(e.g.: 'immediately', 'in 2 weeks', or a specific date)",
        "lo": "ທ່ານສາມາດເລີ່ມເຮັດວຽກໄດ້ເມື່ອໃດ?\n(ເຊັ່ນ: 'ທັນທີ', 'ສອງອາທິດຕໍ່ໄປ')",
        "th": "คุณสามารถเริ่มงานได้เมื่อไหร่?\n(เช่น: 'ทันที', 'อีก 2 สัปดาห์')",
    },
    "work_type": {
        "ru": "Какой формат работы вам подходит? 📄\n(Полная занятость, Частичная, Фриланс, Контракт)",
        "en": "What type of employment are you looking for? 📄\n(Full-time, Part-time, Freelance, Contract)",
        "lo": "ທ່ານຊອກຫາຮູບແບບການເຮັດວຽກແບບໃດ? 📄\n(ເຕັມເວລາ, ບາງສ່ວນ, ຟຣີແລນ, ສັນຍາ)",
        "th": "คุณกำลังมองหารูปแบบการทำงานแบบไหน? 📄\n(เต็มเวลา, พาร์ทไทม์, ฟรีแลนซ์, สัญญาจ้าง)",
    },
    "form_complete": {
        "ru": "✅ Спасибо за ответы! Анкета отправлена. Ожидайте обратной связи.",
        "en": "✅ Thank you! Your application has been submitted. We'll be in touch soon.",
        "lo": "✅ ຂອບໃຈ! ໃບສະໝັກຂອງທ່ານຖືກສົ່ງແລ້ວ. ພວກເຮົາຈະຕິດຕໍ່ທ່ານໃນໄວໆນີ້.",
        "th": "✅ ขอบคุณ! ใบสมัครของคุณถูกส่งเรียบร้อยแล้ว เราจะติดต่อกลับเร็วๆ นี้",
    },
    "form_rejected": {
        "ru": "😔 Спасибо за отклик, но по данной позиции мы не можем продолжить с вами процесс.",
        "en": "😔 Thank you for applying. Unfortunately, we're unable to proceed with your application for this position.",
        "lo": "😔 ຂອບໃຈທີ່ສະໝັກ. ຂໍອະໄພ, ພວກເຮົາບໍ່ສາມາດດຳເນີນການຕໍ່ກັບໃບສະໝັກຂອງທ່ານໄດ້.",
        "th": "😔 ขอบคุณที่สมัคร แต่เราไม่สามารถดำเนินการต่อกับใบสมัครของคุณสำหรับตำแหน่งนี้ได้",
    },
    "no_vacancies": {
        "ru": "😔 Активных вакансий пока нет.",
        "en": "😔 No active positions available at the moment.",
        "lo": "😔 ບໍ່ມີຕຳແໜ່ງທີ່ເປີດຮັບໃນຂະນະນີ້.",
        "th": "😔 ขณะนี้ไม่มีตำแหน่งที่เปิดรับสมัคร",
    },

    # ── NUDGE ──────────────────────────────────────────────────
    "nudge_draft_text": {
        "ru": "👋 Вы начали заполнять анкету, но не завершили.\nОсталось буквально пара шагов — нажмите кнопку ниже:",
        "en": "👋 You started filling out the application but didn't finish.\nJust a couple of steps left — tap the button below:",
        "lo": "👋 ທ່ານເລີ່ມຕື່ມຂໍ້ມູນໃບສະໝັກແຕ່ຍັງບໍ່ທັນສຳເລັດ.\nເຫຼືອອີກສອງສາມຂັ້ນຕອນ — ກົດປຸ່ມລຸ່ມນີ້:",
        "th": "👋 คุณเริ่มกรอกใบสมัครแต่ยังไม่เสร็จ\nเหลืออีกแค่ไม่กี่ขั้นตอน — แตะปุ่มด้านล่าง:",
    },
    "nudge_draft_btn": {
        "ru": "✍️ Продолжить заполнение",
        "en": "✍️ Continue application",
        "lo": "✍️ ສືບຕໍ່ການສະໝັກ",
        "th": "✍️ ทำต่อ",
    },
    "nudge_invite_text": {
        "ru": "⏰ Напоминаем: вас пригласили на собеседование",
        "en": "⏰ Reminder: you've been invited for an interview",
        "lo": "⏰ ແຈ້ງເຕືອນ: ທ່ານໄດ້ຮັບເຊີນໃຫ້ເຂົ້າສຳພາດ",
        "th": "⏰ แจ้งเตือน: คุณได้รับเชิญเข้าสัมภาษณ์",
    },
    "nudge_invite_suffix": {
        "ru": "\n\nПожалуйста, подтвердите или откажитесь:",
        "en": "\n\nPlease confirm or decline:",
        "lo": "\n\nກະລຸນາຢືນຢັນ ຫຼື ປະຕິເສດ:",
        "th": "\n\nกรุณายืนยันหรือปฏิเสธ:",
    },
    "nudge_invite_confirm": {
        "ru": "✅ Подтвердить",
        "en": "✅ Confirm",
        "lo": "✅ ຢືນຢັນ",
        "th": "✅ ยืนยัน",
    },
    "nudge_invite_decline": {
        "ru": "❌ Отказаться",
        "en": "❌ Decline",
        "lo": "❌ ປະຕິເສດ",
        "th": "❌ ปฏิเสธ",
    },
    "nudge_app_complete": {
        "ru": "👍 Ваша анкета уже заполнена!",
        "en": "👍 Your application is already complete!",
        "lo": "👍 ໃບສະໝັກຂອງທ່ານສຳເລັດແລ້ວ!",
        "th": "👍 ใบสมัครของคุณเสร็จสมบูรณ์แล้ว!",
    },
    "nudge_app_not_found": {
        "ru": "Анкета не найдена",
        "en": "Application not found",
        "lo": "ບໍ່ພົບໃບສະໝັກ",
        "th": "ไม่พบใบสมัคร",
    },

    # ── HR ACTIONS — сообщения кандидату ──────────────────────
    "hr_invite_text": {
        "ru": "👋 {name}!\n\n📅 Вас приглашают на собеседование:\n<b>{dt}</b>\n\nПодтвердите участие:",
        "en": "👋 {name}!\n\n📅 You have been invited for an interview:\n<b>{dt}</b>\n\nPlease confirm or decline:",
        "lo": "👋 {name}!\n\n📅 ທ່ານໄດ້ຮັບເຊີນໃຫ້ເຂົ້າສຳພາດ:\n<b>{dt}</b>\n\nກະລຸນາຢືນຢັນ ຫຼື ປະຕິເສດ:",
        "th": "👋 {name}!\n\n📅 คุณได้รับเชิญเข้าสัมภาษณ์:\n<b>{dt}</b>\n\nกรุณายืนยันหรือปฏิเสธ:",
    },
    "hr_invite_confirm_btn": {
        "ru": "✅ Подтвердить",
        "en": "✅ Confirm",
        "lo": "✅ ຢືນຢັນ",
        "th": "✅ ยืนยัน",
    },
    "hr_invite_decline_btn": {
        "ru": "❌ Отказаться",
        "en": "❌ Decline",
        "lo": "❌ ປະຕິເສດ",
        "th": "❌ ปฏิเสธ",
    },
    "hr_confirmed_candidate": {
        "ru": "✅ Спасибо! Собеседование подтверждено.",
        "en": "✅ Thank you! Your interview is confirmed.",
        "lo": "✅ ຂອບໃຈ! ການສຳພາດຂອງທ່ານໄດ້ຮັບການຢືນຢັນແລ້ວ.",
        "th": "✅ ขอบคุณ! การสัมภาษณ์ของคุณได้รับการยืนยันแล้ว",
    },
    "hr_confirmed_see_you": {
        "ru": "📅 Ждём вас {dt}",
        "en": "📅 See you on {dt}",
        "lo": "📅 ພວກເຮົາລໍຖ້າທ່ານໃນວັນທີ {dt}",
        "th": "📅 พบกันวันที่ {dt}",
    },
    "hr_declined_candidate": {
        "ru": "❌ Вы отказались от собеседования. Спасибо за отклик!",
        "en": "❌ You have declined the interview. Thank you for your application!",
        "lo": "❌ ທ່ານໄດ້ປະຕິເສດການສຳພາດ. ຂອບໃຈທີ່ສະໝັກ!",
        "th": "❌ คุณปฏิเสธการสัมภาษณ์ ขอบคุณที่สมัครงาน!",
    },
    "hr_clarify_msg": {
        "ru": "📩 Сообщение от HR:\n\n{text}\n\nВы можете ответить прямо в этот чат.",
        "en": "📩 Message from HR:\n\n{text}\n\nYou can reply directly in this chat.",
        "lo": "📩 ຂໍ້ຄວາມຈາກ HR:\n\n{text}\n\nທ່ານສາມາດຕອບກັບໂດຍກົງໃນການສົນທະນານີ້.",
        "th": "📩 ข้อความจาก HR:\n\n{text}\n\nคุณสามารถตอบกลับได้โดยตรงในแชทนี้",
    },
    "hr_reply_sent": {
        "ru": "✅ Ваш ответ отправлен HR-менеджеру.",
        "en": "✅ Your reply has been sent to HR.",
        "lo": "✅ ຄຳຕອບຂອງທ່ານຖືກສົ່ງໄປຫາ HR ແລ້ວ.",
        "th": "✅ คำตอบของคุณถูกส่งไปยัง HR แล้ว",
    },
    "hr_reply_failed": {
        "ru": "❌ Не удалось доставить ответ. Попробуйте позже.",
        "en": "❌ Failed to deliver reply. Please try again.",
        "lo": "❌ ບໍ່ສາມາດສົ່ງຄຳຕອບໄດ້. ກະລຸນາລອງໃໝ່.",
        "th": "❌ ไม่สามารถส่งคำตอบได้ กรุณาลองใหม่อีกครั้ง",
    },
    "hr_resume_link": {
        "ru": "📄 Резюме (ссылка): {url}",
        "en": "📄 Resume (link): {url}",
        "lo": "📄 CV (ລິ້ງ): {url}",
        "th": "📄 เรซูเม่ (ลิงก์): {url}",
    },

    # ── HR NOTIFICATIONS — уведомления в admin-чат ─────────────
    "hr_new_candidate": {
        "ru": "🆕 Новый кандидат",
        "en": "🆕 New candidate",
        "lo": "🆕 ຜູ້ສະໝັກໃໝ່",
        "th": "🆕 ผู้สมัครใหม่",
    },
    "hr_notify_vacancy": {
        "ru": "💼 Вакансия: {title}",
        "en": "💼 Position: {title}",
        "lo": "💼 ຕຳແໜ່ງ: {title}",
        "th": "💼 ตำแหน่ง: {title}",
    },
    "hr_notify_age": {
        "ru": "🎂 Возраст: {age}",
        "en": "🎂 Age: {age}",
        "lo": "🎂 ອາຍຸ: {age}",
        "th": "🎂 อายุ: {age}",
    },
    "hr_notify_salary": {
        "ru": "💰 Зарплата: {salary}",
        "en": "💰 Salary: {salary}",
        "lo": "💰 ເງິນເດືອນ: {salary}",
        "th": "💰 เงินเดือน: {salary}",
    },
    "hr_notify_languages": {
        "ru": "🌐 Языки: {languages}",
        "en": "🌐 Languages: {languages}",
        "lo": "🌐 ພາສາ: {languages}",
        "th": "🌐 ภาษา: {languages}",
    },
    "hr_notify_location": {
        "ru": "📍 Город: {location}",
        "en": "📍 Location: {location}",
        "lo": "📍 ສະຖານທີ່: {location}",
        "th": "📍 สถานที่: {location}",
    },
    "hr_notify_ai": {
        "ru": "🤖 AI-анализ:\n{summary}",
        "en": "🤖 AI summary:\n{summary}",
        "lo": "🤖 AI ສະຫຼຸບ:\n{summary}",
        "th": "🤖 AI สรุป:\n{summary}",
    },
    "hr_btn_invite": {
        "ru": "✅ Пригласить",
        "en": "✅ Invite",
        "lo": "✅ ເຊີນ",
        "th": "✅ เชิญ",
    },
    "hr_btn_reject": {
        "ru": "❌ Отказать",
        "en": "❌ Reject",
        "lo": "❌ ປະຕິເສດ",
        "th": "❌ ปฏิเสธ",
    },
    "hr_btn_clarify": {
        "ru": "❓ Уточнить",
        "en": "❓ Clarify",
        "lo": "❓ ສອບຖາມ",
        "th": "❓ สอบถาม",
    },
    "hr_btn_resume": {
        "ru": "📄 Резюме",
        "en": "📄 Resume",
        "lo": "📄 CV",
        "th": "📄 เรซูเม่",
    },
    "hr_btn_resume_link": {
        "ru": "📄 Резюме (ссылка)",
        "en": "📄 Resume (link)",
        "lo": "📄 CV (ລິ້ງ)",
        "th": "📄 เรซูเม่ (ลิงก์)",
    },
    "hr_candidate_confirmed": {
        "ru": "✅ Кандидат <b>{name}</b> подтвердил собеседование{dt}.",
        "en": "✅ <b>{name}</b> confirmed the interview{dt}.",
        "lo": "✅ <b>{name}</b> ຢືນຢັນການສຳພາດ{dt}.",
        "th": "✅ <b>{name}</b> ยืนยันการสัมภาษณ์{dt}",
    },
    "hr_candidate_declined": {
        "ru": "❌ Кандидат <b>{name}</b> отказался от собеседования{dt}.",
        "en": "❌ <b>{name}</b> declined the interview{dt}.",
        "lo": "❌ <b>{name}</b> ປະຕິເສດການສຳພາດ{dt}.",
        "th": "❌ <b>{name}</b> ปฏิเสธการสัมภาษณ์{dt}",
    },
    "hr_candidate_reply": {
        "ru": "📩 Ответ от кандидата <b>{name}</b>:\n\n{text}",
        "en": "📩 Reply from <b>{name}</b>:\n\n{text}",
        "lo": "📩 ຄຳຕອບຈາກ <b>{name}</b>:\n\n{text}",
        "th": "📩 คำตอบจาก <b>{name}</b>:\n\n{text}",
    },
    "hr_rejection_sent": {
        "ru": "Кандидату отправлен отказ.",
        "en": "Rejection sent to candidate.",
        "lo": "ສົ່ງການປະຕິເສດໄປຫາຜູ້ສະໝັກແລ້ວ.",
        "th": "ส่งการปฏิเสธไปยังผู้สมัครแล้ว",
    },
    "hr_msg_sent": {
        "ru": "✅ Сообщение отправлено кандидату. Ответ придёт сюда.",
        "en": "✅ Message sent. Reply will appear here.",
        "lo": "✅ ສົ່ງຂໍ້ຄວາມຫາຜູ້ສະໝັກແລ້ວ. ຄຳຕອບຈະມາທີ່ນີ້.",
        "th": "✅ ส่งข้อความแล้ว คำตอบจะปรากฏที่นี่",
    },
    "hr_msg_failed": {
        "ru": "❌ Не удалось отправить сообщение кандидату.",
        "en": "❌ Failed to send message to candidate.",
        "lo": "❌ ບໍ່ສາມາດສົ່ງຂໍ້ຄວາມຫາຜູ້ສະໝັກໄດ້.",
        "th": "❌ ไม่สามารถส่งข้อความไปยังผู้สมัครได้",
    },
    "hr_invite_input": {
        "ru": "Введите дату и время собеседования:\nФормат: <code>12.07.25 15:00</code> или <code>12.07.2025 15:00</code>",
        "en": "Enter interview date and time:\nFormat: <code>12.07.25 15:00</code> or <code>12.07.2025 15:00</code>",
        "lo": "ໃສ່ວັນທີ ແລະ ເວລາສຳພາດ:\nຮູບແບບ: <code>12.07.25 15:00</code>",
        "th": "ระบุวันที่และเวลาสัมภาษณ์:\nรูปแบบ: <code>12.07.25 15:00</code>",
    },
    "hr_invite_parse_error": {
        "ru": "Не могу распознать дату. Попробуй: <code>12.07.25 15:00</code>",
        "en": "Can't parse the date. Try: <code>12.07.25 15:00</code>",
        "lo": "ບໍ່ສາມາດອ່ານວັນທີໄດ້. ລອງ: <code>12.07.25 15:00</code>",
        "th": "ไม่สามารถอ่านวันที่ได้ ลอง: <code>12.07.25 15:00</code>",
    },
    "hr_invite_sent": {
        "ru": "📨 Приглашение отправлено. Собеседование: {dt}",
        "en": "📨 Invitation sent. Interview: {dt}",
        "lo": "📨 ສົ່ງຄຳເຊີນແລ້ວ. ສຳພາດ: {dt}",
        "th": "📨 ส่งคำเชิญแล้ว สัมภาษณ์: {dt}",
    },
    "hr_clarify_input": {
        "ru": "✏️ Введите сообщение для кандидата <b>{name}</b>:\n(оно будет отправлено ему в Telegram)",
        "en": "✏️ Enter message for <b>{name}</b>:\n(will be sent to them in Telegram)",
        "lo": "✏️ ໃສ່ຂໍ້ຄວາມສຳລັບ <b>{name}</b>:\n(ຈະສົ່ງໄປຫາພວກເຂົາໃນ Telegram)",
        "th": "✏️ ระบุข้อความสำหรับ <b>{name}</b>:\n(จะส่งไปยัง Telegram ของพวกเขา)",
    },
    "hr_resume_not_found": {
        "ru": "Резюме не найдено",
        "en": "Resume not found",
        "lo": "ບໍ່ພົບ CV",
        "th": "ไม่พบเรซูเม่",
    },
    "hr_resume_send_failed": {
        "ru": "Не удалось отправить файл",
        "en": "Failed to send file",
        "lo": "ບໍ່ສາມາດສົ່ງໄຟລ໌ໄດ້",
        "th": "ไม่สามารถส่งไฟล์ได้",
    },
    "hr_resume_unavailable": {
        "ru": "Файл резюме недоступен",
        "en": "Resume file not available",
        "lo": "ໄຟລ໌ CV ບໍ່ສາມາດໃຊ້ງານໄດ້",
        "th": "ไฟล์เรซูเม่ไม่พร้อมใช้งาน",
    },
    "hr_candidate_not_found": {
        "ru": "Кандидат не найден",
        "en": "Candidate not found",
        "lo": "ບໍ່ພົບຜູ້ສະໝັກ",
        "th": "ไม่พบผู้สมัคร",
    },
}


def q(key: str) -> str:
    """Получить текст на текущем языке бота."""
    lang_questions = QUESTIONS.get(key)
    if not lang_questions:
        raise KeyError(f"Question key '{key}' not found in QUESTIONS")
    return (
        lang_questions.get(BOT_LANG)
        or lang_questions.get("en")
        or next(iter(lang_questions.values()))
    )