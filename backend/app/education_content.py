"""
Seed content for the education companion: fraud-awareness topics (used
for daily advice rotation and as the chat companion's factual
grounding) and quiz questions, in English, French, and Kreol Morisyen.

This is real, stable guidance, never share an OTP, verify through
official channels, not content that needs an AI model to state
correctly. The future AI layer's role is explaining and personalizing
this content conversationally, and eventually generating new quiz
questions (see the source="ai_generated" distinction on QuizQuestion),
not inventing the underlying facts from scratch.

Grounded in the same real research already used elsewhere in this
project: the Mauritius Financial Crimes Commission's 2025-2026
enforcement bulletins, and the specific real scam patterns (fake
investment schemes, OTP-phishing, impersonation) those bulletins named
as the most common financial crime type in the country.

Each topic/question stores its title, body, prompt, options, and
explanation as {"en": ..., "fr": ..., "cr": ...} dicts (see
models.EducationTopic and models.QuizQuestion) rather than one row per
language, so a single stable id serves all three languages.

Honest limitation: French text was reviewed carefully; Kreol text is a
first pass, following the same principle already established
elsewhere in this project (indicator_extractor.py, explanations_i18n.py):
capturing the real meaning and tone in natural Kreol phrasing, not a
mechanical word-for-word translation. Mauritian Kreol has no single
standardized spelling system, so this reflects one reasonable informal
spelling choice, not an authoritative orthography.
"""

