import os
from os import environ
from datetime import date, datetime, timedelta
from typing import List
import sched
import time
import json
import base64

import requests
import pytz


# Settings. Read only once on startup.
LOCAL_ACCESS_TOKEN_EXPIRY_SLACK = (
    60  # Expires tokens X seconds earlier to prevent in-flight token expiry.
)
LOCAL_ACCESS_TOKEN_FILE = "data/birddesk-access-token.json"
REQUEST_USER_AGENT = environ.get("REQUEST_USER_AGENT")
DESKBIRD_TIMEZONE = environ.get("DESKBIRD_TIMEZONE")
DESKBIRD_RESOURCE_ID = environ.get("DESKBIRD_RESOURCE_ID")
DESKBIRD_WORKSPACE_ID = environ.get("DESKBIRD_WORKSPACE_ID")
DESKBIRD_USER_ID = environ.get("DESKBIRD_USER_ID")
DESKBIRD_ZONE_ITEM_IDS_ON_MONDAYS = environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_MONDAYS")
DESKBIRD_ZONE_ITEM_IDS_ON_TUESDAYS = environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_TUESDAYS")
DESKBIRD_ZONE_ITEM_IDS_ON_WEDNESDAYS = environ.get(
    "DESKBIRD_ZONE_ITEM_IDS_ON_WEDNESDAYS"
)
DESKBIRD_ZONE_ITEM_IDS_ON_THURSDAYS = environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_THURSDAYS")
DESKBIRD_ZONE_ITEM_IDS_ON_FRIDAYS = environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_FRIDAYS")
DESKBIRD_GOOGLE_AUTH_KEY = environ.get("DESKBIRD_GOOGLE_AUTH_KEY")
DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN = environ.get("DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN")


# Global event scheduler, since we're idle about 99% of the time anyway.
scheduler = sched.scheduler(time.time, time.sleep)


def daily_run():
    print("Daily run...")
    # bearer_token = obtain_bearer_token()


def sync_access_token():
    """Makes sure there is an access token stored locally. Refreshes one when non exists or it's expired."""
    try:
        print("[sync_access_token] Checking local access token...")
        f = open(LOCAL_ACCESS_TOKEN_FILE, "r")
        access_token = f.read()

        print("[sync_access_token] Inspecting local access token...")
        access_token_parts = access_token.split(".")
        base64_token_data = access_token_parts[1]
        token_data = base64.b64decode(
            base64_token_data + "=="
        )  # https://stackoverflow.com/a/49459036
        token_claims = json.loads(token_data)
        token_expires_at = token_claims["exp"]

        print(
            f"[sync_access_token] Checking local access token expiry... (slack: {LOCAL_ACCESS_TOKEN_EXPIRY_SLACK}s)"
        )
        if utc_now_timestamp() + LOCAL_ACCESS_TOKEN_EXPIRY_SLACK > token_expires_at:
            raise RuntimeError("[sync_access_token] Expired access token")

        print(
            f"[sync_access_token] Found valid access token for: {token_claims['name']} ({token_claims['email']})"
        )

        return access_token
    except Exception as e:
        print(f"[sync_access_token] Error: {e}")
        # Obtain new one below.
        pass

    print(f"[sync_access_token] Sending Request for new access token...")
    response = requests.post(
        url=f"https://securetoken.googleapis.com/v1/token?key={DESKBIRD_GOOGLE_AUTH_KEY}",
        headers={
            "User-Agent": REQUEST_USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN,
        },
    )
    print(
        f"[sync_access_token] Response for new access token: HTTP {response.status_code}"
    )

    if response.status_code != 200:
        print(f"[sync_access_token] Response content: {response.text}")
        raise RuntimeError(f"[sync_access_token] Failed to get new access token!")

    access_token = response.json()["access_token"]

    f = open(LOCAL_ACCESS_TOKEN_FILE, "w")
    f.write(access_token)


def get_access_token() -> str:
    """Obtains a new access token by using the given refresh token."""
    f = open(LOCAL_ACCESS_TOKEN_FILE, "r")
    return f.read()


