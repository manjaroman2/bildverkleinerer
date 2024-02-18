# from oauthlib.oauth2 import Client, WebApplicationClient
from requests import get, post, request
from base64 import b64encode
from requests_oauthlib import OAuth2Session

# clientid = "MarcManj-TestApp-SBX-5b4446ab8-1f41fcd0"
# devid = "3b48f270-b45f-4d72-968d-da66d7ce9fcf"
# clientsecret = "SBX-b4446ab8ade8-8e60-4356-a00f-556b"
clientid = "MarcManj-TestApp-PRD-ab44d5824-5eb923d1"
clientsecret="PRD-b44d5824acf4-a10c-4862-b782-672e"

# authtoken = b64encode(f"{clientid}:{clientsecret}".encode())

scope="https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly https://api.ebay.com/oauth/api_scope/sell.finances https://api.ebay.com/oauth/api_scope/sell.payment.dispute https://api.ebay.com/oauth/api_scope/commerce.identity.readonly https://api.ebay.com/oauth/api_scope/sell.reputation https://api.ebay.com/oauth/api_scope/sell.reputation.readonly https://api.ebay.com/oauth/api_scope/commerce.notification.subscription https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly https://api.ebay.com/oauth/api_scope/sell.stores https://api.ebay.com/oauth/api_scope/sell.stores.readonly"
scope=scope.split(' ')
oauth_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
# response = post(
#     url=uri,
#     headers={
#         "Content-Type": "application/x-www-form-urlencoded",
#         "Authorization": f"Basic {authtoken}",
#     },
#     data={
#         "grant_type": "client_credentials",
#         "scope": scope
#     }
# )
# print(response.json())

# https://auth.sandbox.ebay.com/oauth2/authorize?client_id=MarcManj-TestApp-SBX-5b4446ab8-1f41fcd0&response_type=code&redirect_uri=
oauth = OAuth2Session(clientid, redirect_uri="Marc_Manjaro-MarcManj-TestAp-zsftkom", scope=scope)
auth_url, state = oauth.authorization_url("https://auth.ebay.com/oauth2/authorize")
print(auth_url)
r = input(":")
token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=r,
        # Google specific extra parameter used for client
        # authentication
        client_secret=clientsecret)

