import datetime
import json
import sqlite3
import msal
import requests

msal_app = msal.PublicClientApplication(
    "1fbdf10d-d4e5-4716-b990-7ada9610a5d3",
    authority="https://login.microsoftonline.com/consumers",
)


def get_profile_info(token):
    xbl_payload = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": "d={}".format(token) if not token.startswith('d=') else token
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }

    xbl_response = requests.post(url='https://user.auth.xboxlive.com/user/authenticate', json=xbl_payload)
    xbl_response = xbl_response.json()

    xbl_token = xbl_response['Token']
    xui_uhs = xbl_response['DisplayClaims']['xui'][0]['uhs']

    xsts_payload = {
        "Properties": {
            "SandboxId": "RETAIL",
            "UserTokens": [
                xbl_token
            ]
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT"
    }

    xsts_response = requests.post('https://xsts.auth.xboxlive.com/xsts/authorize', json=xsts_payload)
    xsts_response = xsts_response.json()
    xsts_token = xsts_response['Token']

    mc_payload = {
        "identityToken": f"XBL3.0 x={xui_uhs};{xsts_token}"
    }

    mc_response = requests.post('https://api.minecraftservices.com/authentication/login_with_xbox', json=mc_payload)
    mc_response = mc_response.json()

    mc_token = mc_response['access_token']

    # Profile
    profile = requests.get(
        'https://api.minecraftservices.com/minecraft/profile',
        headers={'Authorization': f'Bearer {mc_token}'}
    )
    profile = profile.json()

    return mc_token, profile


# MSAL utils
def start_device_code_flow():
    flow = msal_app.initiate_device_flow(scopes=["XboxLive.signin"])
    if "user_code" not in flow:
        print("Failed to create device flow. Err: " + json.dumps(flow, indent=4))
        raise Exception()
    print(f"To sign in, open {flow['verification_uri']} and enter the code {flow['user_code']}.")
    return flow


def get_token_with_device_code(flow):
    result = msal_app.acquire_token_by_device_flow(flow)
    return result


def obtain_token_with_device_code():
    flow = start_device_code_flow()
    result = get_token_with_device_code(flow)
    return result


def load_auth_info(key):
    info = None
    with sqlite3.connect('.minecraft-auth.db') as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS auth (key TEXT PRIMARY KEY, time TEXT, data TEXT)')
        for row in conn.execute('SELECT * FROM auth WHERE key = ?', (key,)):
            info = row
            break
    return info


def save_auth_info(key, data):
    with sqlite3.connect('.minecraft-auth.db') as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS auth (key TEXT PRIMARY KEY, time TEXT, data TEXT)')
        data = json.dumps(data)
        now = datetime.datetime.now().isoformat()
        conn.execute(
            'INSERT INTO auth (key, time, data) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET time = ?, data = ?',
            (key, now, data, now, data)
        )
        conn.commit()


def authenticate(client, options):
    print("Attempting authentication...")
    print("Loading stored authentication info...")
    key = options["username"]
    authinfo = load_auth_info(key)
    if authinfo is None:
        print("No stored authentication info found. Beginning initial authentication...")
        token = obtain_token_with_device_code()
        print("Authentication granted!")
    else:
        print("Stored authentication info found.")
        authdata = json.loads(authinfo[2])
        time = datetime.datetime.fromisoformat(authinfo[1])
        if time + datetime.timedelta(seconds=authdata['expires_in']) <= datetime.datetime.now():
            print("Authentication token has expired. Attempting a refresh...")
            token = msal_app.acquire_token_by_refresh_token(
                authdata["refresh_token"],
                scopes=["XboxLive.signin"],
            )
        else:
            print("Using stored authentication token.")
            token = authdata
    if "access_token" in token:
        print("Saving authentication information...")
        save_auth_info(key, token)
        print("Fetching access token and profile information...")
        try:
            auth_token, profile = get_profile_info(token["access_token"])
        except Exception as e:
            raise Exception(f"Authentication failed - {e}") from e
    else:
        raise Exception(
            f"Authentication failed: '{token.get('error')}' ({token.get('error_description')}) - "
            f"Correlation ID: {token.get('correlation_id')}"
        )
    print(f"Authentication successful. Authenticated as {profile['name']} ({profile['id']}).")
    session = {
        "accessToken": auth_token,
        "selectedProfile": profile,
        "availableProfile": [profile]
    }
    print(session)
    client.session = session
    client.username = profile["name"]
    client.uuid = profile["id"]
    options["accessToken"] = auth_token
    options["haveCredentials"] = True
    client.emit('session', session)
    conn = options["connect"](client)
    return conn