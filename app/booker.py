from os import environ
from datetime import date, datetime
from typing import List
import sched
import time

import requests
import pytz


scheduler = sched.scheduler(time.time, time.sleep)


def daily_run(google_auth_key: str, google_auth_refresh_token: str, user_agent: str):
    print("Daily run...")
    bearer_token = get_bearer_token(
        google_auth_key=google_auth_key,
        google_auth_refresh_token=google_auth_refresh_token,
        user_agent=user_agent,
    )


def get_bearer_token(
    google_auth_key: str, google_auth_refresh_token: str, user_agent: str
):
    print(f"Sending Request for bearer token...")
    response = requests.post(
        url=f"https://securetoken.googleapis.com/v1/token?key={google_auth_key}",
        headers={
            "User-Agent": user_agent,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": google_auth_refresh_token,
        },
    )
    print(f"Response for bearer token: HTTP {response.status_code}")

    if response.status_code != 200:
        print(f"Response content: {response.text}")
        raise RuntimeError(f"Failed to get bearer token!")

    return response.json()["access_token"]


def book_zone_items(
    target_date: date, zone_item_ids: List[int], bearer_token: str, user_agent: str
):

    for current_zone_item_id in zone_item_ids:
        print(zone_item_ids)

        # response = requests.post(
        #     url="https://app.deskbird.com/api/v1.1/multipleDayBooking",
        #     headers={
        #         "User-Agent": user_agent,
        #         "Authorization": f"Bearer {bearer_token}",
        #     },
        #     json={
        #         "bookings": [
        #             {
        #                 "bookingStartTime": 1706853600000,
        #                 "bookingEndTime": 1706893200000,
        #                 "internal": True,
        #                 "isAnonymous": False,
        #                 "isDayPass": False,
        #                 "resourceId": environ.get("DESKBIRD_RESOURCE_ID"),
        #                 "zoneItemId": current_zone_item_id,
        #                 "workspaceId": environ.get("DESKBIRD_WORKSPACE_ID"),
        #                 "userId": environ.get("DESKBIRD_USER_ID"),
        #             }
        #         ]
        #     },
        # )
        # print(f"Request for zone item {current_zone_item_id}: {response.url}")
        # print(f"Response for zone item {current_zone_item_id}: HTTP {response.status_code} - {response.raw}")


def run():
    local_tz = pytz.timezone(environ.get("DESKBIRD_TIMEZONE"))
    user_agent = environ.get("REQUEST_USER_AGENT")
    print(f"[Config] Local timezone:                       {local_tz}")
    print(f"[Config] User-Agent for requests:              {user_agent}")

    deskbird_resource_id = environ.get("DESKBIRD_RESOURCE_ID")
    deskbird_workspace_id = environ.get("DESKBIRD_WORKSPACE_ID")
    deskbird_user_id = environ.get("DESKBIRD_USER_ID")
    print(f"[Config] Deskbird resource ID:                 {deskbird_resource_id}")
    print(f"[Config] Deskbird workspace ID:                {deskbird_workspace_id}")
    print(f"[Config] Deskbird user ID:                     {deskbird_user_id}")

    deskbird_google_auth_refresh_token = environ.get(
        "DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN"
    )
    deskbird_google_auth_key = environ.get("DESKBIRD_GOOGLE_AUTH_KEY")
    print(
        f"[Config] Deskbird Google Auth refresh token:   {deskbird_google_auth_refresh_token[0]}...{deskbird_google_auth_refresh_token[-1]} ({len(deskbird_google_auth_refresh_token)} chars)"
    )
    print(
        f"[Config] Deskbird Google Auth key:             {deskbird_google_auth_key[0]}...{deskbird_google_auth_key[-1]} ({len(deskbird_google_auth_key)} chars)"
    )

    deskbird_zone_ids_on_mondays = environ.get(
        "DESKBIRD_ZONE_ITEM_IDS_ON_MONDAYS"
    ).split(",")
    deskbird_zone_ids_on_tuesdays = environ.get(
        "DESKBIRD_ZONE_ITEM_IDS_ON_TUESDAYS"
    ).split(",")
    deskbird_zone_ids_on_wednesdays = environ.get(
        "DESKBIRD_ZONE_ITEM_IDS_ON_WEDNESDAYS"
    ).split(",")
    deskbird_zone_ids_on_thursdays = environ.get(
        "DESKBIRD_ZONE_ITEM_IDS_ON_THURSDAYS"
    ).split(",")
    deskbird_zone_ids_on_fridays = environ.get(
        "DESKBIRD_ZONE_ITEM_IDS_ON_FRIDAYS"
    ).split(",")
    print(
        f"[Config] Deskbird zone IDs on MONDAYs:         {deskbird_zone_ids_on_mondays}"
    )
    print(
        f"[Config] Deskbird zone IDs on TUESDAYs:        {deskbird_zone_ids_on_tuesdays}"
    )
    print(
        f"[Config] Deskbird zone IDs on WEDNESDAYs:      {deskbird_zone_ids_on_wednesdays}"
    )
    print(
        f"[Config] Deskbird zone IDs on THURSDAYs:       {deskbird_zone_ids_on_thursdays}"
    )
    print(
        f"[Config] Deskbird zone IDs on FRIDAYs:         {deskbird_zone_ids_on_fridays}"
    )

    utc_now_timestamp = time.mktime(datetime.now(pytz.utc).timetuple())
    # scheduler.enterabs(
    #     time=utc_now_timestamp + 2,
    #     priority=1,
    #     action=daily_run,
    #     kwargs=dict(
    #         # Kwargs passed to action: daily_run(...)
    #         user_agent=user_agent,
    #         google_auth_key=deskbird_google_auth_key,
    #         google_auth_refresh_token=deskbird_google_auth_refresh_token,
    #     )
    # )

    while True:
        print(f"Running booker iteration... until next event")
        scheduler.run(blocking=True)
        time.sleep(1)
