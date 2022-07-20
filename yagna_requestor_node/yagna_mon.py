import os
import json
import time
import quart
import subprocess
import requests

app = quart.Quart(__name__)

yagna_initialized = False
payment_initialized = False

yagna_app_key = os.getenv("YAGNA_APPKEY") or "q-24538-4939"


def check_me():
    endpoint = "http://127.0.0.1:7465/me"
    # data = {"ip": "1.1.2.3"}
    headers = {"Authorization": f"Bearer {yagna_app_key}"}

    identity = requests.get(endpoint, headers=headers).json()
    return identity


def init_sender():
    command = f"yagna payment init --sender"
    print(f"Executing command {command}")
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    if err:
        raise Exception(err)
    return True


def check_payments():
    command = f"yagna payment status --json"
    print(f"Executing command {command}")
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    payments = json.loads(out)
    print(payments)
    return payments


@app.route('/')
async def index():
    identity_info = check_me() if yagna_initialized else {}
    payment_details = check_payments() if payment_initialized else {}

    info = {
        "yagna_initialized": yagna_initialized,
        "payment_initialized": payment_initialized,
        "payment_details": payment_details,
        "identity_info": identity_info
    }
    return quart.jsonify(info)


@app.route('/payment_init')
async def payment_init():
    try:
        init_sender()
    except Exception as ex1:
        return quart.jsonify({"result": str(ex1)})
    return quart.jsonify({"result": "success"})


def run() -> None:
    app.run(host="0.0.0.0", port=3333, use_reloader=False)


def check_for_yagna_startup(max_tries: int):
    for tries in range(0, max_tries):
        try:
            time.sleep(1.0)
            print(f"Calling yagna identity... (try no: {tries + 1})")
            check_me()
            return True
        except Exception as ex:
            print(ex)
    return False


def initialize_payments(max_tries: int):
    for tries in range(0, max_tries):
        try:
            time.sleep(1.0)
            print(f"Initializing payments... (try no: {tries + 1})")
            init_sender()
            return True
            break
        except Exception as ex:
            print(ex)
    return False


if __name__ == '__main__':
    yagna_initialized = check_for_yagna_startup(10)
    if yagna_initialized:
        payment_initialized = initialize_payments(5)

    run()
