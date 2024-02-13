from os import environ
from datetime import datetime, timedelta
import sched
import time
import json
import base64

import requests
import pytz


DEFAULT_SLEEP_TIME = 10
MAX_SLEEP_TIME = 6 * 60 * 60
LOCAL_ACCESS_TOKEN_EXPIRY_SLACK = 60  # Expires tokens X seconds earlier to prevent edge case of in-flight token expiry.
LOCAL_ACCESS_TOKEN_FILE = "data/birddesk-access-token.json"

# Settings. Read only once on startup.
BOOK_DAYS_AHEAD = int(
    environ.get("BOOK_DAYS_AHEAD") or 1
)  # "Target" day ahead, NOT a RANGE of "0 to target"
LOCAL_TIMEZONE = environ.get("LOCAL_TIMEZONE")
REQUEST_USER_AGENT = environ.get("REQUEST_USER_AGENT")
DESKBIRD_WORKING_HOURS_STARTING_HOUR = int(
    environ.get("DESKBIRD_WORKING_HOURS_STARTING_HOUR")
)
DESKBIRD_WORKING_HOURS_CLOSING_HOUR = int(
    environ.get("DESKBIRD_WORKING_HOURS_CLOSING_HOUR")
)
DESKBIRD_RESOURCE_ID = environ.get("DESKBIRD_RESOURCE_ID")
DESKBIRD_WORKSPACE_ID = environ.get("DESKBIRD_WORKSPACE_ID")
DESKBIRD_USER_ID = environ.get("DESKBIRD_USER_ID")
DESKBIRD_ZONE_ITEM_IDS_ON_MONDAYS = (
    environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_MONDAYS") or ""
)
DESKBIRD_ZONE_ITEM_IDS_ON_TUESDAYS = (
    environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_TUESDAYS") or ""
)
DESKBIRD_ZONE_ITEM_IDS_ON_WEDNESDAYS = (
    environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_WEDNESDAYS") or ""
)
DESKBIRD_ZONE_ITEM_IDS_ON_THURSDAYS = (
    environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_THURSDAYS") or ""
)
DESKBIRD_ZONE_ITEM_IDS_ON_FRIDAYS = (
    environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_FRIDAYS") or ""
)
DESKBIRD_ZONE_ITEM_IDS_ON_SATURDAYS = (
    environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_SATURDAYS") or ""
)
DESKBIRD_ZONE_ITEM_IDS_ON_SUNDAYS = (
    environ.get("DESKBIRD_ZONE_ITEM_IDS_ON_SUNDAYS") or ""
)
DESKBIRD_GOOGLE_AUTH_KEY = environ.get("DESKBIRD_GOOGLE_AUTH_KEY")
DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN = environ.get("DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN")

# Global event scheduler, since we're idle about 99% of the time anyway.
scheduler = sched.scheduler(timefunc=time.time, delayfunc=time.sleep)


def run() -> None:
    """Schedules all tasks required to run the app."""
    scheduler.enterabs(
        time=utc_now_timestamp(),
        priority=1,
        action=run_on_startup,
    )

    # Initial booking attempt for target day on startup. Also starts event queue chain for midnight events.
    scheduler.enterabs(
        time=utc_now_timestamp(),
        priority=2,
        action=run_after_midnight,
    )

    while True:
        print("[run] Running scheduler")
        scheduler.run(blocking=False)

        if not scheduler.queue:
            raise RuntimeError(
                "Scheduler events depleted! Infinite event loop (re)scheduling failed?"
            )

        # Status update. For logging and debugging.
        local_timezone = pytz.timezone(LOCAL_TIMEZONE)
        sleep_time = None

        for queued_event in scheduler.queue:
            seconds_until_event = int(queued_event.time - utc_now_timestamp())

            # Sleep until *just* before the next event.
            if sleep_time is None or seconds_until_event < sleep_time:
                sleep_time = seconds_until_event - DEFAULT_SLEEP_TIME

            local_event_time = datetime.fromtimestamp(queued_event.time).astimezone(
                local_timezone
            )
            print(
                f"[run] Upcoming event: {queued_event.action} @ {local_event_time} ({seconds_until_event} seconds)"
            )

        # Keep sleep within some boundaries.
        sleep_time = 1 if sleep_time < 0 else sleep_time
        sleep_time = MAX_SLEEP_TIME if sleep_time > MAX_SLEEP_TIME else sleep_time

        print(f"[run] Sleeping for {sleep_time} second(s)...")
        time.sleep(sleep_time)


