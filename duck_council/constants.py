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

    class agent_names:
        WINNER = 'winner'
        PRAGMATIC = 'pragmatic'
        ETHICAL = 'ethical'
        EMO = 'emo'
        RISKY = 'risky'