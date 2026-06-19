# PulseAds Partner Specification

PulseAds authenticates with a bearer token supplied in the Authorization header. The campaigns
endpoint uses cursor pagination: each response includes a next_cursor value that the client passes
on the following request until it is null. PulseAds enforces rate limits and returns HTTP 429 with a
Retry-After header when the caller is too aggressive. Spend is reported in integer cents and must be
divided by one hundred to obtain a currency amount.