def run_after_midnight():
    """Should be called once a day, just after (local) midnight."""
    print("[run_after_midnight] Running midnight job")
    book_target_zone_items()

    # (Re)schedule the self for upcoming midnight. Also works around local DST changes nicely (23/24/25 hours days).
    schedule_next_midnight_event()


def schedule_next_midnight_event():
    """Returns a handle to the event scheduled."""
    local_timezone = pytz.timezone(LOCAL_TIMEZONE)
    local_now = datetime.now().astimezone(local_timezone)
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Required for DST transitions. Not pretty, but it works.
    naive_local_tomorrow_midnight = datetime.combine(
        date=local_midnight.date() + timedelta(days=1), time=local_midnight.time()
    )
    local_tomorrow_midnight = local_timezone.localize(naive_local_tomorrow_midnight)

    utc_next_midnight = local_tomorrow_midnight.astimezone(pytz.utc)
    utc_next_midnight_timestamp = time.mktime(utc_next_midnight.timetuple())

    print(
        f"[schedule_next_midnight_event] Rescheduling self for {local_tomorrow_midnight} ({utc_next_midnight} / {utc_next_midnight_timestamp})"
    )
    scheduler.enterabs(
        time=utc_next_midnight_timestamp
        + 5,  # A little bit of slack... preventing desync
        priority=1,
        action=run_after_midnight,
    )
    # Refresh access token just a bit before that.
    scheduler.enterabs(
        time=utc_next_midnight_timestamp - 5,
        priority=1,
        action=get_access_token,
    )


def utc_now_timestamp() -> float:
    utc_datetime = datetime.now(pytz.utc)
    return time.mktime(utc_datetime.timetuple())


def get_access_token() -> str:
    """Refreshes and returns an access token locally (or if it is expired). Cached locally on file system."""
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

        print("[sync_access_token] Local access token still OK")
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
        print(f"[sync_access_token] Failed to get new access token: {response.text}")
        raise RuntimeError(f"Unable to refresh access token")

    access_token = response.json()["access_token"]

    f = open(LOCAL_ACCESS_TOKEN_FILE, "w")
    f.write(access_token)

    return access_token