EDUCATION_TOPICS = [
    {
        "title": {
            "en": "Never share your OTP, even with your bank",
            "fr": "Ne partagez jamais votre OTP, même avec votre banque",
            "cr": "Pa zame partaz ou OTP, mem ar ou labank",
        },
        "body": {
            "en": (
                "A one-time password (OTP) exists to prove a transaction is genuinely yours. "
                "No legitimate bank, telecom provider, or government office will ever call, text, "
                "or email you asking you to read your OTP back to them. If a message urges you to "
                "'verify your OTP' or 'confirm your code', that request itself is the scam, not a "
                "legitimate part of any real verification process."
            ),
            "fr": (
                "Un mot de passe à usage unique (OTP) existe pour prouver qu'une transaction est "
                "réellement la vôtre. Aucune banque, aucun opérateur télécom ni aucun bureau "
                "gouvernemental légitime ne vous appellera, ne vous enverra de SMS ou d'e-mail pour "
                "vous demander de leur communiquer votre OTP. Si un message vous presse de "
                "« vérifier votre OTP » ou de « confirmer votre code », cette demande est elle-même "
                "l'arnaque, elle ne fait partie d'aucun processus de vérification légitime."
            ),
            "cr": (
                "Enn OTP existe pou prouve ki enn transaksion se vremem ou-lipmem ki pe fer li. "
                "Okenn labank, operater telefonn, ouswa biro gouvernman legitim pa zame pou apel "
                "ou, avoy sms, ouswa email pou demann ou donn zot ou OTP. Si enn mesaz pouse ou "
                "pou 'verifie ou OTP' ouswa 'konfirm ou kod', sa demande la limem se leskrokri, "
                "li pa fer parti okenn vre prosesis verifikasion."
            ),
        },
        "category": "otp",
    },
    {
        "title": {
            "en": "Urgency is a manufactured pressure tactic",
            "fr": "L'urgence est une tactique de pression artificielle",
            "cr": "Irzansi se enn taktik presion fabrike",
        },
        "body": {
            "en": (
                "Messages claiming your account will be suspended 'today', or that you have "
                "'24 hours' to act, are designed to make you skip the step where you'd normally "
                "stop and think. A real institution's genuine deadlines are rarely this dramatic, "
                "and they never depend on you acting within minutes of reading a text message. "
                "When you feel rushed, that feeling is itself worth noticing."
            ),
            "fr": (
                "Les messages affirmant que votre compte sera suspendu « aujourd'hui », ou que "
                "vous avez « 24 heures » pour agir, sont conçus pour vous faire sauter l'étape où "
                "vous vous arrêteriez normalement pour réfléchir. Les véritables délais d'une "
                "institution réelle sont rarement aussi dramatiques, et ne dépendent jamais d'une "
                "action de votre part dans les minutes suivant la lecture d'un SMS. Lorsque vous "
                "vous sentez pressé, ce sentiment lui-même mérite d'être remarqué."
            ),
            "cr": (
                "Bann mesaz ki dir ou kont pou sispann 'zordi mem', ouswa ki ou ena '24 er' pou "
                "azir, zot fer expre pou fer ou sote lepa kot ou ti pou normalman arete pou "
                "reflesi. Bann vre delaï enn institision reel rarman osi dramatik, ek zame zot pa "
                "depann lor ou azir dan bann minit apre ou finn lir enn sms. Kan ou santi ou pouse, "
                "sa santiman la limem i merit ou remark li."
            ),
        },
        "category": "urgency",
    },
    {
        "title": {
            "en": "A real bank's name in a message doesn't make the message real",
            "fr": "Le nom d'une vraie banque dans un message ne rend pas le message authentique",
            "cr": "Non enn vre labank dan enn mesaz pa fer sa mesaz la vre",
        },
        "body": {
            "en": (
                "Scammers regularly use a real institution's name, logo, and even a lookalike "
                "domain to make a fraudulent message look legitimate. Verifying that a bank's "
                "name is real confirms the NAME is real, it says nothing about whether this "
                "particular message actually came from them. Always contact an institution "
                "through a number or website you already know is theirs, never one provided "
                "inside the message you're checking."
            ),
            "fr": (
                "Les escrocs utilisent régulièrement le nom, le logo et même un domaine ressemblant "
                "à celui d'une véritable institution pour rendre un message frauduleux crédible. "
                "Vérifier que le nom d'une banque est réel confirme que le NOM est réel, cela ne "
                "prouve en rien que ce message particulier provient effectivement d'elle. Contactez "
                "toujours une institution via un numéro ou un site web dont vous connaissez déjà "
                "l'authenticité, jamais celui fourni dans le message que vous vérifiez."
            ),
            "cr": (
                "Bann eskrok souvan servi non, logo, e mem enn domenn ki resanble avek enn vre "
                "institision pou fer enn mesaz frodiler paret legitim. Verifie ki non enn labank li "
                "vre konfirm ki sa NON la li vre, sa pa dir nanye lor si sa mesaz partikilie la "
                "vremem sorti kot zot. Touzour kontakte enn institision atraver enn nimero ouswa "
                "enn sit web ou deza konnen li pou zot, zame enn ki finn done dan mesaz ou pe verifie."
            ),
        },
        "category": "impersonation",
    },
    {
        "title": {
            "en": "Guaranteed high returns are a guaranteed red flag",
            "fr": "Des rendements élevés garantis sont un signal d'alarme garanti",
            "cr": "Retour elve garanti se enn signal alarm garanti",
        },
        "body": {
            "en": (
                "Investment offers promising fixed, unusually high, or 'risk-free' returns are "
                "one of the most common fraud patterns in Mauritius today, real investments "
                "always carry real risk, and no legitimate advisor guarantees a specific return. "
                "One documented case saw a single scammer extort over a million rupees from "
                "dozens of victims through exactly this kind of fake crypto investment scheme, "
                "run entirely over social media."
            ),
            "fr": (
                "Les offres d'investissement promettant des rendements fixes, anormalement élevés "
                "ou « sans risque » sont l'un des schémas de fraude les plus courants à Maurice "
                "aujourd'hui, un investissement réel comporte toujours un risque réel, et aucun "
                "conseiller légitime ne garantit un rendement précis. Un cas documenté a vu un seul "
                "escroc extorquer plus d'un million de roupies à des dizaines de victimes via "
                "exactement ce type de faux schéma d'investissement crypto, mené entièrement sur "
                "les réseaux sociaux."
            ),
            "cr": (
                "Bann ofer investisman ki promet retour fix, extra-ordinerman elve, ouswa 'san "
                "risk' se enn parmi bann model frod pli komen Moris zordi, enn vre investisman "
                "touzour ena vre risk, ek okenn konseye legitim pa garanti enn retour presi. Enn "
                "ka dokimante finn montre enn sel eskrok finn extorke plis ki enn milion roupi kot "
                "plizir dizenn viktim atraver exakteman sa kalite fos eskem investisman crypto, "
                "fer antierman lor rezo social."
            ),
        },
        "category": "investment",
    },
    {
        "title": {
            "en": "A lookalike link is not the real thing",
            "fr": "Un lien qui ressemble n'est pas le vrai",
            "cr": "Enn lien ki resanble pa sa vre kikenn",
        },
        "body": {
            "en": (
                "A link that looks like a bank's real domain but isn't is built to look "
                "trustworthy at a glance while pointing somewhere else entirely. Before clicking "
                "any link in an unexpected message, check the actual domain carefully, or better, "
                "don't click it at all, and instead type the institution's known website address "
                "directly into your browser yourself."
            ),
            "fr": (
                "Un lien qui ressemble au vrai domaine d'une banque mais qui ne l'est pas est conçu "
                "pour paraître digne de confiance au premier coup d'œil tout en pointant vers un "
                "endroit totalement différent. Avant de cliquer sur un lien dans un message "
                "inattendu, vérifiez attentivement le domaine réel, ou mieux, ne cliquez pas du "
                "tout, et tapez plutôt vous-même l'adresse du site web connu de l'institution "
                "directement dans votre navigateur."
            ),
            "cr": (
                "Enn lien ki paret kouma vre domenn enn labank me ki pa sa, li fer expre pou paret "
                "diyn konfians a premie regar pandan ki li pwente ver enn kotsa net diferan. Avan "
                "ou klik lor okenn lien dan enn mesaz inatandi, verifie byin domenn reel la, ouswa "
                "pli bon, pa klik ditou, e plito tape ou-mem adres sit web ou konnen ki pou sa "
                "institision la direkteman dan ou browser."
            ),
        },
        "category": "impersonation",
    },
    {
        "title": {
            "en": "Slow down before sending money or sharing details",
            "fr": "Ralentissez avant d'envoyer de l'argent ou de partager des informations",
            "cr": "Aret prese avan ou anvoy larzan ouswa partaz detay",
        },
        "body": {
            "en": (
                "There is no legitimate financial situation where you must decide, right now, "
                "in the next few minutes, whether to send money or share your card details. "
                "If a message pressures you toward instant action, that pressure is a signal on "
                "its own. Pausing to verify independently costs you a few minutes; acting on a "
                "scam can cost far more."
            ),
            "fr": (
                "Il n'existe aucune situation financière légitime où vous devez décider, "
                "immédiatement, dans les prochaines minutes, s'il faut envoyer de l'argent ou "
                "partager les détails de votre carte. Si un message vous pousse vers une action "
                "instantanée, cette pression est en elle-même un signal. Prendre une pause pour "
                "vérifier indépendamment vous coûte quelques minutes ; céder à une arnaque peut "
                "coûter bien plus."
            ),
            "cr": (
                "Pa ena okenn sitiasion finansie legitim kot ou bizin desid, tousuit, dan "
                "prosenn bann minit, si pou anvoy larzan ouswa partaz detay ou kart. Si enn mesaz "
                "fors ou ver enn aksion tousuit, sa presion la limem se enn signal. Aret pou "
                "verifie endepandaman ou perdi zis detrwa minit; azir lor enn eskrokri kapav "
                "kout ou boukou plis."
            ),
        },
        "category": "general",
    },
]

