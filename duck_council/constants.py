from dataclasses import dataclass

@dataclass
class Route:
    path: str
    description: str
    method: str
    
class Constants:

    class http_methods:
        GET = 'GET'
        POST = 'POST'

    class http_status_codes:
        OK=200
        BAD_REQUEST=400
        SERVER_ERROR=500

    class routes:
        health = Route('/', 'Health check endpoint', 'GET')
        prompt = Route('/prompt', 'Submit a prompt to the duck council', 'POST')
        duck_data = Route('/duck_profiles', 'Get profiles of all duck agents', 'GET')
        images = Route('/images/<filename>', 'Serve agent images by filename', 'GET')

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
