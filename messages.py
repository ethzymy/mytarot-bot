"""
MyTarot — Trilingual Message Templates
=========================================
All system messages (non-AI-generated) in Chinese, English, and Malay.
"""


def _t(zh: str, en: str, ms: str, lang: str = "zh") -> str:
    """Select message by language code."""
    return {"zh": zh, "en": en, "ms": ms}.get(lang, zh)


# ================= Onboarding (First-Time Setup) =================

def onboarding_birthday(lang="zh"):
    return _t(
        "🐱 *灵猫需要感知你的命运频率...*\n\n"
        "🎂 请输入你的出生日期：\n"
        "格式：YYYY-MM-DD（如 1990-05-15）",

        "🐱 *Oracle Cat needs to sense your destiny frequency...*\n\n"
        "🎂 Please enter your date of birth:\n"
        "Format: YYYY-MM-DD (e.g. 1990-05-15)",

        "🐱 *Oracle Cat perlu merasai frekuensi takdir anda...*\n\n"
        "🎂 Sila masukkan tarikh lahir anda:\n"
        "Format: YYYY-MM-DD (cth. 1990-05-15)",
        lang
    )


def onboarding_birth_hour(lang="zh"):
    return _t(
        "⏰ *出生时辰*（可选）\n\n"
        "灵猫的感知力随时辰变化而增强。\n"
        "如果你知道自己的出生时辰，请输入：\n\n"
        "格式：HH:MM（如 08:30）\n"
        "或中国时辰：子/丑/寅/卯/辰/巳/午/未/申/酉/戌/亥\n\n"
        "不知道？回复【跳过】即可。",

        "⏰ *Birth Hour* (optional)\n\n"
        "Oracle Cat's perception strengthens with birth hour.\n"
        "If you know your birth time, please enter:\n\n"
        "Format: HH:MM (e.g. 08:30)\n\n"
        "Don't know? Reply【Skip】.",

        "⏰ *Waktu Lahir* (pilihan)\n\n"
        "Persepsi Oracle Cat meningkat dengan waktu lahir.\n"
        "Jika anda tahu, sila masukkan:\n\n"
        "Format: HH:MM (cth. 08:30)\n\n"
        "Tidak tahu? Balas【Langkau】.",
        lang
    )


def onboarding_gender(lang="zh"):
    return _t(
        "🌙 *能量属性*\n\n"
        "塔罗的阴阳能量会因人而异——\n\n"
        "1️⃣ ☀️ 男 (阳)\n"
        "2️⃣ 🌙 女 (阴)\n"
        "3️⃣ 🌀 不透露\n\n"
        "回复数字 (1-3)。",

        "🌙 *Energy Attribute*\n\n"
        "Tarot's yin-yang energy varies by individual—\n\n"
        "1️⃣ ☀️ Male (Yang)\n"
        "2️⃣ 🌙 Female (Yin)\n"
        "3️⃣ 🌀 Prefer not to say\n\n"
        "Reply with a number (1-3).",

        "🌙 *Atribut Tenaga*\n\n"
        "Tenaga yin-yang Tarot berbeza mengikut individu—\n\n"
        "1️⃣ ☀️ Lelaki (Yang)\n"
        "2️⃣ 🌙 Perempuan (Yin)\n"
        "3️⃣ 🌀 Tidak mahu nyatakan\n\n"
        "Balas dengan nombor (1-3).",
        lang
    )


def onboarding_lucky_number(lang="zh"):
    return _t(
        "🔢 *直觉数字*\n\n"
        "闭上眼，让灵猫引导你——\n"
        "脑海中浮现的第一个数字是多少？\n\n"
        "请输入 *1 到 99* 之间的数字。\n"
        "这个数字将成为你的命运印记 ✨",

        "🔢 *Intuition Number*\n\n"
        "Close your eyes, let Oracle Cat guide you—\n"
        "What is the first number that comes to mind?\n\n"
        "Enter a number between *1 and 99*.\n"
        "This number becomes your destiny seal ✨",

        "🔢 *Nombor Intuisi*\n\n"
        "Pejamkan mata, biar Oracle Cat membimbing—\n"
        "Apakah nombor pertama dalam fikiran anda?\n\n"
        "Masukkan nombor antara *1 hingga 99*.\n"
        "Nombor ini menjadi meterai takdir anda ✨",
        lang
    )


