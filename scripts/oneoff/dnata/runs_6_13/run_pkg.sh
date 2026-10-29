# holiday packages 6-10 Nov 2026 (4 nights); Bangkok and Kuala Lumpur 6-11 Nov (the Emirates flight lands the next day)
cd /home/user/CPI-Web-Scarping/scripts/oneoff/dnata
R=runs_6_13; mkdir -p $R/shots
CHECKIN=2026-11-06 CHECKOUT=2026-11-10 python3 dnata_packages.py $R/targets_main.json $R/pkg_main.json; echo MAIN_DONE
CHECKIN=2026-11-06 CHECKOUT=2026-11-11 python3 dnata_packages.py $R/targets_late.json $R/pkg_late.json; echo LATE_DONE
CHECKIN=2026-11-06 CHECKOUT=2026-11-10 NIGHTS=4 SHOTDIR=$R/shots python3 shots.py $R/pkg_main.json $R/shots_main.json; echo SHOTS_MAIN_DONE
CHECKIN=2026-11-06 CHECKOUT=2026-11-11 NIGHTS=4 SHOTDIR=$R/shots python3 shots.py $R/pkg_late.json $R/shots_late.json; echo SHOTS_LATE_DONE