def book_zone_items(target_date: date, local_tz, zone_item_ids: List[int]):
    bearer_token = get_access_token()

    midnight = datetime.combine(date=target_date, time=datetime.time())
    local_midnight = local_tz.localize(midnight)
    booking_start_local = local_tz.normalize(local_midnight + timedelta(hours=7))
    booking_end_local = local_tz.normalize(local_midnight + timedelta(hours=18))

    for current_zone_item_id in zone_item_ids:
        booking_start_utc_seconds = time.mktime(
            booking_start_local.astimezone(pytz.utc).timetuple()
        )
        booking_end_utc_seconds = time.mktime(
            booking_end_local.astimezone(pytz.utc).timetuple()
        )

        print(
            f"Trying to book zone item {current_zone_item_id} for {booking_start_local} - {booking_end_local}"
        )
        # response = requests.post(
        #     url="https://app.deskbird.com/api/v1.1/multipleDayBooking",
        #     headers={
        #         "User-Agent": REQUEST_USER_AGENT,
        #         "Authorization": f"Bearer {bearer_token}",
        #     },
        #     json={
        #         "bookings": [
        #             {
        #                 "bookingStartTime": booking_start_utc_seconds,
        #                 "bookingEndTime": booking_end_utc_seconds,
        #                 "internal": True,
        #                 "isAnonymous": False,
        #                 "isDayPass": False,
        #                 "resourceId": DESKBIRD_RESOURCE_ID,
        #                 "zoneItemId": current_zone_item_id,
        #                 "workspaceId": DESKBIRD_WORKSPACE_ID,
        #                 "userId": DESKBIRD_USER_ID,
        #             }
        #         ]
        #     },
        # )
        # print(f"Request for zone item {current_zone_item_id}: {response.url}")
        # print(f"Response for zone item {current_zone_item_id}: HTTP {response.status_code} - {response.raw}")


def utc_now_timestamp():
    utc_datetime = datetime.now(pytz.utc)
    return time.mktime(utc_datetime.timetuple())


def startup_run():
    print(f"[Config] Local timezone:                       {DESKBIRD_TIMEZONE}")
    print(f"[Config] User-Agent for requests:              {REQUEST_USER_AGENT}")
    print(f"[Config] Deskbird resource ID:                 {DESKBIRD_RESOURCE_ID}")
    print(f"[Config] Deskbird workspace ID:                {DESKBIRD_WORKSPACE_ID}")
    print(f"[Config] Deskbird user ID:                     {DESKBIRD_USER_ID}")
    print(
        f"[Config] Deskbird Google Auth refresh token:   {DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN[0]}...{DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN[-1]} ({len(DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN)} chars)"
    )
    print(
        f"[Config] Deskbird Google Auth key:             {DESKBIRD_GOOGLE_AUTH_KEY[0]}...{DESKBIRD_GOOGLE_AUTH_KEY[-1]} ({len(DESKBIRD_GOOGLE_AUTH_KEY)} chars)"
    )
    print(
        f"[Config] Deskbird zone IDs on MONDAYs:         {DESKBIRD_ZONE_ITEM_IDS_ON_MONDAYS.split(',')}"
    )
    print(
        f"[Config] Deskbird zone IDs on TUESDAYs:        {DESKBIRD_ZONE_ITEM_IDS_ON_TUESDAYS.split(',')}"
    )
    print(
        f"[Config] Deskbird zone IDs on WEDNESDAYs:      {DESKBIRD_ZONE_ITEM_IDS_ON_WEDNESDAYS.split(',')}"
    )
    print(
        f"[Config] Deskbird zone IDs on THURSDAYs:       {DESKBIRD_ZONE_ITEM_IDS_ON_THURSDAYS.split(',')}"
    )
    print(
        f"[Config] Deskbird zone IDs on FRIDAYs:         {DESKBIRD_ZONE_ITEM_IDS_ON_FRIDAYS.split(',')}"
    )

    sync_access_token()


def run():
    # Once.
    scheduler.enterabs(
        time=utc_now_timestamp() + 1,
        priority=1,
        action=startup_run,
    )

    # scheduler.enterabs(
    #     time=utc_now_timestamp() + 1,
    #     priority=1,
    #     action=daily_run,
    #     kwargs=dict(
    #         # Kwargs passed to daily_run()
    #     )
    # )

    while True:
        print(f"Running booker iteration... until next event")
        print(f"Event queue: {scheduler.queue}")
        scheduler.run(blocking=True)
        time.sleep(1)