def onboarding_complete(lang="zh"):
    return _t(
        "✨ *命运档案已建立！*\n\n"
        "灵猫已完整感知你的灵性频率。\n"
        "从现在开始，每一次解读都将为你量身定制。\n\n"
        "🐱 喵呜~ 准备好了吗？让我们开始吧！\n\n"
        "请选择你想探索的领域：\n\n"
        "1️⃣ 💌 爱情\n"
        "2️⃣ 💼 事业\n"
        "3️⃣ 🎓 学业\n"
        "4️⃣ 🌀 其他",

        "✨ *Destiny Profile Created!*\n\n"
        "Oracle Cat has fully sensed your spiritual frequency.\n"
        "From now on, every reading is tailored for you.\n\n"
        "🐱 Meow~ Ready? Let's begin!\n\n"
        "Choose your area of interest:\n\n"
        "1️⃣ 💌 Love\n"
        "2️⃣ 💼 Career\n"
        "3️⃣ 🎓 Studies\n"
        "4️⃣ 🌀 Other",

        "✨ *Profil Takdir Dicipta!*\n\n"
        "Oracle Cat telah merasai frekuensi rohani anda.\n"
        "Mulai sekarang, setiap bacaan disesuaikan untuk anda.\n\n"
        "🐱 Meow~ Sedia? Jom mulakan!\n\n"
        "Pilih bidang yang ingin diterokai:\n\n"
        "1️⃣ 💌 Cinta\n"
        "2️⃣ 💼 Kerjaya\n"
        "3️⃣ 🎓 Pelajaran\n"
        "4️⃣ 🌀 Lain-lain",
        lang
    )

def welcome(lang="zh"):
    return _t(
        "🐱 *欢迎来到 My Tarot！*\n\n"
        "我是灵猫 Oracle，你的专属塔罗向导。\n"
        "让我用古老的猫之智慧，为你揭开命运的面纱。\n\n"
        "请选择你想探索的领域：\n\n"
        "1️⃣ 💌 爱情\n"
        "2️⃣ 💼 事业\n"
        "3️⃣ 🎓 学业\n"
        "4️⃣ 🌀 其他\n\n"
        "📌 直接回复数字 (1-4) 即可开始。",

        "🐱 *Welcome to My Tarot!*\n\n"
        "I am Oracle Cat, your tarot guide.\n"
        "Let me unveil the mysteries of fate with ancient feline wisdom.\n\n"
        "Choose your area of interest:\n\n"
        "1️⃣ 💌 Love\n"
        "2️⃣ 💼 Career\n"
        "3️⃣ 🎓 Studies\n"
        "4️⃣ 🌀 Other\n\n"
        "📌 Reply with a number (1-4) to begin.",

        "🐱 *Selamat datang ke My Tarot!*\n\n"
        "Saya Oracle Cat, panduan tarot anda.\n"
        "Izinkan saya membuka rahsia takdir anda.\n\n"
        "Pilih bidang yang ingin diterokai:\n\n"
        "1️⃣ 💌 Cinta\n"
        "2️⃣ 💼 Kerjaya\n"
        "3️⃣ 🎓 Pelajaran\n"
        "4️⃣ 🌀 Lain-lain\n\n"
        "📌 Balas dengan nombor (1-4).",
        lang
    )


def category_selected(category_label, lang="zh"):
    return _t(
        f"✅ 已选择【{category_label}】领域。\n\n"
        "现在请选择服务：\n\n"
        "🔮 回复【抽卡】— 灵猫为你抽一张牌\n"
        "📈 回复【运势】— 查看12个月运势曲线\n"
        "🃏 回复【实体牌】— 使用你的实体卡牌解读",

        f"✅ You've selected【{category_label}】.\n\n"
        "Choose a service:\n\n"
        "🔮 Reply【Draw】— Let Oracle Cat draw a card\n"
        "📈 Reply【Fortune】— View 12-month fortune curve\n"
        "🃏 Reply【Real Card】— Use your physical deck",

        f"✅ Anda memilih【{category_label}】.\n\n"
        "Pilih perkhidmatan:\n\n"
        "🔮 Balas【Cabut】— Biar Oracle Cat cabut kad\n"
        "📈 Balas【Nasib】— Lihat lengkung nasib 12 bulan\n"
        "🃏 Balas【Kad Fizikal】— Guna dek fizikal anda",
        lang
    )


def preparing_draw(category_label, lang="zh"):
    return _t(
        f"🔮 正在为您连接【{category_label}】领域的灵性场域...\n"
        "卡牌正在抽取，请稍候...",
        f"🔮 Connecting to the spiritual field of【{category_label}】...\n"
        "Drawing your card, please wait...",
        f"🔮 Menyambung ke medan rohani【{category_label}】...\n"
        "Mencabut kad anda, sila tunggu...",
        lang
    )


# ================= Draw Limits =================

