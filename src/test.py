from requests_oauthlib import OAuth2Session

clientid, clientsecret = open("ebay-creds.txt", "r").read().splitlines()

scope="https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly https://api.ebay.com/oauth/api_scope/sell.finances https://api.ebay.com/oauth/api_scope/sell.payment.dispute https://api.ebay.com/oauth/api_scope/commerce.identity.readonly https://api.ebay.com/oauth/api_scope/sell.reputation https://api.ebay.com/oauth/api_scope/sell.reputation.readonly https://api.ebay.com/oauth/api_scope/commerce.notification.subscription https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly https://api.ebay.com/oauth/api_scope/sell.stores https://api.ebay.com/oauth/api_scope/sell.stores.readonly"
scope=scope.split(' ')
oauth_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
oauth = OAuth2Session(clientid, redirect_uri="Marc_Manjaro-MarcManj-TestAp-zsftkom", scope=scope)
auth_url, state = oauth.authorization_url("https://auth.ebay.com/oauth2/authorize")
print(auth_url)
r = input(":")
token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=r,
        client_secret=clientsecret)

