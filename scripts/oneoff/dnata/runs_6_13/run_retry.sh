# rows whose earlier hotel is not on sale for 6-10 Nov: the nearest match by name instead
cd /home/user/CPI-Web-Scarping/scripts/oneoff/dnata
R=runs_6_13
CHECKIN=2026-11-06 CHECKOUT=2026-11-10 python3 dnata_packages.py $R/targets_retry.json $R/pkg_retry.json; echo RETRY_DONE
CHECKIN=2026-11-06 CHECKOUT=2026-11-10 NIGHTS=4 SHOTDIR=$R/shots python3 shots.py $R/pkg_retry.json $R/shots_retry.json; echo SHOTS_RETRY_DONE