def draw_limit_reached(remaining_hours, remaining_mins, lang="zh"):
    return _t(
        f"⚠️ *今日灵感已达上限*\n\n"
        f"灵猫的灵性频率需要恢复。\n"
        f"⏳ 距离下次免费抽卡：*{remaining_hours}小时 {remaining_mins}分钟*\n\n"
        "💡 *升级 Pro 即可获得每日5次抽卡额度！*",

        f"⚠️ *Daily draw limit reached*\n\n"
        f"Oracle Cat needs to recharge.\n"
        f"⏳ Next free draw in: *{remaining_hours}h {remaining_mins}m*\n\n"
        "💡 *Upgrade to Pro for 5 daily draws!*",

        f"⚠️ *Had cabutan harian tercapai*\n\n"
        f"Oracle Cat perlu mengecas semula.\n"
        f"⏳ Cabutan percuma seterusnya: *{remaining_hours}j {remaining_mins}m*\n\n"
        "💡 *Naik taraf ke Pro untuk 5 cabutan harian!*",
        lang
    )


# ================= Subscription =================

def subscription_menu(lang="zh"):
    return _t(
        "📋 *订阅计划*\n\n"
        "1️⃣ *Pro* — RM 45/月\n"
        "   · 每日5次抽卡\n"
        "   · 完整12个月运势曲线\n"
        "   · 绑定2个生日\n"
        "   · 每周推送\n\n"
        "2️⃣ *Agent* — RM 99/月\n"
        "   · 每日25次抽卡\n"
        "   · 帮朋友/客户抽卡\n"
        "   · 专业品牌卡片\n\n"
        "3️⃣ *Affiliate* — RM 266/月\n"
        "   · 每日60次抽卡\n"
        "   · 推荐返现10%\n"
        "   · 首月赠送实体卡牌\n\n"
        "回复数字 (1-3) 选择计划。",

        "📋 *Subscription Plans*\n\n"
        "1️⃣ *Pro* — RM 45/month\n"
        "   · 5 daily draws\n"
        "   · Full 12-month fortune curve\n"
        "   · 2 birthday slots\n"
        "   · Weekly push\n\n"
        "2️⃣ *Agent* — RM 99/month\n"
        "   · 25 daily draws\n"
        "   · Draw for friends/clients\n"
        "   · Professional branding\n\n"
        "3️⃣ *Affiliate* — RM 266/month\n"
        "   · 60 daily draws\n"
        "   · 10% referral cashback\n"
        "   · Free physical deck on signup\n\n"
        "Reply with a number (1-3).",

        "📋 *Pelan Langganan*\n\n"
        "1️⃣ *Pro* — RM 45/bulan\n"
        "   · 5 cabutan harian\n"
        "   · Lengkung nasib 12 bulan penuh\n"
        "   · 2 slot tarikh lahir\n"
        "   · Push mingguan\n\n"
        "2️⃣ *Agent* — RM 99/bulan\n"
        "   · 25 cabutan harian\n"
        "   · Cabut untuk kawan/pelanggan\n"
        "   · Penjenamaan profesional\n\n"
        "3️⃣ *Affiliate* — RM 266/bulan\n"
        "   · 60 cabutan harian\n"
        "   · 10% pulangan rujukan\n"
        "   · Dek fizikal percuma\n\n"
        "Balas dengan nombor (1-3).",
        lang
    )


# ================= Referral =================

def referral_prompt(lang="zh"):
    return _t(
        "🎁 是否有朋友的推荐码？\n\n"
        "有 → 请输入推荐码（如 REF-KEAN）\n"
        "没有 → 回复【跳过】",

        "🎁 Do you have a referral code from a friend?\n\n"
        "Yes → Enter the code (e.g. REF-KEAN)\n"
        "No → Reply【Skip】",

        "🎁 Adakah anda mempunyai kod rujukan?\n\n"
        "Ya → Masukkan kod (cth. REF-KEAN)\n"
        "Tidak → Balas【Langkau】",
        lang
    )


# ================= PIN Activation =================

def pin_prompt(lang="zh"):
    return _t(
        "🃏 *实体卡牌激活*\n\n"
        "请输入卡盒内侧的 PIN 码：\n"
        "格式：MT-XXXX（如 MT-8K3F）\n\n"
        "回复【取消】返回主菜单。",

        "🃏 *Physical Deck Activation*\n\n"
        "Enter the PIN code inside your card box:\n"
        "Format: MT-XXXX (e.g. MT-8K3F)\n\n"
        "Reply【Cancel】to return.",

        "🃏 *Pengaktifan Dek Fizikal*\n\n"
        "Masukkan kod PIN di dalam kotak kad:\n"
        "Format: MT-XXXX (cth. MT-8K3F)\n\n"
        "Balas【Batal】untuk kembali.",
        lang
    )


