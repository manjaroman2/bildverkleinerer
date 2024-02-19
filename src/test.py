from urllib.parse import unquote_plus
a = "state=test123&code=v^1.1%23i^1%23I^3%23f^0%23p^3%23r^1%23t^Ul41XzExOkJFN0U4QkFEQjlGMkI2MzNGNTYxMTc3Q0Y0MTcwMjUwXzBfMSNFXjI2MA%3D%3D&expires_in=299"
print([x.split("=") for x in "state=test123&code=v^1.1%23i^1%23I^3%23f^0%23p^3%23r^1%23t^Ul41XzExOkJFN0U4QkFEQjlGMkI2MzNGNTYxMTc3Q0Y0MTcwMjUwXzBfMSNFXjI2MA%3D%3D&expires_in=299".split("&")])