def book_target_zone_items() -> None:
    """Books whatever zone items are configured for the given target date (targeted by days ahead)."""
    local_timezone = pytz.timezone(LOCAL_TIMEZONE)
    local_now = datetime.now().astimezone(local_timezone)
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Required for DST transitions. Not pretty, but it works.
    naive_local_tomorrow_midnight = datetime.combine(
        date=local_midnight.date() + timedelta(days=BOOK_DAYS_AHEAD),
        time=local_midnight.time(),
    )
    local_target_midnight = local_timezone.localize(naive_local_tomorrow_midnight)
    local_target_day_name = local_target_midnight.strftime("%A")

    print(
        f"[book_zone_items] Booking {BOOK_DAYS_AHEAD} day(s) ahead ({local_target_day_name}, {local_target_midnight})"
    )

    day_of_week_zone_items_to_book = {
        1: DESKBIRD_ZONE_ITEM_IDS_ON_MONDAYS,
        2: DESKBIRD_ZONE_ITEM_IDS_ON_TUESDAYS,
        3: DESKBIRD_ZONE_ITEM_IDS_ON_WEDNESDAYS,
        4: DESKBIRD_ZONE_ITEM_IDS_ON_THURSDAYS,
        5: DESKBIRD_ZONE_ITEM_IDS_ON_FRIDAYS,
        6: DESKBIRD_ZONE_ITEM_IDS_ON_SATURDAYS,
        7: DESKBIRD_ZONE_ITEM_IDS_ON_SUNDAYS,
    }[local_target_midnight.isoweekday()]

    print(
        f"[book_zone_items] Zone item IDs configured for {local_target_day_name}: {day_of_week_zone_items_to_book}"
    )

    if not day_of_week_zone_items_to_book:
        return

    zone_item_ids = day_of_week_zone_items_to_book.split(",")

    local_booking_start = local_target_midnight + timedelta(
        hours=DESKBIRD_WORKING_HOURS_STARTING_HOUR
    )
    local_booking_start = local_timezone.normalize(local_booking_start)

    local_booking_end_local = local_target_midnight + timedelta(
        hours=DESKBIRD_WORKING_HOURS_CLOSING_HOUR
    )
    local_booking_end_local = local_timezone.normalize(local_booking_end_local)

    bearer_token = get_access_token()

    for current_zone_item_id in zone_item_ids:
        current_zone_item_id = current_zone_item_id.strip()
        utc_booking_start_seconds = time.mktime(
            local_booking_start.astimezone(pytz.utc).timetuple()
        )
        utc_booking_end_seconds = time.mktime(
            local_booking_end_local.astimezone(pytz.utc).timetuple()
        )
        utc_booking_start_seconds = int(utc_booking_start_seconds * 1000)
        utc_booking_end_seconds = int(utc_booking_end_seconds * 1000)

        print(
            f"[book_zone_items] Trying to book zone item #{current_zone_item_id} for {local_booking_start} ({utc_booking_start_seconds}) - {local_booking_end_local} ({utc_booking_end_seconds})"
        )
        response = requests.post(
            url="https://app.deskbird.com/api/v1.1/multipleDayBooking",
            headers={
                "User-Agent": REQUEST_USER_AGENT,
                "Authorization": f"Bearer {bearer_token}",
            },
            json={
                "bookings": [
                    {
                        "bookingStartTime": utc_booking_start_seconds,
                        "bookingEndTime": utc_booking_end_seconds,
                        "internal": True,
                        "isAnonymous": False,
                        "isDayPass": False,
                        "resourceId": DESKBIRD_RESOURCE_ID,
                        "zoneItemId": int(current_zone_item_id),
                        "workspaceId": DESKBIRD_WORKSPACE_ID,
                        "userId": DESKBIRD_USER_ID,
                    }
                ]
            },
        )
        print(
            f"[book_zone_items] Request for booking zone item #{current_zone_item_id}: {response.request.method} {response.url}"
        )
        print(
            f"[book_zone_items] Response for booking zone item #{current_zone_item_id}: HTTP {response.status_code}"
        )

        if response.status_code != 200:
            print(
                f"[book_zone_items] FAILED to book zone item #{current_zone_item_id}: {response.text}"
            )


def list_workspace_zone_items() -> None:
    """Lists all zone items available in the workspace. May help you in configuring DESKBIRD_ZONE_ITEM_IDS_ON_*."""
    bearer_token = get_access_token()
    response = requests.get(
        url=f"https://app.deskbird.com/api/v1.2/internalWorkspaces/{DESKBIRD_WORKSPACE_ID}/zones?internal",
        headers={
            "User-Agent": REQUEST_USER_AGENT,
            "Authorization": f"Bearer {bearer_token}",
        },
    )
    print(
        f"[list_workspace_zone_items] Request for workspace #{DESKBIRD_WORKSPACE_ID} zones: {response.request.method} {response.url}"
    )
    print(
        f"[list_workspace_zone_items] Response for workspace #{DESKBIRD_WORKSPACE_ID} zones: HTTP {response.status_code}"
    )

    if response.status_code != 200:
        raise RuntimeError("[list_workspace_zone_items] Failed")

    print("[list_workspace_zone_items] Listing zone items available for you:")
    for current_result in response.json()["results"]:
        current_resource_type = current_result["availability"]["resourceType"]

        for current_zone_item in current_result["availability"]["zoneItems"]:
            print(
                f"[list_workspace_zone_items] Zone item #{current_zone_item['id']} -> ({current_resource_type} : {current_zone_item['name']})"
            )


def run_on_startup() -> None:
    print(f"[Config] Local timezone:                       {LOCAL_TIMEZONE}")
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
    print(
        f"[Config] Deskbird zone IDs on SATURDAYs:       {DESKBIRD_ZONE_ITEM_IDS_ON_SATURDAYS.split(',')}"
    )
    print(
        f"[Config] Deskbird zone IDs on SUNDAYs:         {DESKBIRD_ZONE_ITEM_IDS_ON_SUNDAYS.split(',')}"
    )
    # Initial refresh. Also makes sure the mechanism/account is checked on boot.
    get_access_token()

    # One-time listing. You may or may not be interested in its output.
    list_workspace_zone_items()
