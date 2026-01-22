# Daily Report Cron Job Setup

## Install the cron job

Run this command to edit your crontab:

```bash
crontab -e
```

Add this line to run the daily report at 3am every day:

```cron
0 3 * * * /Users/deanturpin/jira/bin/daily_report_cron.sh
```

Save and exit (`:wq` in vim, or `Ctrl+X` then `Y` in nano).

## Verify it's installed

```bash
crontab -l
```

You should see your cron job listed.

## Check the logs

The script logs to `/tmp/jira-daily-report.log`:

```bash
tail /tmp/jira-daily-report.log
```

## Test it manually

```bash
/Users/deanturpin/jira/bin/daily_report_cron.sh
```

## Remove the cron job

If you want to disable it later:

```bash
crontab -e
```

Delete the line or comment it out with `#`.

## Notes

- Your laptop needs to be on and awake at 3am for this to run
- If you want to prevent sleep, you can use `caffeinate` or adjust Energy Saver settings
- The virtual environment must exist at `venv/` (already created)