QUIZ_QUESTIONS = [
    {
        "prompt": {
            "en": "Your bank sends you a text with your OTP and says 'never share this code.' Ten minutes later, someone calling from the same number asks you to read the code back to verify a transaction. What should you do?",
            "fr": "Votre banque vous envoie un SMS avec votre OTP et dit « ne partagez jamais ce code ». Dix minutes plus tard, quelqu'un appelant depuis le même numéro vous demande de relire ce code pour vérifier une transaction. Que devez-vous faire ?",
            "cr": "Ou labank avoy ou enn sms ar ou OTP e dir 'pa zame partaz sa kod la.' Dis minit apre, enn dimoune ki apel ar mem nimero demann ou pou relir sa kod la pou verifie enn transaksion. Ki ou bizin fer?",
        },
        "options": {
            "en": [
                {"id": "a", "text": "Read it back, since it's the same number that sent the OTP"},
                {"id": "b", "text": "Refuse, hang up, and call your bank back using the number on your card"},
                {"id": "c", "text": "Read back only the last 3 digits as a compromise"},
            ],
            "fr": [
                {"id": "a", "text": "Le relire, puisque c'est le même numéro qui a envoyé l'OTP"},
                {"id": "b", "text": "Refuser, raccrocher, et rappeler votre banque en utilisant le numéro figurant sur votre carte"},
                {"id": "c", "text": "Relire seulement les 3 derniers chiffres comme compromis"},
            ],
            "cr": [
                {"id": "a", "text": "Relir li, vi ki se mem nimero ki finn avoy OTP la"},
                {"id": "b", "text": "Refize, rakroze, e rapel ou labank servi nimero lor ou kart"},
                {"id": "c", "text": "Relir zis dernie 3 chifr kouma enn konpromi"},
            ],
        },
        "correct_option_id": "b",
        "explanation": {
            "en": "A real bank never asks you to read an OTP back over the phone, that request is the scam itself, regardless of what number it appears to come from (caller ID can be spoofed). Always hang up and call back using a number you already know is genuine.",
            "fr": "Une vraie banque ne vous demande jamais de relire un OTP par téléphone, cette demande est l'arnaque elle-même, peu importe le numéro d'où elle semble provenir (l'identifiant de l'appelant peut être falsifié). Raccrochez toujours et rappelez en utilisant un numéro dont vous savez déjà qu'il est authentique.",
            "cr": "Enn vre labank pa zame demann ou pou relir enn OTP lor telefonn, sa demande la limem se leskrokri, kit ki nimero li paret sorti (caller ID kapav ganny falsifie). Touzour rakroze e rapel servi enn nimero ou deza konnen li vre.",
        },
        "category": "otp",
    },
    {
        "prompt": {
            "en": "A message says: 'URGENT: Your account will be permanently closed in 2 hours unless you verify now.' What's the most useful first reaction?",
            "fr": "Un message dit : « URGENT : Votre compte sera définitivement fermé dans 2 heures si vous ne vérifiez pas maintenant. » Quelle est la première réaction la plus utile ?",
            "cr": "Enn mesaz dir: 'IRZAN: Ou kont pou ferme pou touzour dan 2 er si ou pa verifie tousuit.' Ki premie reaksion pli itil?",
        },
        "options": {
            "en": [
                {"id": "a", "text": "Act immediately, since the deadline sounds serious"},
                {"id": "b", "text": "Notice the urgency itself as a warning sign, and verify independently before doing anything"},
                {"id": "c", "text": "Wait exactly 2 hours to see what happens"},
            ],
            "fr": [
                {"id": "a", "text": "Agir immédiatement, car le délai semble sérieux"},
                {"id": "b", "text": "Remarquer l'urgence elle-même comme un signal d'alarme, et vérifier indépendamment avant de faire quoi que ce soit"},
                {"id": "c", "text": "Attendre exactement 2 heures pour voir ce qui se passe"},
            ],
            "cr": [
                {"id": "a", "text": "Azir tousuit, vi ki delai la paret serie"},
                {"id": "b", "text": "Remark irzansi la limem kouma enn signal alarm, e verifie endepandaman avan fer nanye"},
                {"id": "c", "text": "Atann exakteman 2 er pou get ki arive"},
            ],
        },
        "correct_option_id": "b",
        "explanation": {
            "en": "Extreme urgency is a manufactured pressure tactic designed to stop you from thinking it through. Genuine account issues from real institutions don't typically come with dramatic, minutes-long deadlines delivered by text.",
            "fr": "L'urgence extrême est une tactique de pression artificielle conçue pour vous empêcher de réfléchir. Les véritables problèmes de compte d'institutions réelles ne s'accompagnent généralement pas de délais dramatiques de quelques minutes livrés par SMS.",
            "cr": "Irzansi extrem se enn taktik presion fabrike fer expre pou anpes ou reflesi byin. Bann vre problem kont sorti kot bann vre institision pa normalman vini avek bann delai dramatik, dan bann minit, par sms.",
        },
        "category": "urgency",
    },
    {
        "prompt": {
            "en": "A message claiming to be from a real, well-known bank asks you to click a link to 'reactivate' your account. The bank's name is spelled correctly and the message looks professional. Does this confirm the message is genuine?",
            "fr": "Un message prétendant provenir d'une banque réelle et bien connue vous demande de cliquer sur un lien pour « réactiver » votre compte. Le nom de la banque est correctement orthographié et le message paraît professionnel. Cela confirme-t-il que le message est authentique ?",
            "cr": "Enn mesaz ki pretann sorti kot enn vre labank byin konnen demann ou pou klik lor enn lien pou 'reaktive' ou kont. Non labank la byin ekrir e mesaz la paret profesionel. Eski sa konfirm mesaz la vre?",
        },
        "options": {
            "en": [
                {"id": "a", "text": "Yes, a professional-looking message from a real bank's name is safe"},
                {"id": "b", "text": "No, a real institution's name being used doesn't confirm who actually sent this specific message"},
            ],
            "fr": [
                {"id": "a", "text": "Oui, un message d'apparence professionnelle avec le nom d'une vraie banque est sûr"},
                {"id": "b", "text": "Non, l'utilisation du nom d'une institution réelle ne confirme pas qui a réellement envoyé ce message spécifique"},
            ],
            "cr": [
                {"id": "a", "text": "Oui, enn mesaz ki paret profesionel avek non enn vre labank li san danze"},
                {"id": "b", "text": "Non, servi non enn vre institision pa konfirm kisannla vremem finn avoy sa mesaz partikilie la"},
            ],
        },
        "correct_option_id": "b",
        "explanation": {
            "en": "Verifying that a bank's name is real confirms the NAME exists, it says nothing about whether this particular message actually came from them. Scammers regularly impersonate real, well-known institutions convincingly.",
            "fr": "Vérifier que le nom d'une banque est réel confirme que le NOM existe, cela ne prouve en rien que ce message particulier provient effectivement d'elle. Les escrocs usurpent régulièrement l'identité d'institutions réelles et bien connues de manière convaincante.",
            "cr": "Verifie ki non enn labank li vre konfirm ki sa NON la existe, sa pa dir nanye lor si sa mesaz partikilie la vremem sorti kot zot. Bann eskrok souvan inperson bann vre institision byin konnen dan enn fason konvinkan.",
        },
        "category": "impersonation",
    },
    {
        "prompt": {
            "en": "An investment opportunity promises a guaranteed 20% monthly return with 'zero risk.' What does this most likely indicate?",
            "fr": "Une opportunité d'investissement promet un rendement mensuel garanti de 20 % avec « zéro risque ». Que cela indique-t-il le plus probablement ?",
            "cr": "Enn oportinite investisman promet enn retour mansiel garanti 20% ar 'zero risk.' Ki sa endike pli probableman?",
        },
        "options": {
            "en": [
                {"id": "a", "text": "A rare but genuine high-performing investment"},
                {"id": "b", "text": "A common fraud pattern, real investments always carry real risk"},
            ],
            "fr": [
                {"id": "a", "text": "Un investissement rare mais authentique et très performant"},
                {"id": "b", "text": "Un schéma de fraude courant, un investissement réel comporte toujours un risque réel"},
            ],
            "cr": [
                {"id": "a", "text": "Enn investisman rar me vre ki pe byin perform"},
                {"id": "b", "text": "Enn model frod komen, enn vre investisman touzour ena vre risk"},
            ],
        },
        "correct_option_id": "b",
        "explanation": {
            "en": "No legitimate investment can honestly guarantee a fixed high return with zero risk. This exact pattern, guaranteed returns framed as risk-free, is one of the most common investment scam structures.",
            "fr": "Aucun investissement légitime ne peut honnêtement garantir un rendement élevé fixe sans aucun risque. Ce schéma exact, des rendements garantis présentés comme sans risque, est l'une des structures d'arnaque à l'investissement les plus courantes.",
            "cr": "Okenn investisman legitim pa kapav onetman garanti enn retour elve fix ar zero risk. Sa model exakt la, retour garanti prezante kouma san risk, se enn parmi bann striktir eskrokri investisman pli komen.",
        },
        "category": "investment",
    },
    {
        "prompt": {
            "en": "You want to verify a message claiming to be from your bank. What's the safest way to check?",
            "fr": "Vous souhaitez vérifier un message prétendant provenir de votre banque. Quelle est la manière la plus sûre de vérifier ?",
            "cr": "Ou anvi verifie enn mesaz ki pretann sorti kot ou labank. Ki fason pli san danze pou verifie?",
        },
        "options": {
            "en": [
                {"id": "a", "text": "Click the link in the message and log in to see if it looks right"},
                {"id": "b", "text": "Call the number provided in the message"},
                {"id": "c", "text": "Contact the bank using a number or website you already know is genuine, not anything from the message"},
            ],
            "fr": [
                {"id": "a", "text": "Cliquer sur le lien dans le message et se connecter pour voir si cela semble correct"},
                {"id": "b", "text": "Appeler le numéro fourni dans le message"},
                {"id": "c", "text": "Contacter la banque via un numéro ou un site web dont vous connaissez déjà l'authenticité, rien provenant du message"},
            ],
            "cr": [
                {"id": "a", "text": "Klik lor lien dan mesaz la e konekte pou get si li paret bon"},
                {"id": "b", "text": "Apel nimero ki finn done dan mesaz la"},
                {"id": "c", "text": "Kontakte labank la servi enn nimero ouswa sit web ou deza konnen li vre, nanye ki sorti dan mesaz la"},
            ],
        },
        "correct_option_id": "c",
        "explanation": {
            "en": "Any contact detail contained in the suspicious message itself, a link, a phone number, could be part of the scam. Always use a channel you independently know is real, such as the number on your bank card or their official website typed in directly.",
            "fr": "Tout détail de contact contenu dans le message suspect lui-même, un lien, un numéro de téléphone, pourrait faire partie de l'arnaque. Utilisez toujours un canal dont vous savez de manière indépendante qu'il est réel, comme le numéro sur votre carte bancaire ou leur site web officiel tapé directement.",
            "cr": "Nenport ki detay kontak ki dan sa mesaz sispek la limem, enn lien, enn nimero telefonn, kapav fer parti eskrokri la. Touzour servi enn kanal ou konnen endepandaman li vre, kouma nimero lor ou kart labank ouswa zot sit web ofisiel tape direkteman."
        },
        "category": "impersonation",
    },
]
