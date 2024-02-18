from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import quote_plus, urlparse, unquote, urlencode, unquote_plus
from urllib.request import Request, urlopen
from ssl import wrap_socket
from webbrowser import open as webbrowser_open
from base64 import b64encode
from time import time
from json import loads as json_loads, dumps as json_dumps
from utils import Token
from ebaysdk.trading import Connection as Trading
from ebaycreds import *

Authorization = b64encode(f"{clientid}:{clientsecret}".encode()).decode()
Authorization = f"Basic {Authorization}"

redirect_url = "Marc_Manjaro-MarcManj-TestAp-zsftkom"

scope = "https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly https://api.ebay.com/oauth/api_scope/sell.finances https://api.ebay.com/oauth/api_scope/sell.payment.dispute https://api.ebay.com/oauth/api_scope/commerce.identity.readonly https://api.ebay.com/oauth/api_scope/sell.reputation https://api.ebay.com/oauth/api_scope/sell.reputation.readonly https://api.ebay.com/oauth/api_scope/commerce.notification.subscription https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly https://api.ebay.com/oauth/api_scope/sell.stores https://api.ebay.com/oauth/api_scope/sell.stores.readonly"
# for x in scope.split(" "):
#     print(x)

def get(url):
    return urlopen(Request(url, method="GET", headers={'User-Agent': 'Mozilla/5.0'})).read()

class Api:
    def __init__(self, token=None, code=None, debug=False) -> None:
        self.code = code
        self.debug = debug
        self.token: Token = token
        if self.token is not None:
            self.trading = Trading(debug=True, config_file=None, appid=clientid, certid=clientsecret, devid=devid, token=self.token.value, warnings=True, timeout=20)


    def post(self, url, headers=dict(), data=dict()):
        req = Request(url, data=urlencode(data).encode(), method="POST")
        for k, v in headers.items():
            req.add_header(k, v)
        if self.debug:
            print(req.get_method())
            print(req.get_full_url())
            print(headers)
            print(req.data)
        return urlopen(req)

    def post_auth(self, url, headers=dict(), data=dict()):
        headers["Authorization"] = f"Bearer {self.get_token()}"
        return self.post(url, headers=headers, data=data)

    def post_auth_json(
        self,
        url,
        headers={"Content-Type": "application/json", "Content-Language": "de-DE"},
        data=dict(),
    ):
        return self.post_auth(url, headers, data)

    def get_token(self):
        def post_auth_code():
            # https://api.ebay.com/identity/v1/oauth2/token
            return self.post(
                "https://api.ebay.com/identity/v1/oauth2/token",
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": Authorization,
                },
                data={
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_url,
                    "code": self.code,
                },
            )

        if self.token is None or self.token.expires <= int(time()) + 10:
            r = json_loads(post_auth_code().read().decode())
            self.token = Token(r["access_token"], int(time()) + r["expires_in"])
        self.trading = Trading(debug=self.debug, config_file=None, appid=clientid, certid=clientsecret, devid=devid, token=self.token.value, warnings=True, timeout=20)
        return self.token

    def get(self, url, headers=dict(), params=dict()):
        req = Request(f"{url}?{urlencode(params)}", method="GET")
        for k, v in headers.items():
            req.add_header(k, v)
        if self.debug:
            print(req.get_method())
            print(req.get_full_url())
            print(headers)
            print(req.data)
        return urlopen(req)

    def get_auth(self, url, headers=dict(), params=dict()):
        headers["Authorization"] = f"Bearer {self.get_token()}"
        return self.get(url, headers=headers, params=params)

    def get_auth_json(self, url, headers=dict(), params=dict()):
        return json_loads(
            self.get_auth(url, headers=headers, params=params).read().decode()
        )

    def get_inventory_item(self, limit: str = 25, offset: str = 0):
        return self.get_auth_json(
            "https://api.ebay.com/sell/inventory/v1/inventory_item",
            params={"limit": limit, "offset": offset},
        )

    def get_user(self):
        return self.get_auth_json("https://apiz.ebay.com/commerce/identity/v1/user/")
    
    def trading_exec(self, verb, data = None):
        self.get_token()
        return self.trading.execute(verb, data)


# api.post_auth_json("https://api.ebay.com/sell/inventory/v1/offer")

# https://api.ebay.com/sell/inventory/v1/inventory_item
# api = Api()
# api.get("https://google.com", headers={"Content-Type": "json"}, params={"q": "lol"})


def oauth_create_server(api: Api, out=None):
    keep_running = True

    class Serv(BaseHTTPRequestHandler):
        def do_POST(self):
            print("POST", self.path)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            message = "Hello, World! Here is a POST response"
            self.wfile.write(bytes(message, "utf8"))

        def do_GET(self):
            parsed = urlparse(self.path)
            response_code = 200
            if parsed.path == "/accepted":
                params = dict(x.split("=") for x in unquote_plus(parsed.query).split("&"))
                if "code" not in params:
                    print(parsed.query)
                    print(unquote_plus(parsed.query))
                    raise Exception("code not found in params")
                
                api.code = params["code"]
                print(api.code)
                nonlocal keep_running
                keep_running = False
                message = "accepted"
            elif parsed.path == "/declined":
                print(parsed)
                message = "declined"
            elif parsed.path == "/privacy":
                print(parsed)
                message = "u good bruh"
            else:
                message = "no"
                response_code = 400
            self.send_response(response_code)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(message, "utf8"))

    with HTTPServer(("localhost", 4443), Serv) as httpd:
        httpd.socket = wrap_socket(
            httpd.socket,
            keyfile=Path(__file__).parent / "server.key",
            certfile=Path(__file__).parent / "server.cert",
            server_side=True,
        )
        if out is not None:
            out.put(httpd)
        while keep_running:
            httpd.handle_request()


def oauth_send_browser():
    url = "https://auth.ebay.com/oauth2/authorize"
    params = urlencode(
        {
            "response_type": "code",
            "client_id": clientid,
            "redirect_uri": redirect_url,
            "scope": scope,
            "locale": "de-DE",
            "state": "test123",
        }
    )
    webbrowser_open(f"{url}?{params}")


if __name__ == "__main__":
    # def dump(api, full=False):

    #     print("\n")

    #     if api.warnings():
    #         print("Warnings" + api.warnings())

    #     if api.response.content:
    #         print("Call Success: %s in length" % len(api.response.content))

    #     print("Response code: %s" % api.response_code())
    #     print("Response DOM1: %s" % api.response.dom())  # deprecated
    #     print("Response ETREE: %s" % api.response.dom())

    #     if full:
    #         print(api.response.content)
    #         print(api.response.json())
    #         print("Response Reply: %s" % api.response.reply)
    #     else:
    #         dictstr = "%s" % api.response.dict()
    #         print("Response dictionary: %s..." % dictstr[:150])
    #         replystr = "%s" % api.response.reply
    #         print("Response Reply: %s" % replystr[:150])
    pass