class Constants:

    class http_methods:
        GET = 'GET'
        POST = 'POST'

    class http_status_codes:
        OK=200
        BAD_REQUEST=400
        SERVER_ERROR=500

    class routes:
        health = '/'
        prompt = '/prompt'
        duck_data = '/duck_profiles'
        images = '/images/<filename>'

    class agent_names:
        LAWYER = 'lawyer'
        WITCH = 'witch'
        DOCTOR = 'doctor'
        RICH = 'rich'
        GAMER = 'gamer'
        GANGSTA = 'gangsta'
        SERIAL_KILLER = 'serial_killer'
        DIPLOMAT = 'diplomat'
        TECHNO = 'techno'
        KING = 'king'
        SPIRITUAL_MEDIUM = 'spiritual_medium'
        DETECTIVE = 'detective'
        REBEL = 'rebel'