# ================= Real Card Mode =================

def real_card_spread_menu(available_spreads, lang="zh"):
    menu = []
    spread_names = {
        "single": ("1️⃣ 单牌解读", "1️⃣ Single Card", "1️⃣ Kad Tunggal"),
        "three_card": ("2️⃣ 三牌阵", "2️⃣ Three Card", "2️⃣ Tiga Kad"),
        "five_element": ("3️⃣ 五元素牌阵", "3️⃣ Five Element", "3️⃣ Lima Elemen"),
        "celtic_cross": ("4️⃣ 凯尔特十字", "4️⃣ Celtic Cross", "4️⃣ Salib Celtic"),
    }
    idx = {"zh": 0, "en": 1, "ms": 2}.get(lang, 0)

    for spread in available_spreads:
        if spread in spread_names:
            menu.append(spread_names[spread][idx])

    header = _t("🃏 *选择牌阵：*\n\n", "🃏 *Choose a spread:*\n\n",
                "🃏 *Pilih susunan:*\n\n", lang)
    footer = _t("\n\n回复数字选择。", "\n\nReply with a number.", "\n\nBalas dengan nombor.", lang)

    return header + "\n".join(menu) + footer


def real_card_input_prompt(card_count, lang="zh"):
    return _t(
        f"📝 请输入你抽到的 {card_count} 张牌的编号：\n\n"
        f"格式：用逗号或空格分隔（如 15, 42, 7）\n"
        "编号范围：0-77\n"
        "可选标注正逆位：15正 42逆 7正\n\n"
        "回复【对照表】查看编号列表。",

        f"📝 Enter the numbers of your {card_count} drawn cards:\n\n"
        f"Format: separate with commas or spaces (e.g. 15, 42, 7)\n"
        "Number range: 0-77\n"
        "Optional orientation: 15U 42R 7U\n\n"
        "Reply【List】for card number reference.",

        f"📝 Masukkan nombor {card_count} kad yang dicabut:\n\n"
        f"Format: pisahkan dengan koma atau ruang (cth. 15, 42, 7)\n"
        "Julat nombor: 0-77\n\n"
        "Balas【Senarai】untuk rujukan nombor kad.",
        lang
    )


# ================= Disclaimer =================

def disclaimer(lang="zh"):
    return _t(
        "📜 *免责声明*\n\n"
        "My Tarot 提供的所有解读内容仅供娱乐和参考目的。\n"
        "本服务不构成专业建议（包括但不限于心理、医疗、法律或财务建议）。\n\n"
        "继续使用即表示您理解并同意以上条款。\n\n"
        "回复【同意】继续使用。",

        "📜 *Disclaimer*\n\n"
        "All readings from My Tarot are for entertainment purposes only.\n"
        "This service does not constitute professional advice.\n\n"
        "By continuing, you acknowledge and agree to these terms.\n\n"
        "Reply【Agree】to continue.",

        "📜 *Penafian*\n\n"
        "Semua bacaan My Tarot adalah untuk tujuan hiburan sahaja.\n"
        "Perkhidmatan ini bukan nasihat profesional.\n\n"
        "Dengan meneruskan, anda bersetuju dengan syarat ini.\n\n"
        "Balas【Setuju】untuk meneruskan.",
        lang
    )


# ================= Errors & Generic =================

def invalid_input(lang="zh"):
    return _t(
        "⚠️ 灵猫未能识别，请重新输入。",
        "⚠️ Oracle Cat didn't understand. Please try again.",
        "⚠️ Oracle Cat tidak faham. Sila cuba lagi.",
        lang
    )


def return_to_menu(lang="zh"):
    return _t(
        "🐱 回复【你好】或【Hi】开始新的占卜之旅。",
        "🐱 Reply【Hi】to start a new reading.",
        "🐱 Balas【Hi】untuk memulakan bacaan baru.",
        lang
    )


# ================= Engagement Hooks =================

def post_draw_hook(lang="zh"):
    return _t(
        "🐱 刚才的解读对你有启发吗？\n这是你的命运牌列中尚未翻开的牌...\n\n回复【抽卡】继续探索，或回复【菜单】更换领域。",

        "🐱 Did that reading resonate with you?\nHere is an unopened card from your destiny spread...\n\nReply【Draw】to continue, or【Menu】to change focus.",

        "🐱 Adakah bacaan itu memberi inspirasi?\nIni adalah kad yang belum dibuka dari susunan takdir anda...\n\nBalas【Cabut】untuk teruskan, atau【Menu】untuk tukar bidang.",
        lang
    )
