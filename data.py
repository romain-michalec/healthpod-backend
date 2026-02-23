from textwrap import dedent

system_prompt = dedent(  # Remove indent
    """\
    You are a friendly digital health assistant deployed in a clinical
    setting in the United Kingdom.

    You are assisting patients in answering a short lifestyle
    questionnaire about their smoking, drinking, and exercising habits,
    before helping them use wireless medical devices to collect a set of
    measurements as part of their regular monitoring for cardiovascular
    disease: weight, heart rate, and blood pressure.
    """
).strip()  # Strip leading and trailing whitespace

idle = 'Type "Hello" to start.'

welcome = dedent(
    """\
    Welcome to this self-screening health station.

    I'm here to help you take some health readings. We'll start with a
    few questions, then we'll measure your weight, heart rate, and blood
    pressure.

    Talk to me in your own words or use the buttons on the screen.

    Are you ready to begin?
    """
).strip()

ready = {
    "in general": {
        "context": dedent(
            """\
            The patient is asked if they are ready to proceed. They reply in
            their own words. Analyze their response to figure out if they are
            ready to proceed.

            They are ready if they explicitly confirm ("yes", "yes I am",
            "sure", "let's go", "okay", "I'm ready", etc). Otherwise, they are
            not ready.

            Respond with READY or NOT READY.
            """
        ).strip(),
        "valid options": [
            "READY",
            "NOT READY",
        ],
    },
    "during sensor conversation": {
        "context": "TODO",
        "valid options": "TODO",
    },
}

lifestyle = {
    "smoking": {
        "context": dedent(
            """\
            The patient is asked about their smoking habits. They reply in their
            own words. Analyze their response to figure out how much they smoke
            in an average week. Respond with one of:

            - UNCLEAR, if it is unclear how much the patient smokes based on
                their response.
            - QUESTION SKIPPED, if the patient indicates that they would rather
                not answer the question.
            - NON-SMOKER, if the patient doesn't smoke.
            - MODERATE SMOKER, if the patient smokes less than one pack of
                cigarettes in an average week.
            - HEAVY SMOKER, if the patient smokes more than one pack of
                cigarettes in an average week.

            If it is UNCLEAR how much the patient smokes based on their
            response, ask follow-up questions until the patient provides enough
            information for you to determine if they are a NON-SMOKER, a
            MODERATE SMOKER, or a HEAVY SMOKER, or until they indicate that they
            would rather SKIP the question.
            """
        ).strip(),
        "question": dedent(
            """\
            How much do you smoke in an average week?

            Tell me in your own words or choose one of the options on the
            screen.
            """
        ).strip(),
        "invalid options": [
            "UNCLEAR",
        ],
        "valid options": [
            "QUESTION SKIPPED",
            "NON-SMOKER",
            "MODERATE SMOKER",
            "HEAVY SMOKER",
        ],
    },
    "drinking": {
        "context": dedent(
            """\
            The patient is asked about their drinking habits. They reply in
            their own words. Analyze their response to figure out how much
            alcohol they drink in an average week. Respond with one of:

            - UNCLEAR, if it is unclear how much alcohol the patient drinks
                based on their response.
            - QUESTION SKIPPED, if the patient indicates that they would rather
                not answer the question.
            - NON-DRINKER, if the patient doesn't drink alcohol.
            - MODERATE DRINKER, if the patient drinks less than 14 units of
                alcohol in an average week.
            - HEAVY DRINKER, if the patient drinks more than 14 units of alcohol
                in an average week.

            If it is UNCLEAR how much alcohol the patient drinks based on their
            response, ask follow-up questions until the patient provides enough
            information for you to determine if they are a NON-DRINKER, a
            MODERATE DRINKER, or a HEAVY DRINKER, or until they indicate that
            they would rather SKIP the question.
            """
        ).strip(),
        "question": dedent(
            """\
            Now, how much alcohol do you drink in an average week?

            Tell me in your own words or choose one of the options on the
            screen.
            """
        ).strip(),
        "invalid options": [
            "UNCLEAR",
        ],
        "valid options": [
            "QUESTION SKIPPED",
            "NON-DRINKER",
            "MODERATE DRINKER",
            "HEAVY DRINKER",
        ],
    },
    "exercising": {
        "context": dedent(
            """\
            The patient is asked how active they are. They reply in their own
            words. Analyze their response to figure out how active they are in
            an average week. Respond with one of:

            - UNCLEAR, if it is unclear how active the patient is based on their
                response.
            - QUESTION SKIPPED, if the patient indicates that they would rather
                not answer the question.
            - NOT ACTIVE, if the patient has a sedentary lifestyle.
            - MODERATELY ACTIVE, if the patient does less than two hours of
                vigorous activity in an average week.
            - VERY ACTIVE, if the patient does more than two hours of vigorous
                activity in an average week.

            If it is UNCLEAR how active the patient is based on their response,
            ask follow-up questions until the patient provides enough
            information for you to determine if they are NOT ACTIVE, MODERATELY
            ACTIVE, or VERY ACTIVE, or until they indicate that they
            would rather SKIP the question.
            """
        ).strip(),
        "question": dedent(
            """\
            Now, how active are you in an average week?

            Tell me in your own words or choose one of the options on the
            screen.
            """
        ).strip(),
        "invalid options": [
            "UNCLEAR",
        ],
        "valid options": [
            "QUESTION SKIPPED",
            "NOT ACTIVE",
            "MODERATELY ACTIVE",
            "VERY ACTIVE",
        ],
    },
}

first_recap = dedent(
    """\
    Thank you. Please check your answers below. Are you ready to move on
    to taking a few health readings with the medical devices on the
    table? I will guide you through using them.
    """
).strip()







consent = """\
    You are analyzing user input in a health sensor conversation.

    Determine if the user is indicating they are READY for the sensor reading to be taken.

    They are ready if they:
    - Explicitly confirm: 'yes', 'ready', 'ok', 'sure', 'go ahead', 'let's go', 'done', 'good'
    - State they've completed the action: 'I'm on the scale', 'finger is on the sensor', 'thermometer is under my tongue', 'it's in place', etc.
    - Even if frustrated, if they confirm the action is complete: 'it is in place!', 'I already did it', 'I told you I'm ready'

    They are NOT ready if they:
    - Are asking a clarifying question
    - Are requesting help or more information
    - Have not yet completed the action

    IMPORTANT: If the user indicates they have completed the requested action (even if phrased differently), they ARE ready.

    Respond with ONLY 'YES' if they are ready to proceed.
    Respond with ONLY 'NO' if they are asking a question or haven't completed the action yet.
    """
consent = dedent(consent).strip()
