from os import environ
from time import sleep
from datetime import date, datetime
from typing import List

import requests
import pytz


def book_zone_items(target_date: date, zone_item_ids: List[int]):

    for current_zone_item_id in zone_item_ids:
        print(zone_item_ids)

        # response = requests.post(
        #     url="https://app.deskbird.com/api/v1.1/multipleDayBooking",
        #     headers={
        #         "User-Agent": environ.get("REQUEST_USER_AGENT"),
        #         # "Authorization": "Bearer TEST",  # @TODO
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
    print(f"[Config] Local timezone: {local_tz}")

    deskbird_resource_id = environ.get("DESKBIRD_RESOURCE_ID")
    deskbird_workspace_id = environ.get("DESKBIRD_WORKSPACE_ID")
    deskbird_user_id = environ.get("DESKBIRD_USER_ID")
    print(f"[Config] Deskbird resource ID: {deskbird_resource_id}")
    print(f"[Config] Deskbird workspace ID: {deskbird_workspace_id}")
    print(f"[Config] Deskbird user ID: {deskbird_user_id}")

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
    print(f"[Config] Deskbird zone IDs on MONDAYs: {deskbird_zone_ids_on_mondays}")
    print(f"[Config] Deskbird zone IDs on TUESDAYs: {deskbird_zone_ids_on_tuesdays}")
    print(
        f"[Config] Deskbird zone IDs on WEDNESDAYs: {deskbird_zone_ids_on_wednesdays}"
    )
    print(f"[Config] Deskbird zone IDs on THURSDAYs: {deskbird_zone_ids_on_thursdays}")
    print(f"[Config] Deskbird zone IDs on FRIDAYs: {deskbird_zone_ids_on_fridays}")

    while True:
        now = datetime.now(local_tz)

        print(f"Running booker... {now}")
        sleep(5)
