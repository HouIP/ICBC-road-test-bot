# ICBC Appointment Bot

Robot for checking ICBC road test appointments.

### Usage

Make sure the .env file is properly configured with your ICBC credentials and a [Discord incoming webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) URL.
Run `checker_bot.py` to poll every few minutes: it runs `icbc-appointment.py`, compares the new `appointments.csv` to the snapshot from before that run, and posts to Discord when a **earlier** slot appears (per location). If there was no prior snapshot, it only records a baseline and does not notify. `checker_state.json` stores already-notified slots to reduce duplicate alerts.
Execute the following command to run the bot:
```python
python checker_bot.py
```
## Config

create a .env file in the root directory to store your configuration values, such as ICBC credentials and your Discord webhook URL. `./.env`
```yaml
# .env file
ICBC_LASTNAME="YOUR_LAST_NAME"
ICBC_LICENCENUMBER="YOUR_LICENCE_NUMBER"
ICBC_KEYWORD="KEYWORD"
ICBC_EXPECT_AFTERDATE="2024-07-13"  # YYYY-MM-DD
ICBC_EXPECT_BEFOREDATE="2024-08-31"  # YYYY-MM-DD
ICBC_EXPECT_AFTERTIME="07:00"  # HH:MM
ICBC_EXPECT_BEFORETIME="17:30"  # HH:MM
ICBC_EXAMCLASS=7  # 5/7

DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN"
```

## Usage

It supports any location, by modifying the locations in icbc-appointment.py. For example **Point Grey**:
```python
point_grey = {
    "aPosID": 9,
    "examType": examClass+"-R-1",
    "examDate": expactAfterDate,
    "ignoreReserveTime": "false",
    "prfDaysOfWeek": "[0,1,2,3,4,5,6]",
    "prfPartsOfDay": "[0,1]",
    "lastName": lastName,
    "licenseNumber": licenceNumber
}
```
## Locations
| Location  | posID |
| ------------- | ------------- |
| Richmond claim centre (Elmbridge Way)  | 273  |
| Richmond driver licensing (Lansdowne Centre mall)  | 93  |
| Vancouver driver licensing (Point Grey)  | 9  |
| Vancouver claim centre (Kingsway)  | 275  |
| Burnaby claim centre (Wayburne Drive)  | 274  |
| Surrey driver licensing  | 11  |
| Newton claim centre (68 Avenue)  | 271  |
| Surrey claim centre (152A St.)  | 269  |
| North Vancouver driver licensing  | 8  |

## Contributing
Feel free to contribute.

1. Able to change location
2. Able to choose Day of week
